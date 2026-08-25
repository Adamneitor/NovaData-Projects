"""Normalización de orden (índice) de datos adicionales por etapa.

Reglas:
- Todo dato seleccionado tiene índice 1..N (sin nulos ni huecos)
- Al seleccionar: siguiente = max + 1
- Si se asigna un orden ocupado → swap + compactar
"""

from __future__ import annotations

from typing import Any


def parse_orden(value: Any) -> int | None:
    if value is None or value == "" or value is False:
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def ordenar_datos_expediente(caso_datos: list[Any], flujo: Any) -> list[Any]:
    """Ordena datos capturados del caso para el expediente.

    1) Etapa más reciente primero (mayor Etapa.orden)
    2) Dentro de la etapa, por índice EtapaDato.orden (ascendente)
    3) Desempate por dato_id
    """
    etapas = list(getattr(flujo, "etapas", None) or [])
    etapa_orden = {int(e.id): int(e.orden or 0) for e in etapas if getattr(e, "id", None) is not None}

    # (etapa_id, dato_id) → índice configurado
    indice: dict[tuple[int, int], int | None] = {}
    # dato_id → etapa_id de mayor orden donde el dato está asignado (fallback si CasoDato sin etapa)
    etapa_fallback_dato: dict[int, int] = {}
    for e in etapas:
        eid = int(e.id)
        eord = etapa_orden.get(eid, 0)
        for ed in getattr(e, "datos", None) or []:
            did = int(ed.dato_id)
            indice[(eid, did)] = parse_orden(getattr(ed, "orden", None))
            prev = etapa_fallback_dato.get(did)
            if prev is None or eord >= etapa_orden.get(prev, -1):
                etapa_fallback_dato[did] = eid

    def _clave(cd: Any) -> tuple:
        did = int(cd.dato_id)
        eid = int(cd.etapa_id) if getattr(cd, "etapa_id", None) else etapa_fallback_dato.get(did)
        eord = etapa_orden.get(eid, -1) if eid is not None else -1
        dord = indice.get((eid, did)) if eid is not None else None
        if dord is None:
            # buscar índice en cualquier etapa que tenga el dato
            for (ee, dd), oo in indice.items():
                if dd == did and oo is not None:
                    dord = oo
                    if eord < 0:
                        eord = etapa_orden.get(ee, -1)
                    break
        return (
            0 if eord >= 0 else 1,
            -eord,
            dord is None,
            dord if dord is not None else 10_000,
            did,
        )

    return sorted(list(caso_datos or []), key=_clave)


def siguiente_orden_disponible(items: list[dict[str, Any]], *, orden_key: str = "orden") -> int:
    usados = [parse_orden(r.get(orden_key)) for r in items]
    usados = [n for n in usados if n is not None]
    return (max(usados) + 1) if usados else 1


def compactar_ordenes(
    items: list[dict[str, Any]],
    *,
    id_key: str = "dato_id",
    orden_key: str = "orden",
) -> list[dict[str, Any]]:
    """Reasigna 1..N a TODOS los ítems (sin orden van al final)."""
    rows = [dict(x) for x in items]
    ranked = sorted(
        rows,
        key=lambda r: (
            parse_orden(r.get(orden_key)) is None,
            parse_orden(r.get(orden_key)) or 0,
            int(r[id_key]),
        ),
    )
    for idx, r in enumerate(ranked, start=1):
        r[orden_key] = idx
    return rows


def aplicar_cambio_orden(
    items: list[dict[str, Any]],
    dato_id: int,
    nuevo_orden: Any,
    *,
    id_key: str = "dato_id",
    orden_key: str = "orden",
) -> list[dict[str, Any]]:
    """Aplica asignación/swap y compacta. Vacío mueve el ítem al final."""
    rows = [dict(x) for x in items]
    target = next((r for r in rows if int(r[id_key]) == int(dato_id)), None)
    if target is None:
        return compactar_ordenes(rows, id_key=id_key, orden_key=orden_key)

    next_ord = parse_orden(nuevo_orden)
    if next_ord is None:
        # Seleccionados no pueden quedar sin índice → al final
        target[orden_key] = siguiente_orden_disponible(rows, orden_key=orden_key) + 1000
        return compactar_ordenes(rows, id_key=id_key, orden_key=orden_key)

    other = next(
        (r for r in rows if int(r[id_key]) != int(dato_id) and parse_orden(r.get(orden_key)) == next_ord),
        None,
    )
    if other is not None:
        other[orden_key] = parse_orden(target.get(orden_key))
        target[orden_key] = next_ord
    else:
        target[orden_key] = next_ord

    return compactar_ordenes(rows, id_key=id_key, orden_key=orden_key)


def asignar_al_seleccionar(
    items: list[dict[str, Any]],
    dato_id: int,
    *,
    id_key: str = "dato_id",
    orden_key: str = "orden",
    obligatorio: bool = False,
) -> list[dict[str, Any]]:
    """Agrega o reasigna el dato con el siguiente índice disponible."""
    rows = [dict(x) for x in items]
    existing = next((r for r in rows if int(r[id_key]) == int(dato_id)), None)
    nxt = siguiente_orden_disponible(rows, orden_key=orden_key)
    if existing is None:
        rows.append({id_key: int(dato_id), "obligatorio": obligatorio, orden_key: nxt})
    else:
        if parse_orden(existing.get(orden_key)) is None:
            existing[orden_key] = nxt
    return compactar_ordenes(rows, id_key=id_key, orden_key=orden_key)


def normalizar_lista_datos(datos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sanitiza payload: todo seleccionado queda con orden 1..N; conserva reglas condicionales."""
    by_id: dict[int, dict[str, Any]] = {}
    cleaned: list[dict[str, Any]] = []
    for d in datos or []:
        did = int(d["dato_id"])
        dep_raw = d.get("depends_on", d.get("depende_de_dato_id"))
        dep = None
        if dep_raw not in (None, "", 0, "0"):
            try:
                dep = int(dep_raw)
            except (TypeError, ValueError):
                dep = None
        if dep == did:
            dep = None
        row = {
            "dato_id": did,
            "obligatorio": bool(d.get("obligatorio")),
            "orden": parse_orden(d.get("orden")),
            "depends_on": dep,
            "condition": (str(d.get("condition") or d.get("condicion_valor") or "true") if dep else None),
            "required_when": bool(d.get("required_when", d.get("requerido_si_cumple"))) if dep else False,
            "disable_when_false": bool(d.get("disable_when_false", d.get("deshabilitar_si_no_cumple")))
            if dep
            else False,
        }
        by_id[did] = row
        cleaned.append(row)

    # Controllers must exist in the same selection
    for row in cleaned:
        dep = row.get("depends_on")
        if dep and dep not in by_id:
            row["depends_on"] = None
            row["condition"] = None
            row["required_when"] = False
            row["disable_when_false"] = False

    return compactar_ordenes(cleaned)
