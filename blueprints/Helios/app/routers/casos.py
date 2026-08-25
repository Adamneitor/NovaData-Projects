import shutil
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import PERFIL_SOPORTE, PERFIL_SUPER, get_current_user
from app.config import UPLOADS_DIR, should_render_datos_inline
from app.database import get_db
from app.models import (
    Caso,
    CasoApiLog,
    CasoDato,
    CasoDocumento,
    CasoHistorial,
    Cliente,
    DatoComplementario,
    Estado,
    Etapa,
    Flujo,
    Usuario,
)
from app.services import motor
from app.services.api_mapeo import dato_ids_output_de_caso
from app.services.dato_condicion import evaluar_campo
from app.services.dato_formato import format_dato, parse_value, validate_value
from app.services.dato_orden import ordenar_datos_expediente
from app.web import flash, render


def _datos_etapa_ordenados(etapa: Etapa) -> list:
    return sorted(
        list(etapa.datos or []),
        key=lambda ed: (ed.orden is None, ed.orden or 999, ed.dato_id),
    )


def _progreso_datos(datos_etapa, datos_valores: dict) -> tuple[int, int]:
    total = len(datos_etapa)
    completados = sum(1 for ed in datos_etapa if (datos_valores.get(ed.dato_id) or "").strip())
    return completados, total

router = APIRouter(prefix="/casos")

INTENT_PREFIX = "transicion_intent_"


def _intent_key(caso_id: int) -> str:
    return f"{INTENT_PREFIX}{caso_id}"


def _get_intent(request: Request, caso_id: int) -> dict | None:
    intent = request.session.get(_intent_key(caso_id))
    if not intent or intent.get("caso_id") != caso_id:
        return None
    return intent


def _set_intent(request: Request, caso_id: int, estado_destino_id: int, comentario: str,
                errores: list[dict] | None = None, attempt_id: str | None = None) -> dict:
    intent = {
        "caso_id": caso_id,
        "estado_destino_id": estado_destino_id,
        "comentario": comentario or "",
        "errores": errores or [],
        "attempt_id": attempt_id or uuid.uuid4().hex,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    request.session[_intent_key(caso_id)] = intent
    return intent


def _clear_intent(request: Request, caso_id: int) -> None:
    request.session.pop(_intent_key(caso_id), None)


def _refrescar_errores_intent(request: Request, db: Session, caso: Caso) -> dict | None:
    """Si hay intención pendiente, revalida contra el estado actual del caso (post-corrección)."""
    intent = _get_intent(request, caso.id)
    if not intent:
        return None
    destino = db.get(Estado, intent["estado_destino_id"])
    if not destino or not any(
        t.estado_destino_id == destino.id for t in caso.estado_actual.transiciones
    ):
        _clear_intent(request, caso.id)
        return None
    errores = [
        e.as_dict()
        for e in motor.evaluar_movimiento(db, caso, destino, destino.etapa)
    ]
    intent["errores"] = errores
    request.session[_intent_key(caso.id)] = intent
    return intent


def _puede_actuar(usuario: Usuario, etapa: Etapa) -> bool:
    """El usuario puede trabajar la etapa si pertenece a un grupo asignado a ella,
    o si es Super Usuario / Soporte Operativo. Etapas sin grupos: abiertas a todos."""
    if usuario.perfil_id in (PERFIL_SUPER, PERFIL_SOPORTE):
        return True
    if not etapa.grupos:
        return True
    grupos_usuario = {g.id for g in usuario.grupos}
    return any(g.id in grupos_usuario for g in etapa.grupos)


@router.get("")
def lista(
    request: Request,
    estado_general: str = "",
    cliente_id: int | None = None,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Caso).order_by(Caso.id.desc())
    if estado_general:
        q = q.filter(Caso.estado_general == estado_general)
    cliente_pref = db.get(Cliente, cliente_id) if cliente_id else None
    return render(
        request,
        "casos/lista.html",
        {
            "casos": q.limit(300).all(),
            "usuario": usuario,
            "filtro": estado_general,
            "flujos": db.query(Flujo).filter(Flujo.activo).order_by(Flujo.nombre).all(),
            "cliente_pref": cliente_pref,
        },
    )


@router.post("/crear")
def crear(
    request: Request,
    flujo_id: int = Form(...),
    cliente_id: str = Form(...),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not cliente_id.strip():
        flash(request, "Debe seleccionar un cliente para crear el caso.", "danger")
        return RedirectResponse("/casos", status_code=303)

    cliente = db.get(Cliente, int(cliente_id))
    if not cliente:
        flash(request, "Cliente inválido.", "danger")
        return RedirectResponse("/casos", status_code=303)

    flujo = db.get(Flujo, flujo_id)
    if not flujo or not flujo.activo:
        flash(request, "Flujo inválido o inactivo.", "danger")
        return RedirectResponse("/casos", status_code=303)

    try:
        caso = motor.crear_caso(db, flujo, usuario, cliente.id)
        mensajes = motor._procesar_apis_de_estado(db, caso, usuario)
        mensajes += motor._cerrar_si_corresponde(db, caso, usuario)
        db.commit()
        flash(request, f"Caso #{caso.id} creado para {cliente.nombre_completo}.")
        for m in mensajes:
            flash(request, m, "info")
        return RedirectResponse(f"/casos/{caso.id}", status_code=303)
    except motor.MotorError as e:
        db.rollback()
        flash(request, str(e), "danger")
        return RedirectResponse("/casos", status_code=303)

@router.get("/{caso_id}")
def detalle(
    request: Request,
    caso_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    caso = db.get(Caso, caso_id)
    if not caso:
        flash(request, "Caso no encontrado.", "danger")
        return RedirectResponse("/casos", status_code=303)

    etapa = caso.etapa_actual
    estado = caso.estado_actual
    puede_actuar = caso.estado_general == "ACTIVO" and _puede_actuar(usuario, etapa)

    transiciones = estado.transiciones if puede_actuar else []
    docs_pend, datos_pend = motor.pendientes_etapa(db, caso)

    regla_datos_match, regla_datos_preview = (None, None)
    tiene_reglas_datos = False
    regla_api_match, regla_api_preview = (None, None)
    if puede_actuar and estado:
        tiene_reglas_datos = bool(getattr(estado, "reglas_datos", None))
        if tiene_reglas_datos:
            regla_datos_match, regla_datos_preview = motor.resolver_regla_datos(db, caso, estado)

        # AUTO: si ya hay resultado API OK + sin pendientes, avanzar sin click
        auto_msgs = motor.intentar_aplicar_regla_api_auto(db, caso, usuario)
        if auto_msgs:
            db.commit()
            for m in auto_msgs:
                flash(request, m, "info")
            return RedirectResponse(f"/casos/{caso_id}", status_code=303)

        if getattr(estado, "api_call_id", None) and getattr(estado, "reglas_api", None):
            regla_api_match, regla_api_preview, _ = motor.resolver_regla_api(db, caso)

    # Última carga por tipo de documento (para requisitos de etapa actual)
    docs_cargados = {cd.documento_id: cd for cd in caso.documentos}
    # Expediente: todas las cargas del caso (cualquier etapa), más recientes primero
    docs_expediente = sorted(
        list(caso.documentos),
        key=lambda cd: (cd.fecha_carga or datetime.min, cd.id),
        reverse=True,
    )
    etapas_por_id = {e.id: e for e in caso.flujo.etapas}
    datos_valores_all = {cd.dato_id: cd.valor for cd in caso.datos}
    datos_etapa = _datos_etapa_ordenados(etapa)
    datos_completados, datos_total = _progreso_datos(datos_etapa, datos_valores_all)

    # Umbral solo para EDICIÓN en el bucket (cualquier etapa):
    # ≤6 → inputs inline; >6 → CTA al formulario dedicado.
    # La CONSULTA (expediente) siempre muestra valores capturados en cualquier etapa/flujo.
    datos_inline = should_render_datos_inline(len(datos_etapa))
    datos_valores = (
        {ed.dato_id: datos_valores_all.get(ed.dato_id, "") for ed in datos_etapa}
        if datos_inline
        else {}
    )
    datos_expediente = ordenar_datos_expediente(
        [cd for cd in caso.datos if (cd.valor or "").strip()],
        caso.flujo,
    )

    api_logs = (
        db.query(CasoApiLog).filter(CasoApiLog.caso_id == caso.id).order_by(CasoApiLog.id.desc()).limit(20).all()
    )
    # Solo importa el intento MÁS RECIENTE (si ya hubo éxito después de un fallo, no advertir)
    ultimo_api_log = api_logs[0] if api_logs else None
    ultimo_api_log_estado = next(
        (l for l in api_logs if l.estado_id == (estado.id if estado else None)),
        None,
    )
    ultimo_api_fallo = ultimo_api_log if (ultimo_api_log and not ultimo_api_log.exito) else None
    estado_api_fallo = (
        db.get(Estado, ultimo_api_fallo.estado_id)
        if ultimo_api_fallo and ultimo_api_fallo.estado_id
        else None
    )
    puede_reintentar_api = bool(
        puede_actuar and estado and getattr(estado, "api_call_id", None)
    )
    api_estado_nombre = (
        estado.api_call.nombre if (estado and getattr(estado, "api_call", None)) else None
    )
    api_fallo_otro_estado = bool(
        puede_actuar
        and ultimo_api_fallo
        and estado
        and ultimo_api_fallo.estado_id
        and ultimo_api_fallo.estado_id != estado.id
        and not puede_reintentar_api
    )

    intent = _refrescar_errores_intent(request, db, caso) if puede_actuar else None
    if not puede_actuar:
        _clear_intent(request, caso_id)

    # Resumen UX: tiempo en etapa/estado actual
    ultimo_hist = (
        db.query(CasoHistorial)
        .filter(
            CasoHistorial.caso_id == caso.id,
            CasoHistorial.etapa_id == caso.etapa_actual_id,
            CasoHistorial.estado_id == caso.estado_actual_id,
        )
        .order_by(CasoHistorial.id.desc())
        .first()
    )
    desde = ultimo_hist.fecha if ultimo_hist else caso.fecha_creacion
    delta = datetime.now() - desde
    if delta.days > 0:
        tiempo_en_etapa = f"{delta.days}d {delta.seconds // 3600}h"
    elif delta.seconds >= 3600:
        tiempo_en_etapa = f"{delta.seconds // 3600}h {(delta.seconds % 3600) // 60}m"
    else:
        tiempo_en_etapa = f"{max(delta.seconds // 60, 1)} min"

    monto = None
    monto_fmt = None
    for cd in caso.datos:
        nombre = (cd.dato.nombre if cd.dato else "").lower()
        if "monto" in nombre and (cd.valor or "").strip():
            monto = cd.valor
            monto_fmt = format_dato(cd.dato, cd.valor) if cd.dato else cd.valor
            break

    historial_ordenado = list(reversed(list(caso.historial)))
    datos_api_readonly = dato_ids_output_de_caso(db, caso)
    return render(
        request,
        "casos/detalle.html",
        {
            "caso": caso,
            "usuario": usuario,
            "puede_actuar": puede_actuar,
            "transiciones": transiciones,
            "tiene_reglas_datos": tiene_reglas_datos,
            "regla_datos_match": regla_datos_match,
            "regla_datos_preview": regla_datos_preview,
            "regla_api_match": regla_api_match,
            "regla_api_preview": regla_api_preview,
            "docs_etapa": etapa.documentos,
            "datos_etapa": datos_etapa,
            "docs_pendientes": {d.documento_id for d in docs_pend},
            "datos_pendientes": {d.dato_id for d in datos_pend},
            "docs_pend_count": len(docs_pend),
            "datos_pend_count": len(datos_pend),
            "docs_cargados": docs_cargados,
            "docs_expediente": docs_expediente,
            "datos_expediente": datos_expediente,
            "datos_inline": datos_inline,
            "datos_completados": datos_completados,
            "datos_total": datos_total,
            "etapas_por_id": etapas_por_id,
            "datos_valores": datos_valores,
            "datos_api_readonly": datos_api_readonly,
            "api_logs": api_logs,
            "puede_reintentar_api": puede_reintentar_api,
            "ultimo_api_log_estado": ultimo_api_log_estado,
            "api_estado_nombre": api_estado_nombre,
            "ultimo_api_fallo": ultimo_api_fallo,
            "estado_api_fallo": estado_api_fallo,
            "api_fallo_otro_estado": api_fallo_otro_estado,
            "intent": intent,
            "tiempo_en_etapa": tiempo_en_etapa,
            "monto": monto,
            "monto_fmt": monto_fmt,
            "historial_ordenado": historial_ordenado,
            "historial_visible": historial_ordenado[:6],
            "historial_total": len(historial_ordenado),
        },
    )


@router.post("/{caso_id}/mover")
def mover(
    request: Request,
    caso_id: int,
    estado_destino_id: int = Form(...),
    comentario: str = Form(""),
    attempt_id: str = Form(""),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    caso = db.get(Caso, caso_id)
    if not _puede_actuar(usuario, caso.etapa_actual):
        flash(request, "No tiene permisos para actuar en esta etapa.", "danger")
        return RedirectResponse(f"/casos/{caso_id}", status_code=303)

    # Persist intention BEFORE execution (selection ≠ execution)
    intent_prev = _get_intent(request, caso_id)
    # Anti doble ejecución: mismo attempt ya consumido
    if (
        intent_prev
        and intent_prev.get("attempt_id") == attempt_id
        and intent_prev.get("consumed")
    ):
        flash(request, "Este movimiento ya fue procesado. Recargue el caso.", "warning")
        return RedirectResponse(f"/casos/{caso_id}", status_code=303)

    intent = _set_intent(
        request,
        caso_id,
        estado_destino_id,
        comentario.strip(),
        attempt_id=attempt_id or uuid.uuid4().hex,
    )

    valida = any(t.estado_destino_id == estado_destino_id for t in caso.estado_actual.transiciones)
    if not valida:
        intent["errores"] = [
            {
                "codigo": "TRANSICION_INVALIDA",
                "mensaje": "Transición no permitida desde el estado actual.",
                "campo": None,
                "ancla": "#seccion-acciones",
            }
        ]
        request.session[_intent_key(caso_id)] = intent
        flash(request, "Transición no permitida desde el estado actual.", "danger")
        return RedirectResponse(f"/casos/{caso_id}#seccion-acciones", status_code=303)

    destino = db.get(Estado, estado_destino_id)
    try:
        mensajes = motor.mover_caso(db, caso, destino, destino.etapa, usuario, comentario.strip() or None)
        db.commit()
        intent["consumed"] = True
        _clear_intent(request, caso_id)
        for m in mensajes:
            flash(request, m, "info")
        return RedirectResponse(f"/casos/{caso_id}", status_code=303)
    except motor.MotorError as e:
        db.rollback()
        intent["errores"] = e.errores or [
            {"codigo": "ERROR", "mensaje": e.mensaje, "campo": None, "ancla": "#seccion-acciones"}
        ]
        request.session[_intent_key(caso_id)] = intent
        flash(request, e.mensaje, "danger")
        ancla = (e.errores[0].get("ancla") if e.errores else None) or "#seccion-acciones"
        return RedirectResponse(f"/casos/{caso_id}{ancla}", status_code=303)


@router.post("/{caso_id}/reintentar-api")
def reintentar_api(
    request: Request,
    caso_id: int,
    comentario: str = Form(""),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reejecuta el API del estado actual tras un fallo o si el caso quedó detenido."""
    caso = db.get(Caso, caso_id)
    if not caso or not _puede_actuar(usuario, caso.etapa_actual):
        flash(request, "No tiene permisos para actuar en esta etapa.", "danger")
        return RedirectResponse(f"/casos/{caso_id}", status_code=303)

    if caso.estado_general != "ACTIVO":
        flash(request, "El caso no está activo.", "warning")
        return RedirectResponse(f"/casos/{caso_id}", status_code=303)

    if not getattr(caso.estado_actual, "api_call_id", None):
        flash(request, "Este estado no tiene un API asociado.", "warning")
        return RedirectResponse(f"/casos/{caso_id}#seccion-acciones", status_code=303)

    try:
        mensajes = motor.reintentar_api_estado(db, caso, usuario)
        if comentario.strip():
            db.add(
                CasoHistorial(
                    caso_id=caso.id,
                    etapa_id=caso.etapa_actual_id,
                    estado_id=caso.estado_actual_id,
                    usuario_id=usuario.id,
                    comentario=f"Reintento API: {comentario.strip()}"[:500],
                    origen="API",
                )
            )
        db.commit()
        for m in mensajes:
            flash(request, m, "info" if "fallo" not in m.lower() else "danger")
        return RedirectResponse(f"/casos/{caso_id}", status_code=303)
    except motor.MotorError as e:
        db.rollback()
        flash(request, e.mensaje, "danger")
        return RedirectResponse(f"/casos/{caso_id}#seccion-acciones", status_code=303)


@router.post("/{caso_id}/mover-por-api")
def mover_por_api(
    request: Request,
    caso_id: int,
    comentario: str = Form(""),
    attempt_id: str = Form(""),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirma la transición sugerida por una regla API (modo MANUAL)."""
    caso = db.get(Caso, caso_id)
    if not caso or not _puede_actuar(usuario, caso.etapa_actual):
        flash(request, "No tiene permisos para actuar en esta etapa.", "danger")
        return RedirectResponse(f"/casos/{caso_id}", status_code=303)

    try:
        mensajes = motor.mover_por_regla_api(db, caso, usuario, comentario.strip() or None)
        db.commit()
        _clear_intent(request, caso_id)
        for m in mensajes:
            flash(request, m, "info")
        return RedirectResponse(f"/casos/{caso_id}", status_code=303)
    except motor.MotorError as e:
        db.rollback()
        flash(request, e.mensaje, "danger")
        ancla = (e.errores[0].get("ancla") if e.errores else None) or "#seccion-acciones"
        return RedirectResponse(f"/casos/{caso_id}{ancla}", status_code=303)


@router.post("/{caso_id}/mover-por-datos")
def mover_por_datos(
    request: Request,
    caso_id: int,
    comentario: str = Form(""),
    attempt_id: str = Form(""),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ejecuta la primera regla de datos que cumple (o la default) desde el estado actual."""
    caso = db.get(Caso, caso_id)
    if not caso or not _puede_actuar(usuario, caso.etapa_actual):
        flash(request, "No tiene permisos para actuar en esta etapa.", "danger")
        return RedirectResponse(f"/casos/{caso_id}", status_code=303)

    if not getattr(caso.estado_actual, "reglas_datos", None):
        flash(request, "Este estado no tiene reglas por datos configuradas.", "warning")
        return RedirectResponse(f"/casos/{caso_id}#seccion-acciones", status_code=303)

    try:
        mensajes = motor.mover_por_reglas_datos(db, caso, usuario, comentario.strip() or None)
        db.commit()
        _clear_intent(request, caso_id)
        for m in mensajes:
            flash(request, m, "info")
        return RedirectResponse(f"/casos/{caso_id}", status_code=303)
    except motor.MotorError as e:
        db.rollback()
        flash(request, e.mensaje, "danger")
        ancla = (e.errores[0].get("ancla") if e.errores else None) or "#seccion-acciones"
        return RedirectResponse(f"/casos/{caso_id}{ancla}", status_code=303)


@router.post("/{caso_id}/intent/cancelar")
def cancelar_intent(
    request: Request,
    caso_id: int,
    usuario: Usuario = Depends(get_current_user),
):
    _clear_intent(request, caso_id)
    flash(request, "Acción cancelada. Puede elegir otro movimiento.", "info")
    return RedirectResponse(f"/casos/{caso_id}#seccion-acciones", status_code=303)


@router.get("/{caso_id}/validar-movimiento")
def validar_movimiento(
    caso_id: int,
    estado_destino_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Preflight: validación sin side-effects para UI (reintentos / checklist)."""
    from fastapi.responses import JSONResponse

    caso = db.get(Caso, caso_id)
    if not caso:
        return JSONResponse({"ok": False, "errores": [{"codigo": "NOT_FOUND", "mensaje": "Caso no encontrado"}]}, 404)
    destino = db.get(Estado, estado_destino_id)
    if not destino:
        return JSONResponse({"ok": False, "errores": [{"codigo": "DESTINO_INVALIDO", "mensaje": "Destino inválido"}]})
    errores = [e.as_dict() for e in motor.evaluar_movimiento(db, caso, destino, destino.etapa)]
    return JSONResponse({"ok": len(errores) == 0, "errores": errores})


@router.post("/{caso_id}/cancelar")
def cancelar(
    request: Request,
    caso_id: int,
    comentario: str = Form(""),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    caso = db.get(Caso, caso_id)
    if usuario.perfil_id not in (PERFIL_SUPER, PERFIL_SOPORTE):
        flash(request, "Solo Soporte Operativo o Super Usuario pueden cancelar casos.", "danger")
        return RedirectResponse(f"/casos/{caso_id}", status_code=303)
    try:
        motor.cancelar_caso(db, caso, usuario, comentario.strip() or None)
        db.commit()
        flash(request, f"Caso #{caso_id} cancelado.")
    except motor.MotorError as e:
        db.rollback()
        flash(request, str(e), "danger")
    return RedirectResponse(f"/casos/{caso_id}", status_code=303)


# ------------------------------- Documentos --------------------------------


@router.post("/{caso_id}/documentos/{documento_id}/cargar")
def cargar_documento(
    request: Request,
    caso_id: int,
    documento_id: int,
    archivo: UploadFile,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    caso = db.get(Caso, caso_id)
    if caso.estado_general != "ACTIVO" or not _puede_actuar(usuario, caso.etapa_actual):
        flash(request, "No puede cargar documentos en este caso.", "danger")
        return RedirectResponse(f"/casos/{caso_id}", status_code=303)

    carpeta = UPLOADS_DIR / str(caso_id)
    carpeta.mkdir(parents=True, exist_ok=True)
    ext = Path(archivo.filename or "archivo").suffix
    destino = carpeta / f"{documento_id}_{uuid.uuid4().hex[:8]}{ext}"
    with destino.open("wb") as f:
        shutil.copyfileobj(archivo.file, f)

    db.add(
        CasoDocumento(
            caso_id=caso_id,
            documento_id=documento_id,
            etapa_id=caso.etapa_actual_id,
            ruta_archivo=str(destino),
            nombre_original=archivo.filename or destino.name,
            usuario_id=usuario.id,
        )
    )
    db.commit()
    flash(request, "Documento cargado.")
    # Tras completar requisitos, intentar auto-transición por regla API
    caso = db.get(Caso, caso_id)
    if caso and _puede_actuar(usuario, caso.etapa_actual):
        try:
            auto_msgs = motor.intentar_aplicar_regla_api_auto(db, caso, usuario)
            if auto_msgs:
                db.commit()
                for m in auto_msgs:
                    flash(request, m, "info")
        except Exception:  # noqa: BLE001
            db.rollback()
    intent = _get_intent(request, caso_id)
    ancla = "#seccion-acciones" if intent else ""
    return RedirectResponse(f"/casos/{caso_id}{ancla}", status_code=303)


@router.get("/{caso_id}/documentos/{caso_doc_id}/descargar")
def descargar_documento(
    caso_id: int,
    caso_doc_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cd = db.get(CasoDocumento, caso_doc_id)
    if not cd or cd.caso_id != caso_id:
        return RedirectResponse(f"/casos/{caso_id}", status_code=303)
    return FileResponse(cd.ruta_archivo, filename=cd.nombre_original)


# ---------------------------------- Datos ----------------------------------


@router.get("/{caso_id}/datos")
def formulario_datos(
    request: Request,
    caso_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    caso = db.get(Caso, caso_id)
    if not caso:
        flash(request, "Caso no encontrado.", "danger")
        return RedirectResponse("/casos", status_code=303)

    etapa = caso.etapa_actual
    puede_actuar = caso.estado_general == "ACTIVO" and _puede_actuar(usuario, etapa)
    _, datos_pend = motor.pendientes_etapa(db, caso)
    datos_etapa = _datos_etapa_ordenados(etapa)
    datos_valores = {cd.dato_id: cd.valor for cd in caso.datos}
    datos_completados, _ = _progreso_datos(datos_etapa, datos_valores)
    intent = _refrescar_errores_intent(request, db, caso) if puede_actuar else None
    intent_errs = (intent.get("errores") if intent else []) or []
    datos_api_readonly = dato_ids_output_de_caso(db, caso)

    return render(
        request,
        "casos/datos.html",
        {
            "caso": caso,
            "usuario": usuario,
            "puede_actuar": puede_actuar,
            "datos_etapa": datos_etapa,
            "datos_valores": datos_valores,
            "datos_pendientes": {d.dato_id for d in datos_pend},
            "datos_pend_count": len(datos_pend),
            "datos_completados": datos_completados,
            "intent": intent,
            "intent_errs": intent_errs,
            "datos_api_readonly": datos_api_readonly,
        },
    )


@router.post("/{caso_id}/datos")
async def guardar_datos(
    request: Request,
    caso_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    caso = db.get(Caso, caso_id)
    wants_json = "application/json" in (request.headers.get("accept") or "").lower()

    if caso.estado_general != "ACTIVO" or not _puede_actuar(usuario, caso.etapa_actual):
        if wants_json:
            return JSONResponse(
                {"success": False, "errors": [{"field": "_form", "message": "No puede editar datos en este caso."}]},
                status_code=403,
            )
        flash(request, "No puede editar datos en este caso.", "danger")
        return RedirectResponse(f"/casos/{caso_id}", status_code=303)

    form = await request.form()
    return_to = str(form.get("return_to") or "").strip()

    datos_etapa = _datos_etapa_ordenados(caso.etapa_actual)
    bloqueados_api = dato_ids_output_de_caso(db, caso)
    values_ui: dict[str, str] = {}
    for clave, valor in form.items():
        if clave.startswith("dato_"):
            values_ui[clave] = str(valor).strip()

    # Valores para evaluar condiciones (campos deshabilitados no llegan en el POST)
    valores_eval: dict[int, str] = {
        ed.dato_id: values_ui.get(f"dato_{ed.dato_id}", "") for ed in datos_etapa
    }
    # Preservar valores existentes de campos API (disabled no llegan en el form)
    existentes_prev = {cd.dato_id: cd.valor for cd in caso.datos}
    for did in bloqueados_api:
        if did in existentes_prev:
            valores_eval[did] = existentes_prev[did] or ""

    parsed: dict[int, str] = {}
    errors_list: list[dict] = []

    for ed in datos_etapa:
        dato_id = ed.dato_id
        clave = f"dato_{dato_id}"
        # Campos alimentados por API: no aceptar edición manual
        if dato_id in bloqueados_api:
            continue

        valor_ui = valores_eval.get(dato_id, "")
        st = evaluar_campo(ed, valores_eval)

        if not st["enabled"]:
            # No validar; limpiar valor al guardar
            parsed[dato_id] = ""
            values_ui[clave] = ""
            continue

        dato_def = ed.dato or db.get(DatoComplementario, dato_id)
        if not valor_ui:
            if st["required"]:
                errors_list.append(
                    {
                        "field": clave,
                        "dato_id": dato_id,
                        "message": "Este campo es obligatorio.",
                        "ancla": f"#campo-dato_{dato_id}",
                    }
                )
            else:
                parsed[dato_id] = ""
            continue

        if not dato_def:
            continue
        raw = parse_value(valor_ui, dato=dato_def)
        err = validate_value(valor_ui, dato=dato_def)
        if err:
            errors_list.append(
                {
                    "field": clave,
                    "dato_id": dato_id,
                    "message": err,
                    "ancla": f"#campo-dato_{dato_id}",
                }
            )
            continue
        parsed[dato_id] = raw
        values_ui[clave] = valor_ui

    if errors_list:
        if wants_json:
            return JSONResponse(
                {
                    "success": False,
                    "errors": errors_list,
                    "values": values_ui,
                },
                status_code=422,
            )
        # Fallback sin JS: re-renderizar el formulario dedicado conservando valores UI
        etapa = caso.etapa_actual
        _, datos_pend = motor.pendientes_etapa(db, caso)
        datos_etapa = _datos_etapa_ordenados(etapa)
        datos_valores = {cd.dato_id: cd.valor for cd in caso.datos}
        for clave, v in values_ui.items():
            datos_valores[int(clave.removeprefix("dato_"))] = v
        field_err_map = {e["dato_id"]: e["message"] for e in errors_list}
        flash(request, "Corrija los campos marcados. Sus datos se conservaron.", "danger")
        return render(
            request,
            "casos/datos.html",
            {
                "caso": caso,
                "usuario": usuario,
                "puede_actuar": True,
                "datos_etapa": datos_etapa,
                "datos_valores": datos_valores,
                "datos_pendientes": {d.dato_id for d in datos_pend},
                "datos_pend_count": len(datos_pend),
                "datos_completados": sum(1 for ed in datos_etapa if (datos_valores.get(ed.dato_id) or "").strip()),
                "intent": _get_intent(request, caso_id),
                "intent_errs": [],
                "field_errors": field_err_map,
                "valor_es_ui": True,
                "datos_api_readonly": bloqueados_api,
            },
        )

    existentes = {cd.dato_id: cd for cd in caso.datos}
    for dato_id, raw in parsed.items():
        if dato_id in existentes:
            if existentes[dato_id].valor != raw:
                existentes[dato_id].valor = raw
                existentes[dato_id].fecha_modificacion = datetime.now()
                existentes[dato_id].usuario_modificacion_id = usuario.id
            if not existentes[dato_id].etapa_id:
                existentes[dato_id].etapa_id = caso.etapa_actual_id
        elif raw != "":
            db.add(
                CasoDato(
                    caso_id=caso_id,
                    dato_id=dato_id,
                    etapa_id=caso.etapa_actual_id,
                    valor=raw,
                    usuario_adicion_id=usuario.id,
                )
            )
    db.flush()
    auto_msgs = motor.intentar_aplicar_regla_api_auto(db, caso, usuario)
    db.commit()

    intent = _get_intent(request, caso_id)
    if wants_json:
        redirect = (
            f"/casos/{caso_id}#seccion-acciones"
            if intent
            else (f"/casos/{caso_id}/datos" if return_to == "form" else f"/casos/{caso_id}")
        )
        msg = "Datos guardados."
        if auto_msgs:
            msg = "Datos guardados. " + " ".join(auto_msgs)
        elif intent:
            msg = "Datos guardados. Si ya corrigió los pendientes, confirme el movimiento."
        return JSONResponse(
            {
                "success": True,
                "message": msg,
                "redirect": redirect,
                "values": {f"dato_{did}": raw for did, raw in parsed.items()},
            }
        )

    for m in auto_msgs:
        flash(request, m, "info")
    if intent and not auto_msgs:
        flash(request, "Datos guardados. Si ya corrigió los pendientes, confirme el movimiento seleccionado.", "info")
        return RedirectResponse(f"/casos/{caso_id}#seccion-acciones", status_code=303)
    if not auto_msgs:
        flash(request, "Datos guardados.")
    if return_to == "form" and not auto_msgs:
        return RedirectResponse(f"/casos/{caso_id}/datos", status_code=303)
    return RedirectResponse(f"/casos/{caso_id}", status_code=303)