"""Mapeo de inputs/outputs de API con datos del flujo y del cliente."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, selectinload

from app.models import (
    ApiCall,
    ApiRegla,
    ApiReglaCondicion,
    Caso,
    CasoDato,
    Estado,
    EstadoApiInput,
    EstadoApiOutput,
    Etapa,
    Usuario,
)

# Campos del caso / cliente disponibles como origen de input
CAMPOS_CASO: list[tuple[str, str]] = [
    ("id_caso", "Número de caso"),
    ("cliente_id", "Código del cliente"),
    ("cliente_nombre", "Nombre del cliente"),
    ("cliente_identificacion", "Identificación del cliente"),
    ("cliente_correo", "Correo del cliente"),
    ("cliente_telefono", "Teléfono del cliente"),
    ("flujo", "Nombre del flujo"),
    ("etapa", "Etapa actual"),
    ("estado", "Estado actual"),
]

CAMPOS_CASO_KEYS = {c[0] for c in CAMPOS_CASO}


def valor_campo_caso(caso: Caso, campo: str) -> str | None:
    campo = (campo or "").lower().strip()
    cliente = caso.cliente
    mapa = {
        "id_caso": caso.id,
        "cliente_id": caso.cliente_id,
        "cliente_nombre": cliente.nombre_completo if cliente else None,
        "cliente_identificacion": cliente.identificacion if cliente else None,
        "cliente_correo": getattr(cliente, "correo", None) if cliente else None,
        "cliente_telefono": getattr(cliente, "telefono", None) if cliente else None,
        "flujo": caso.flujo.nombre if caso.flujo else None,
        "etapa": caso.etapa_actual.nombre if caso.etapa_actual else None,
        "estado": caso.estado_actual.nombre if caso.estado_actual else None,
    }
    val = mapa.get(campo)
    return None if val is None else str(val)


def valor_dato_caso(db: Session, caso: Caso, dato_id: int | None) -> str | None:
    if not dato_id:
        return None
    cd = (
        db.query(CasoDato)
        .filter(CasoDato.caso_id == caso.id, CasoDato.dato_id == dato_id)
        .first()
    )
    return cd.valor if cd else None


def resolver_origen(
    *,
    origen: str,
    valor_fijo: str | None,
    dato_id: int | None,
    campo_caso: str | None,
    caso: Caso,
    db: Session,
) -> str | None:
    origen = (origen or "fijo").strip().lower()
    if origen == "fijo":
        return valor_fijo
    if origen == "dato":
        return valor_dato_caso(db, caso, dato_id)
    if origen in ("caso", "cliente"):
        return valor_campo_caso(caso, campo_caso or "")
    return None


def _output_a_str(valor: object, formato: str | None = None) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "Si" if valor else "No"
    if formato == "booleano":
        s = str(valor).strip().lower()
        if s in ("true", "1", "si", "sí", "yes"):
            return "Si"
        if s in ("false", "0", "no"):
            return "No"
    return str(valor)


def aplicar_outputs_a_datos(
    db: Session,
    caso: Caso,
    estado: Estado,
    outputs: dict[str, object],
    usuario: Usuario | None = None,
) -> list[str]:
    """Escribe outputs mapeados en CasoDato. Devuelve mensajes descriptivos."""
    mapeos = list(getattr(estado, "mapeos_output", None) or [])
    if not mapeos:
        return []

    mensajes: list[str] = []
    existentes = {cd.dato_id: cd for cd in (caso.datos or [])}
    # refrescar si la colección no está cargada
    if not existentes:
        existentes = {
            cd.dato_id: cd
            for cd in db.query(CasoDato).filter(CasoDato.caso_id == caso.id).all()
        }

    uid = usuario.id if usuario else None
    ahora = datetime.now()

    for m in mapeos:
        out = m.output
        if not out:
            continue
        valor_raw = outputs.get(out.nombre)
        texto = _output_a_str(valor_raw, out.formato)
        nombre_dato = m.dato.nombre if m.dato else f"dato #{m.dato_id}"

        if m.dato_id in existentes:
            cd = existentes[m.dato_id]
            if cd.valor != texto:
                cd.valor = texto
                cd.fecha_modificacion = ahora
                if uid:
                    cd.usuario_modificacion_id = uid
                if not cd.etapa_id:
                    cd.etapa_id = caso.etapa_actual_id
        else:
            cd = CasoDato(
                caso_id=caso.id,
                dato_id=m.dato_id,
                etapa_id=caso.etapa_actual_id,
                valor=texto,
                usuario_adicion_id=uid or 1,
            )
            db.add(cd)
            existentes[m.dato_id] = cd

        mensajes.append(f"{out.nombre} → {nombre_dato} = {texto or '(vacío)'}")

    db.flush()
    return mensajes


def dato_ids_output_del_flujo(db: Session, flujo_id: int) -> set[int]:
    """IDs de datos adicionales mapeados como OUTPUT en algún estado del flujo."""
    rows = (
        db.query(EstadoApiOutput.dato_id)
        .join(Estado, Estado.id == EstadoApiOutput.estado_id)
        .join(Etapa, Etapa.id == Estado.etapa_id)
        .filter(Etapa.flujo_id == flujo_id)
        .all()
    )
    return {int(r[0]) for r in rows if r[0]}


def dato_ids_output_de_caso(db: Session, caso: Caso) -> set[int]:
    return dato_ids_output_del_flujo(db, caso.flujo_id)


def cargar_estado_con_mapeos(db: Session, estado_id: int) -> Estado | None:
    return (
        db.query(Estado)
        .options(
            selectinload(Estado.mapeos_input).selectinload(EstadoApiInput.parametro),
            selectinload(Estado.mapeos_output).selectinload(EstadoApiOutput.output),
            selectinload(Estado.mapeos_output).selectinload(EstadoApiOutput.dato),
            selectinload(Estado.api_call).selectinload(ApiCall.parametros),
            selectinload(Estado.api_call).selectinload(ApiCall.outputs),
            selectinload(Estado.reglas_api).selectinload(ApiRegla.output),
            selectinload(Estado.reglas_api).selectinload(ApiRegla.etapa_destino),
            selectinload(Estado.reglas_api).selectinload(ApiRegla.estado_destino),
            selectinload(Estado.reglas_api)
            .selectinload(ApiRegla.condiciones)
            .selectinload(ApiReglaCondicion.output),
        )
        .filter(Estado.id == estado_id)
        .first()
    )


def validar_mapeos_estado(
    api_id: int | None,
    mapeos_input: list[dict[str, Any]] | None,
    mapeos_output: list[dict[str, Any]] | None,
    catalogo_datos: list[dict] | None = None,
    parametros_api: list[dict] | None = None,
    outputs_api: list[dict] | None = None,
) -> list[str]:
    """Validación en configuración. Devuelve lista de errores."""
    errores: list[str] = []
    if not api_id:
        if mapeos_input or mapeos_output:
            errores.append("Hay mapeos definidos pero el estado no tiene API asociado.")
        return errores

    param_ids = {int(p["id"]) for p in (parametros_api or []) if p.get("id") is not None}
    out_ids = {int(o["id"]) for o in (outputs_api or []) if o.get("id") is not None}
    dato_ids = {int(d["id"]) for d in (catalogo_datos or []) if d.get("id") is not None}
    by_dato = {int(d["id"]): d for d in (catalogo_datos or []) if d.get("id") is not None}
    by_out = {int(o["id"]): o for o in (outputs_api or []) if o.get("id") is not None}

    usados_out_dato: set[int] = set()
    for i, m in enumerate(mapeos_output or [], start=1):
        oid = m.get("output_id")
        did = m.get("dato_id")
        if oid in (None, "", 0, "0"):
            errores.append(f"Output {i}: seleccione un campo de respuesta.")
            continue
        if did in (None, "", 0, "0"):
            errores.append(f"Output {i}: seleccione un dato adicional destino.")
            continue
        oid_i, did_i = int(oid), int(did)
        if out_ids and oid_i not in out_ids:
            errores.append(f"Output {i}: el campo de respuesta no pertenece al API.")
        if dato_ids and did_i not in dato_ids:
            errores.append(f"Output {i}: el dato destino no existe.")
        if did_i in usados_out_dato:
            errores.append(f"Output {i}: el dato destino ya está mapeado por otro output.")
        usados_out_dato.add(did_i)

        # Tipado aproximado
        out_meta = by_out.get(oid_i) or {}
        dato_meta = by_dato.get(did_i) or {}
        fmt = (out_meta.get("formato") or "texto").lower()
        cod = (dato_meta.get("codigo") or "texto").lower()
        if fmt == "numero" and cod not in (
            "numero",
            "numero_decimal",
            "moneda",
            "moneda_decimal",
            "texto",
        ):
            errores.append(
                f"Output {i}: formato número del API poco compatible con tipo «{cod}»."
            )
        if fmt == "booleano" and cod not in ("booleano", "texto"):
            errores.append(
                f"Output {i}: formato booleano del API poco compatible con tipo «{cod}»."
            )

    for i, m in enumerate(mapeos_input or [], start=1):
        pid = m.get("parametro_id")
        origen = (m.get("origen") or "fijo").lower()
        if pid in (None, "", 0, "0"):
            errores.append(f"Input {i}: falta el parámetro del API.")
            continue
        if param_ids and int(pid) not in param_ids:
            errores.append(f"Input {i}: el parámetro no pertenece al API.")
        if origen == "dato" and not m.get("dato_id"):
            errores.append(f"Input {i}: seleccione un dato adicional.")
        if origen in ("caso", "cliente"):
            campo = (m.get("campo_caso") or "").lower()
            if not campo:
                errores.append(f"Input {i}: seleccione un campo del caso/cliente.")
            elif campo not in CAMPOS_CASO_KEYS:
                errores.append(f"Input {i}: campo «{campo}» no válido.")
        if origen == "fijo" and m.get("valor_fijo") in (None, ""):
            # aviso suave: permitido vacío (puede ser opcional)
            pass

    # Un dato no puede ser a la vez origen editable y destino de output en el mismo estado
    input_datos = {
        int(m["dato_id"])
        for m in (mapeos_input or [])
        if (m.get("origen") or "").lower() == "dato" and m.get("dato_id")
    }
    choque = input_datos & usados_out_dato
    if choque:
        errores.append(
            "Un dato no puede ser origen de input y destino de output en el mismo estado: "
            + ", ".join(str(x) for x in sorted(choque))
        )

    return errores
