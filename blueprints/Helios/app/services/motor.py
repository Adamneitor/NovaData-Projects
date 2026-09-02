"""Motor de casos: creacion, validaciones y transiciones (manuales y por API)."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.services.api_engine import (
    ejecutar_api,
    evaluar_reglas,
    outputs_desde_response,
    preview_regla_api,
)
from app.services.api_mapeo import aplicar_outputs_a_datos, cargar_estado_con_mapeos, dato_ids_output_de_caso
from app.services.dato_formato import tipo_codigo
from app.services.dato_regla import evaluar_reglas_datos, preview_regla
from app.models import (
    Caso,
    CasoApiLog,
    CasoDato,
    CasoDocumento,
    CasoHistorial,
    Estado,
    Etapa,
    EtapaDato,
    EtapaDocumento,
    Flujo,
    Usuario,
)
MAX_SALTOS_API = 10
ORIGEN_DATO = "DATO"


class MotorError(Exception):
    def __init__(self, mensaje: str, errores: list[dict] | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.errores = errores or []


@dataclass
class ErrorValidacion:
    codigo: str
    mensaje: str
    campo: str | None = None
    ancla: str | None = None

    def as_dict(self) -> dict:
        return {
            "codigo": self.codigo,
            "mensaje": self.mensaje,
            "campo": self.campo,
            "ancla": self.ancla,
        }


def _errores_pendientes(db: Session, caso: Caso) -> list[ErrorValidacion]:
    docs_pend, datos_pend = pendientes_etapa(db, caso)
    errores: list[ErrorValidacion] = []
    for d in docs_pend:
        errores.append(
            ErrorValidacion(
                codigo="DOC_OBLIGATORIO",
                mensaje=f"Falta el documento obligatorio «{d.documento.nombre}».",
                campo=f"documento_{d.documento_id}",
                ancla="#seccion-documentos",
            )
        )
    for d in datos_pend:
        errores.append(
            ErrorValidacion(
                codigo="DATO_OBLIGATORIO",
                mensaje=f"Falta el dato obligatorio «{d.dato.nombre}».",
                campo=f"dato_{d.dato_id}",
                ancla=f"#campo-dato_{d.dato_id}",
            )
        )
    return errores


def evaluar_movimiento(
    db: Session, caso: Caso, estado_destino: Estado, etapa_destino: Etapa
) -> list[ErrorValidacion]:
    """Validación pura (sin mutar). Separada de la ejecución para reintentos seguros."""
    errores: list[ErrorValidacion] = []
    if caso.estado_general != "ACTIVO":
        errores.append(
            ErrorValidacion(
                codigo="CASO_INACTIVO",
                mensaje="El caso no está activo; no admite movimientos.",
            )
        )
        return errores

    if etapa_destino.id != caso.etapa_actual_id:
        errores.extend(_errores_pendientes(db, caso))
    return errores


def estado_inicial_de_etapa(etapa: Etapa) -> Estado:
    if not etapa.estados:
        raise MotorError(f"La etapa '{etapa.nombre}' no tiene estados definidos.")
    for e in etapa.estados:
        if e.es_inicial:
            return e
    return etapa.estados[0]


def crear_caso(db: Session, flujo: Flujo, usuario: Usuario, cliente_id: int | None) -> Caso:
    etapas = [e for e in flujo.etapas]
    if not etapas:
        raise MotorError("El flujo no tiene etapas definidas.")
    primera = min(etapas, key=lambda e: e.orden)
    estado = estado_inicial_de_etapa(primera)

    from app.services.sqlite_ids import apply_bigint_id

    kwargs = apply_bigint_id(
        db,
        Caso,
        dict(
            flujo_id=flujo.id,
            cliente_id=cliente_id,
            etapa_actual_id=primera.id,
            estado_actual_id=estado.id,
            creado_por_id=usuario.id,
        ),
    )
    caso = Caso(**kwargs)
    db.add(caso)
    db.flush()
    _nuevo_historial(
        db,
        caso_id=caso.id,
        etapa_id=primera.id,
        estado_id=estado.id,
        usuario_id=usuario.id,
        comentario="Caso creado",
        origen="SISTEMA",
    )
    db.flush()
    return caso


from app.services.dato_condicion import es_efectivamente_requerido


def pendientes_etapa(db: Session, caso: Caso) -> tuple[list[EtapaDocumento], list[EtapaDato]]:
    """Documentos y datos obligatorios de la etapa actual que aun no se han cumplido."""
    etapa_id = caso.etapa_actual_id

    docs_requeridos = (
        db.query(EtapaDocumento)
        .filter(EtapaDocumento.etapa_id == etapa_id, EtapaDocumento.obligatorio == True)  # noqa: E712
        .all()
    )
    docs_cargados = {
        cd.documento_id
        for cd in db.query(CasoDocumento).filter(CasoDocumento.caso_id == caso.id).all()
    }
    docs_pendientes = [d for d in docs_requeridos if d.documento_id not in docs_cargados]

    datos_etapa = db.query(EtapaDato).filter(EtapaDato.etapa_id == etapa_id).all()
    valores = {
        cd.dato_id: (cd.valor or "")
        for cd in db.query(CasoDato).filter(CasoDato.caso_id == caso.id).all()
    }
    datos_capturados = {did for did, val in valores.items() if (val or "").strip() != ""}
    bloqueados_api = dato_ids_output_de_caso(db, caso)
    datos_pendientes = [
        d
        for d in datos_etapa
        if d.dato_id not in bloqueados_api
        and es_efectivamente_requerido(d, valores)
        and d.dato_id not in datos_capturados
    ]

    return docs_pendientes, datos_pendientes


def _nuevo_historial(
    db: Session,
    *,
    caso_id: int,
    etapa_id: int,
    estado_id: int,
    usuario_id: int | None,
    comentario: str | None,
    origen: str,
) -> CasoHistorial:
    from app.services.sqlite_ids import apply_bigint_id

    kwargs = apply_bigint_id(
        db,
        CasoHistorial,
        dict(
            caso_id=caso_id,
            etapa_id=etapa_id,
            estado_id=estado_id,
            usuario_id=usuario_id,
            comentario=comentario,
            origen=origen,
        ),
    )
    h = CasoHistorial(**kwargs)
    db.add(h)
    return h


def _registrar(db: Session, caso: Caso, etapa_id: int, estado_id: int, usuario_id: int | None,
               comentario: str | None, origen: str) -> None:
    caso.etapa_actual_id = etapa_id
    caso.estado_actual_id = estado_id
    _nuevo_historial(
        db,
        caso_id=caso.id,
        etapa_id=etapa_id,
        estado_id=estado_id,
        usuario_id=usuario_id,
        comentario=comentario,
        origen=origen,
    )
    db.flush()


def _cerrar_si_corresponde(db: Session, caso: Caso, usuario: Usuario | None) -> list[str]:
    """Si el caso llego a un estado que cierra una etapa final, cierra el caso e
    invoca el API de conclusion del flujo si esta configurado."""
    mensajes: list[str] = []
    db.refresh(caso)
    estado = db.get(Estado, caso.estado_actual_id)
    etapa = db.get(Etapa, caso.etapa_actual_id)
    if not (etapa.es_final and estado.cierra_etapa):
        return mensajes

    caso.estado_general = "CERRADO"
    caso.fecha_cierre = datetime.now()
    mensajes.append("El caso ha llegado a una etapa final y fue CERRADO.")

    flujo = db.get(Flujo, caso.flujo_id)
    if flujo.api_conclusion_id and flujo.api_conclusion:
        resultado = ejecutar_api(flujo.api_conclusion, caso, db, estado_id=estado.id)
        if resultado.exito:
            mensajes.append(f"API de conclusion '{flujo.api_conclusion.nombre}' ejecutado correctamente.")
        else:
            mensajes.append(
                f"API de conclusion '{flujo.api_conclusion.nombre}' fallo: {resultado.error}"
            )
        _nuevo_historial(
            db,
            caso_id=caso.id,
            etapa_id=etapa.id,
            estado_id=estado.id,
            usuario_id=usuario.id if usuario else None,
            comentario=mensajes[-1][:500],
            origen="API",
        )
    db.flush()
    return mensajes


def _procesar_apis_de_estado(db: Session, caso: Caso, usuario: Usuario | None) -> list[str]:
    """Mientras el estado actual tenga un API asociado, lo ejecuta, aplica mapeos
    de output a datos adicionales y aplica la regla de direccionamiento."""
    mensajes: list[str] = []
    for _ in range(MAX_SALTOS_API):
        estado = cargar_estado_con_mapeos(db, caso.estado_actual_id)
        if not estado or not estado.api_call_id or not estado.api_call:
            break

        api = estado.api_call
        resultado = ejecutar_api(api, caso, db, estado_id=estado.id, estado=estado)
        if not resultado.exito:
            mensajes.append(f"API '{api.nombre}' fallo: {resultado.error}. El caso permanece en '{estado.nombre}'.")
            _nuevo_historial(
                db,
                caso_id=caso.id,
                etapa_id=caso.etapa_actual_id,
                estado_id=estado.id,
                usuario_id=usuario.id if usuario else None,
                comentario=mensajes[-1][:500],
                origen="API",
            )
            db.flush()
            break

        # Persistir outputs → datos adicionales según mapeo del estado
        aplicados = aplicar_outputs_a_datos(db, caso, estado, resultado.outputs, usuario)
        if aplicados:
            mensajes.append(
                f"API '{api.nombre}' actualizó datos: " + "; ".join(aplicados) + "."
            )
            db.expire(caso, ["datos"])

        outputs_txt = ", ".join(f"{k}={v}" for k, v in resultado.outputs.items()) or "sin outputs"
        regla = evaluar_reglas(estado.reglas_api, resultado.outputs)
        if not regla:
            mensajes.append(
                f"API '{api.nombre}' respondio ({outputs_txt}) pero ninguna regla aplico. "
                f"El caso permanece en '{estado.nombre}'."
            )
            _nuevo_historial(
                db,
                caso_id=caso.id,
                etapa_id=caso.etapa_actual_id,
                estado_id=estado.id,
                usuario_id=usuario.id if usuario else None,
                comentario=mensajes[-1][:500],
                origen="API",
            )
            db.flush()
            break

        preview = preview_regla_api(regla)
        destino_txt = f"{regla.etapa_destino.nombre} / {regla.estado_destino.nombre}"
        modo = str(getattr(regla, "modo_ejecucion", None) or "AUTO").strip().upper()
        docs_pend, datos_pend = pendientes_etapa(db, caso)
        tiene_pendientes = bool(docs_pend or datos_pend)

        if modo == "MANUAL" or tiene_pendientes:
            if modo == "MANUAL":
                mensajes.append(
                    f"API '{api.nombre}' respondio ({outputs_txt}); regla pendiente (manual): "
                    f"{preview} → {destino_txt}. Confirme la transición en el caso."
                )
            else:
                mensajes.append(
                    f"API '{api.nombre}' respondio ({outputs_txt}); regla pendiente (auto): "
                    f"{preview} → {destino_txt}. Complete datos/documentos obligatorios "
                    f"para avanzar automáticamente."
                )
            _nuevo_historial(
                db,
                caso_id=caso.id,
                etapa_id=caso.etapa_actual_id,
                estado_id=estado.id,
                usuario_id=usuario.id if usuario else None,
                comentario=mensajes[-1][:500],
                origen="API",
            )
            db.flush()
            break

        mensajes.append(
            f"API '{api.nombre}' respondio ({outputs_txt}); regla aplicada (auto): "
            f"{preview} → {destino_txt}."
        )
        _registrar(
            db,
            caso,
            regla.etapa_destino_id,
            regla.estado_destino_id,
            usuario.id if usuario else None,
            mensajes[-1][:500],
            "API",
        )
    else:
        mensajes.append("Se alcanzo el limite de saltos automaticos por API; revise la configuracion del flujo.")

    return mensajes


def _outputs_api_estado_actual(db: Session, caso: Caso, estado: Estado) -> dict[str, object]:
    """Outputs del último API exitoso del estado actual (desde el log)."""
    if not estado.api_call:
        return {}
    log = (
        db.query(CasoApiLog)
        .filter(
            CasoApiLog.caso_id == caso.id,
            CasoApiLog.estado_id == estado.id,
            CasoApiLog.exito.is_(True),
        )
        .order_by(CasoApiLog.id.desc())
        .first()
    )
    if not log:
        return {}
    return outputs_desde_response(estado.api_call, log.response_json)


def resolver_regla_api(db: Session, caso: Caso, estado: Estado | None = None):
    """Evalúa reglas API del estado con el último response exitoso. (regla, preview, outputs)."""
    if estado is None:
        estado = cargar_estado_con_mapeos(db, caso.estado_actual_id)
    if not estado or not getattr(estado, "reglas_api", None):
        return None, None, {}
    outputs = _outputs_api_estado_actual(db, caso, estado)
    if not outputs:
        return None, None, {}
    regla = evaluar_reglas(list(estado.reglas_api or []), outputs)
    preview = preview_regla_api(regla) if regla else None
    return regla, preview, outputs


def intentar_aplicar_regla_api_auto(
    db: Session, caso: Caso, usuario: Usuario | None
) -> list[str]:
    """Si hay regla API AUTO cumplida y sin pendientes, transiciona sin click."""
    if caso.estado_general != "ACTIVO":
        return []
    estado = cargar_estado_con_mapeos(db, caso.estado_actual_id)
    if not estado or not estado.api_call_id:
        return []
    regla, preview, _ = resolver_regla_api(db, caso, estado)
    if not regla:
        return []
    modo = str(getattr(regla, "modo_ejecucion", None) or "AUTO").strip().upper()
    if modo != "AUTO":
        return []
    docs_pend, datos_pend = pendientes_etapa(db, caso)
    if docs_pend or datos_pend:
        return []

    destino_txt = f"{regla.etapa_destino.nombre} / {regla.estado_destino.nombre}"
    mensajes = [f"Regla API aplicada (auto): {preview or 'regla'} → {destino_txt}."]
    _registrar(
        db,
        caso,
        regla.etapa_destino_id,
        regla.estado_destino_id,
        usuario.id if usuario else None,
        mensajes[-1][:500],
        "API",
    )
    mensajes += _procesar_apis_de_estado(db, caso, usuario)
    mensajes += _cerrar_si_corresponde(db, caso, usuario)
    return mensajes


def mover_por_regla_api(
    db: Session,
    caso: Caso,
    usuario: Usuario,
    comentario: str | None = None,
) -> list[str]:
    """Confirma la transición sugerida por una regla API (modo MANUAL)."""
    if caso.estado_general != "ACTIVO":
        raise MotorError("El caso no está activo.")
    estado = cargar_estado_con_mapeos(db, caso.estado_actual_id)
    regla, preview, _ = resolver_regla_api(db, caso, estado)
    if not regla:
        raise MotorError(
            "No hay una regla API pendiente aplicable con el último resultado del API.",
            errores=[
                {
                    "codigo": "SIN_REGLA_API",
                    "mensaje": "Ejecute o reintente el API, o revise las condiciones de las reglas.",
                    "campo": None,
                    "ancla": "#seccion-acciones",
                }
            ],
        )

    destino = db.get(Estado, regla.estado_destino_id)
    etapa_destino = db.get(Etapa, regla.etapa_destino_id)
    errores = evaluar_movimiento(db, caso, destino, etapa_destino)
    if errores:
        raise MotorError(
            "No se puede ejecutar el movimiento. Corrija los pendientes y confirme de nuevo.",
            errores=[e.as_dict() for e in errores],
        )

    detalle = preview or f"prioridad {regla.prioridad}"
    mensajes = [
        f"Regla API confirmada ({detalle}) → {etapa_destino.nombre} / {destino.nombre}."
    ]
    _registrar(
        db,
        caso,
        etapa_destino.id,
        destino.id,
        usuario.id,
        (comentario or mensajes[-1])[:500],
        "API",
    )
    mensajes += _procesar_apis_de_estado(db, caso, usuario)
    mensajes += _cerrar_si_corresponde(db, caso, usuario)
    return mensajes


def reintentar_api_estado(db: Session, caso: Caso, usuario: Usuario | None) -> list[str]:
    """Reejecuta el API del estado actual (útil tras un fallo o cuando no aplicó regla)."""
    if caso.estado_general != "ACTIVO":
        raise MotorError("El caso no está activo.")
    estado = cargar_estado_con_mapeos(db, caso.estado_actual_id)
    if not estado or not estado.api_call_id:
        raise MotorError(
            "El estado actual no tiene un API asociado para reintentar.",
            errores=[
                {
                    "codigo": "SIN_API",
                    "mensaje": "Este estado no tiene API configurado.",
                    "campo": None,
                    "ancla": "#seccion-acciones",
                }
            ],
        )
    mensajes = _procesar_apis_de_estado(db, caso, usuario)
    if not mensajes:
        mensajes = [
            f"API '{estado.api_call.nombre if estado.api_call else ''}' ejecutado; "
            "sin cambios adicionales."
        ]
    mensajes += _cerrar_si_corresponde(db, caso, usuario)
    return mensajes


def valores_datos_caso(db: Session, caso: Caso) -> dict[int, str]:
    return {cd.dato_id: (cd.valor or "") for cd in (caso.datos or [])}


def meta_datos_caso(db: Session, caso: Caso) -> dict[int, dict]:
    meta: dict[int, dict] = {}
    for cd in caso.datos or []:
        if not cd.dato:
            continue
        meta[cd.dato_id] = {
            "codigo": tipo_codigo(cd.dato.tipo_dato),
            "nombre": cd.dato.nombre,
        }
    # También incluir datos de etapas del flujo aunque no tengan valor aún
    flujo = db.get(Flujo, caso.flujo_id)
    for etapa in flujo.etapas or []:
        for ed in etapa.datos or []:
            if ed.dato_id in meta or not ed.dato:
                continue
            meta[ed.dato_id] = {
                "codigo": tipo_codigo(ed.dato.tipo_dato),
                "nombre": ed.dato.nombre,
            }
    return meta


def _estado_con_reglas_datos(db: Session, estado_id: int) -> Estado | None:
    from sqlalchemy.orm import selectinload

    from app.models import DatoRegla

    return (
        db.query(Estado)
        .options(selectinload(Estado.reglas_datos).selectinload(DatoRegla.condiciones))
        .filter(Estado.id == estado_id)
        .first()
    )


def resolver_regla_datos(db: Session, caso: Caso, estado: Estado | None = None):
    """Evalúa reglas de datos del estado actual. Devuelve (regla|None, preview)."""
    if estado is None:
        estado = _estado_con_reglas_datos(db, caso.estado_actual_id)
    if not estado:
        return None, None
    reglas = list(getattr(estado, "reglas_datos", None) or [])
    if not reglas:
        return None, None
    # Asegura condiciones cargadas (lazy) dentro de la sesión
    for r in reglas:
        _ = list(r.condiciones or [])
    valores = valores_datos_caso(db, caso)
    meta = meta_datos_caso(db, caso)
    nombres = {k: v.get("nombre") or f"#{k}" for k, v in meta.items()}
    regla = evaluar_reglas_datos(reglas, valores, meta)
    preview = preview_regla(regla, nombres) if regla else None
    return regla, preview


def mover_por_reglas_datos(
    db: Session,
    caso: Caso,
    usuario: Usuario,
    comentario: str | None = None,
) -> list[str]:
    """Aplica la primera regla de datos que cumple (o la default) y continúa el motor."""
    if caso.estado_general != "ACTIVO":
        raise MotorError("El caso no está activo.")
    estado = _estado_con_reglas_datos(db, caso.estado_actual_id)
    regla, preview = resolver_regla_datos(db, caso, estado)
    if not regla:
        raise MotorError(
            "Ninguna regla de datos aplica y no hay fallback configurado.",
            errores=[
                {
                    "codigo": "SIN_REGLA_DATOS",
                    "mensaje": "Ninguna condición se cumplió y no hay transición por defecto.",
                    "campo": None,
                    "ancla": "#seccion-acciones",
                }
            ],
        )

    destino = db.get(Estado, regla.estado_destino_id)
    etapa_destino = db.get(Etapa, regla.etapa_destino_id)
    errores = evaluar_movimiento(db, caso, destino, etapa_destino)
    if errores:
        raise MotorError(
            "No se puede ejecutar el movimiento. Corrija los pendientes y confirme de nuevo.",
            errores=[e.as_dict() for e in errores],
        )

    detalle = preview or f"prioridad {regla.prioridad}"
    mensajes = [
        f"Regla de datos aplicada ({detalle}) → {etapa_destino.nombre} / {destino.nombre}."
    ]
    _registrar(
        db,
        caso,
        etapa_destino.id,
        destino.id,
        usuario.id,
        (comentario or mensajes[-1])[:500],
        ORIGEN_DATO,
    )
    mensajes += _procesar_apis_de_estado(db, caso, usuario)
    mensajes += _cerrar_si_corresponde(db, caso, usuario)
    return mensajes


def mover_caso(db: Session, caso: Caso, estado_destino: Estado, etapa_destino: Etapa,
               usuario: Usuario, comentario: str | None) -> list[str]:
    """Aplica una transicion manual y luego procesa APIs y cierre automatico."""
    errores = evaluar_movimiento(db, caso, estado_destino, etapa_destino)
    if errores:
        raise MotorError(
            "No se puede ejecutar el movimiento. Corrija los pendientes y confirme de nuevo.",
            errores=[e.as_dict() for e in errores],
        )

    mensajes = [f"Movido a {etapa_destino.nombre} / {estado_destino.nombre}."]
    _registrar(db, caso, etapa_destino.id, estado_destino.id, usuario.id, comentario, "MANUAL")
    mensajes += _procesar_apis_de_estado(db, caso, usuario)
    mensajes += _cerrar_si_corresponde(db, caso, usuario)
    return mensajes


def cancelar_caso(db: Session, caso: Caso, usuario: Usuario, comentario: str | None) -> None:
    if caso.estado_general != "ACTIVO":
        raise MotorError("El caso no esta activo.")
    caso.estado_general = "CANCELADO"
    caso.fecha_cierre = datetime.now()
    _nuevo_historial(
        db,
        caso_id=caso.id,
        etapa_id=caso.etapa_actual_id,
        estado_id=caso.estado_actual_id,
        usuario_id=usuario.id,
        comentario=comentario or "Caso cancelado",
        origen="MANUAL",
    )
    db.flush()
