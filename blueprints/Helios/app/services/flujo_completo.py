"""Serialización y guardado transaccional completo de un flujo BPM."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, selectinload

from app.models import (
    ApiCall,
    ApiRegla,
    ApiReglaCondicion,
    DatoRegla,
    DatoReglaCondicion,
    Estado,
    EstadoApiInput,
    EstadoApiOutput,
    Etapa,
    EtapaDato,
    EtapaDocumento,
    Flujo,
    GrupoUsuario,
    Transicion,
)
from app.services.api_mapeo import CAMPOS_CASO
from app.services.dato_orden import normalizar_lista_datos
from app.services.dato_regla import OPS_BOOL, OPS_NUMERO, OPS_TEXTO, operadores_para_codigo


def _is_temp(value: Any) -> bool:
    if value is None:
        return True
    s = str(value)
    return s.startswith("temp-") or s == "" or s == "null"


def _as_int(value: Any) -> int | None:
    if value is None or value == "" or _is_temp(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def serializar_flujo(flujo: Flujo) -> dict[str, Any]:
    """Snapshot JSON del flujo completo (etapas → estados → transiciones/reglas)."""
    etapas_out = []
    for etapa in sorted(flujo.etapas or [], key=lambda e: e.orden):
        estados_out = []
        for est in etapa.estados or []:
            estados_out.append(
                {
                    "id": est.id,
                    "key": str(est.id),
                    "nombre": est.nombre,
                    "es_inicial": bool(est.es_inicial),
                    "cierra_etapa": bool(est.cierra_etapa),
                    "api_call_id": est.api_call_id,
                    "transiciones": [
                        {
                            "id": t.id,
                            "estado_destino_key": str(t.estado_destino_id),
                            "estado_destino_id": t.estado_destino_id,
                        }
                        for t in (est.transiciones or [])
                    ],
                    "reglas": [
                        {
                            "id": r.id,
                            "nombre": r.nombre or "",
                            "logica": r.logica or "AND",
                            "modo_ejecucion": r.modo_ejecucion or "AUTO",
                            "prioridad": r.prioridad,
                            "estado_destino_key": str(r.estado_destino_id),
                            "estado_destino_id": r.estado_destino_id,
                            # Legado (primera condición) para compatibilidad UI antigua
                            "output_id": (
                                (r.condiciones[0].output_id if r.condiciones else None)
                                or r.output_id
                            ),
                            "operador": (
                                (r.condiciones[0].operador if r.condiciones else None)
                                or r.operador
                                or "="
                            ),
                            "valor": (
                                (r.condiciones[0].valor if r.condiciones else None)
                                or r.valor
                                or ""
                            ),
                            "condiciones": [
                                {
                                    "id": c.id,
                                    "output_id": c.output_id,
                                    "operador": c.operador,
                                    "valor": c.valor or "",
                                }
                                for c in (r.condiciones or [])
                            ]
                            or (
                                [
                                    {
                                        "id": None,
                                        "output_id": r.output_id,
                                        "operador": r.operador or "=",
                                        "valor": r.valor or "",
                                    }
                                ]
                                if r.output_id
                                else []
                            ),
                        }
                        for r in sorted(est.reglas_api or [], key=lambda x: x.prioridad)
                    ],
                    "reglas_datos": [
                        {
                            "id": r.id,
                            "nombre": r.nombre or "",
                            "logica": r.logica or "AND",
                            "prioridad": r.prioridad,
                            "es_default": bool(r.es_default),
                            "estado_destino_key": str(r.estado_destino_id),
                            "estado_destino_id": r.estado_destino_id,
                            "condiciones": [
                                {
                                    "id": c.id,
                                    "dato_id": c.dato_id,
                                    "operador": c.operador,
                                    "valor": c.valor or "",
                                    "valor_hasta": c.valor_hasta or "",
                                }
                                for c in (r.condiciones or [])
                            ],
                        }
                        for r in sorted(
                            est.reglas_datos or [],
                            key=lambda x: (bool(x.es_default), x.prioridad, x.id),
                        )
                    ],
                    "mapeos_input": [
                        {
                            "id": m.id,
                            "parametro_id": m.parametro_id,
                            "origen": m.origen or "fijo",
                            "valor_fijo": m.valor_fijo or "",
                            "dato_id": m.dato_id,
                            "campo_caso": m.campo_caso or "",
                        }
                        for m in (est.mapeos_input or [])
                    ],
                    "mapeos_output": [
                        {
                            "id": m.id,
                            "output_id": m.output_id,
                            "dato_id": m.dato_id,
                        }
                        for m in (est.mapeos_output or [])
                    ],
                }
            )
        etapas_out.append(
            {
                "id": etapa.id,
                "key": str(etapa.id),
                "nombre": etapa.nombre,
                "descripcion": etapa.descripcion or "",
                "orden": etapa.orden,
                "permite_retroceso": bool(etapa.permite_retroceso),
                "es_final": bool(etapa.es_final),
                "solicita_documentacion": bool(etapa.solicita_documentacion),
                "grupo_ids": [g.id for g in (etapa.grupos or [])],
                "documentos": [
                    {"documento_id": d.documento_id, "obligatorio": bool(d.obligatorio)}
                    for d in (etapa.documentos or [])
                ],
                "datos": normalizar_lista_datos(
                    [
                        {
                            "dato_id": d.dato_id,
                            "obligatorio": bool(d.obligatorio),
                            "orden": d.orden if d.orden and d.orden > 0 else None,
                            "depends_on": d.depende_de_dato_id,
                            "condition": d.condicion_valor or "true",
                            "required_when": bool(d.requerido_si_cumple),
                            "disable_when_false": bool(d.deshabilitar_si_no_cumple),
                        }
                        for d in (etapa.datos or [])
                    ]
                ),
                "estados": estados_out,
            }
        )

    return {
        "flujo": {
            "id": flujo.id,
            "nombre": flujo.nombre,
            "descripcion": flujo.descripcion or "",
            "tipo_flujo_id": flujo.tipo_flujo_id,
            "api_conclusion_id": flujo.api_conclusion_id,
            "activo": bool(flujo.activo),
        },
        "etapas": etapas_out,
    }


def cargar_flujo_completo(db: Session, flujo_id: int) -> Flujo | None:
    db.expire_all()
    return (
        db.query(Flujo)
        .options(
            selectinload(Flujo.etapas).selectinload(Etapa.estados).selectinload(Estado.transiciones),
            selectinload(Flujo.etapas)
            .selectinload(Etapa.estados)
            .selectinload(Estado.reglas_api)
            .selectinload(ApiRegla.condiciones),
            selectinload(Flujo.etapas)
            .selectinload(Etapa.estados)
            .selectinload(Estado.reglas_datos)
            .selectinload(DatoRegla.condiciones),
            selectinload(Flujo.etapas).selectinload(Etapa.estados).selectinload(Estado.mapeos_input),
            selectinload(Flujo.etapas).selectinload(Etapa.estados).selectinload(Estado.mapeos_output),
            selectinload(Flujo.etapas).selectinload(Etapa.documentos),
            selectinload(Flujo.etapas).selectinload(Etapa.datos),
            selectinload(Flujo.etapas).selectinload(Etapa.grupos),
        )
        .filter(Flujo.id == flujo_id)
        .first()
    )


def guardar_flujo_completo(db: Session, flujo_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Persiste el árbol completo en una sola transacción.
    Soporta IDs temporales (temp-*) y resuelve relaciones al final.
    """
    flujo = db.get(Flujo, flujo_id)
    if not flujo:
        raise ValueError("Flujo no encontrado.")

    props = payload.get("flujo") or {}
    etapas_payload = payload.get("etapas") or []

    # --- 1. Flujo ---
    if "nombre" in props:
        nombre = (props.get("nombre") or "").strip()
        if not nombre:
            raise ValueError("El nombre del flujo es obligatorio.")
        flujo.nombre = nombre
    if "descripcion" in props:
        flujo.descripcion = (props.get("descripcion") or "").strip() or None
    if "tipo_flujo_id" in props and props.get("tipo_flujo_id"):
        flujo.tipo_flujo_id = int(props["tipo_flujo_id"])
    if "activo" in props:
        flujo.activo = bool(props.get("activo"))
    if "api_conclusion_id" in props:
        raw = props.get("api_conclusion_id")
        flujo.api_conclusion_id = int(raw) if raw not in (None, "", 0, "0") else None

    db.flush()

    etapa_key_to_id: dict[str, int] = {}
    estado_key_to_id: dict[str, int] = {}
    etapas_keep: set[int] = set()

    # --- 2. Etapas (upsert) ---
    for idx, ep in enumerate(etapas_payload, start=1):
        key = str(ep.get("key") or ep.get("id") or f"temp-e{idx}")
        etapa_id = _as_int(ep.get("id"))
        orden = int(ep.get("orden") or idx)
        nombre = (ep.get("nombre") or "").strip() or f"Etapa {idx}"

        if etapa_id:
            etapa = db.get(Etapa, etapa_id)
            if not etapa or etapa.flujo_id != flujo_id:
                raise ValueError(f"Etapa inválida: {etapa_id}")
        else:
            etapa = Etapa(flujo_id=flujo_id, nombre=nombre, orden=orden)
            db.add(etapa)
            db.flush()

        etapa.nombre = nombre
        etapa.descripcion = (ep.get("descripcion") or "").strip() or None
        etapa.orden = orden
        etapa.permite_retroceso = bool(ep.get("permite_retroceso"))
        etapa.es_final = bool(ep.get("es_final"))
        etapa.solicita_documentacion = bool(ep.get("solicita_documentacion"))
        db.flush()

        etapa_key_to_id[key] = etapa.id
        etapa_key_to_id[str(etapa.id)] = etapa.id
        etapas_keep.add(etapa.id)

        # Grupos (replace-all)
        grupo_ids = [int(g) for g in (ep.get("grupo_ids") or []) if str(g).strip() != ""]
        etapa.grupos = (
            db.query(GrupoUsuario).filter(GrupoUsuario.id.in_(grupo_ids)).all() if grupo_ids else []
        )

        # Documentos
        db.query(EtapaDocumento).filter(EtapaDocumento.etapa_id == etapa.id).delete()
        for doc in ep.get("documentos") or []:
            doc_id = int(doc["documento_id"])
            db.add(
                EtapaDocumento(
                    etapa_id=etapa.id,
                    documento_id=doc_id,
                    obligatorio=bool(doc.get("obligatorio")),
                )
            )

        # Datos (orden solo si el usuario lo definió; sin autoíndice)
        db.query(EtapaDato).filter(EtapaDato.etapa_id == etapa.id).delete()
        for dato in normalizar_lista_datos(ep.get("datos") or []):
            dep = dato.get("depends_on")
            db.add(
                EtapaDato(
                    etapa_id=etapa.id,
                    dato_id=int(dato["dato_id"]),
                    obligatorio=bool(dato.get("obligatorio")),
                    orden=dato.get("orden"),
                    depende_de_dato_id=int(dep) if dep else None,
                    condicion_valor=(dato.get("condition") or "true") if dep else None,
                    requerido_si_cumple=bool(dato.get("required_when")) if dep else False,
                    deshabilitar_si_no_cumple=bool(dato.get("disable_when_false")) if dep else False,
                )
            )

        # Estados upsert
        estados_keep: set[int] = set()
        estados_payload = ep.get("estados") or []
        if not estados_payload:
            # Toda etapa necesita al menos un estado inicial
            estados_payload = [
                {
                    "key": f"temp-s-{key}-1",
                    "nombre": "Pendiente",
                    "es_inicial": True,
                    "cierra_etapa": False,
                    "api_call_id": None,
                    "transiciones": [],
                    "reglas": [],
                    "reglas_datos": [],
                    "mapeos_input": [],
                    "mapeos_output": [],
                }
            ]

        iniciales = sum(1 for s in estados_payload if s.get("es_inicial"))
        if iniciales == 0:
            estados_payload[0]["es_inicial"] = True
        elif iniciales > 1:
            seen = False
            for s in estados_payload:
                if s.get("es_inicial"):
                    if seen:
                        s["es_inicial"] = False
                    seen = True

        for si, sp in enumerate(estados_payload, start=1):
            skey = str(sp.get("key") or sp.get("id") or f"temp-s-{etapa.id}-{si}")
            sid = _as_int(sp.get("id"))
            if sid:
                estado = db.get(Estado, sid)
                if not estado or estado.etapa_id != etapa.id:
                    # permitir mover estado solo dentro de la etapa; si no, crear
                    estado = Estado(etapa_id=etapa.id, nombre=(sp.get("nombre") or "Estado").strip())
                    db.add(estado)
                    db.flush()
            else:
                estado = Estado(etapa_id=etapa.id, nombre=(sp.get("nombre") or f"Estado {si}").strip())
                db.add(estado)
                db.flush()

            estado.nombre = (sp.get("nombre") or estado.nombre).strip()
            estado.es_inicial = bool(sp.get("es_inicial"))
            estado.cierra_etapa = bool(sp.get("cierra_etapa"))
            api_raw = sp.get("api_call_id")
            estado.api_call_id = int(api_raw) if api_raw not in (None, "", 0, "0") else None
            db.flush()

            estado_key_to_id[skey] = estado.id
            estado_key_to_id[str(estado.id)] = estado.id
            estados_keep.add(estado.id)
            # stash transitions/rules for second pass
            sp["_resolved_id"] = estado.id

        # Delete estados removed from payload
        for est in list(etapa.estados or []):
            if est.id not in estados_keep:
                db.query(Transicion).filter(Transicion.estado_origen_id == est.id).delete()
                db.query(ApiRegla).filter(ApiRegla.estado_id == est.id).delete()
                db.query(DatoRegla).filter(DatoRegla.estado_id == est.id).delete()
                db.query(EstadoApiInput).filter(EstadoApiInput.estado_id == est.id).delete()
                db.query(EstadoApiOutput).filter(EstadoApiOutput.estado_id == est.id).delete()
                # también referencias entrantes
                db.query(Transicion).filter(Transicion.estado_destino_id == est.id).delete()
                db.query(ApiRegla).filter(ApiRegla.estado_destino_id == est.id).delete()
                db.query(DatoRegla).filter(DatoRegla.estado_destino_id == est.id).delete()
                db.delete(est)
        db.flush()

        # Guardamos payload de estados en la etapa para pase 2
        ep["_estados_resolved"] = estados_payload

    # Eliminar etapas no incluidas
    for etapa in list(flujo.etapas or []):
        if etapa.id not in etapas_keep:
            for est in list(etapa.estados or []):
                db.query(Transicion).filter(Transicion.estado_origen_id == est.id).delete()
                db.query(ApiRegla).filter(ApiRegla.estado_id == est.id).delete()
                db.query(DatoRegla).filter(DatoRegla.estado_id == est.id).delete()
                db.query(EstadoApiInput).filter(EstadoApiInput.estado_id == est.id).delete()
                db.query(EstadoApiOutput).filter(EstadoApiOutput.estado_id == est.id).delete()
                db.query(Transicion).filter(Transicion.estado_destino_id == est.id).delete()
                db.query(ApiRegla).filter(ApiRegla.estado_destino_id == est.id).delete()
                db.query(DatoRegla).filter(DatoRegla.estado_destino_id == est.id).delete()
            db.delete(etapa)
    db.flush()

    # --- 3. Transiciones y reglas (necesitan mapa completo de estados) ---
    for ep in etapas_payload:
        for sp in ep.get("_estados_resolved") or []:
            estado_id = sp["_resolved_id"]
            # Replace-all transiciones del estado
            db.query(Transicion).filter(Transicion.estado_origen_id == estado_id).delete()
            seen_dest: set[int] = set()
            for tr in sp.get("transiciones") or []:
                dest_key = str(tr.get("estado_destino_key") or tr.get("estado_destino_id") or "")
                dest_id = estado_key_to_id.get(dest_key) or _as_int(tr.get("estado_destino_id"))
                if not dest_id or dest_id in seen_dest:
                    continue
                dest = db.get(Estado, dest_id)
                if not dest:
                    continue
                seen_dest.add(dest_id)
                db.add(
                    Transicion(
                        estado_origen_id=estado_id,
                        etapa_destino_id=dest.etapa_id,
                        estado_destino_id=dest_id,
                    )
                )

            db.query(ApiRegla).filter(ApiRegla.estado_id == estado_id).delete()
            for ri, rg in enumerate(sp.get("reglas") or [], start=1):
                dest_key = str(rg.get("estado_destino_key") or rg.get("estado_destino_id") or "")
                dest_id = estado_key_to_id.get(dest_key) or _as_int(rg.get("estado_destino_id"))
                if not dest_id:
                    continue
                dest = db.get(Estado, dest_id)
                if not dest:
                    continue
                conds_raw = list(rg.get("condiciones") or [])
                if not conds_raw and rg.get("output_id"):
                    conds_raw = [
                        {
                            "output_id": rg.get("output_id"),
                            "operador": rg.get("operador") or "=",
                            "valor": rg.get("valor") or "",
                        }
                    ]
                conds = []
                for c in conds_raw:
                    oid = _as_int(c.get("output_id"))
                    if not oid:
                        continue
                    conds.append(
                        {
                            "output_id": oid,
                            "operador": (str(c.get("operador") or "=").strip() or "="),
                            "valor": str(c.get("valor") if c.get("valor") is not None else ""),
                        }
                    )
                if not conds:
                    continue
                first = conds[0]
                regla = ApiRegla(
                    estado_id=estado_id,
                    output_id=first["output_id"],
                    operador=first["operador"],
                    valor=first["valor"],
                    etapa_destino_id=dest.etapa_id,
                    estado_destino_id=dest_id,
                    prioridad=int(rg.get("prioridad") or ri),
                    logica=(str(rg.get("logica") or "AND").strip().upper() or "AND"),
                    modo_ejecucion=(
                        str(rg.get("modo_ejecucion") or "AUTO").strip().upper() or "AUTO"
                    ),
                    nombre=(str(rg.get("nombre") or "").strip() or None),
                )
                db.add(regla)
                db.flush()
                for c in conds:
                    db.add(
                        ApiReglaCondicion(
                            regla_id=regla.id,
                            output_id=c["output_id"],
                            operador=c["operador"],
                            valor=c["valor"],
                        )
                    )
            # Reglas por datos adicionales (AND/OR + condiciones)
            db.query(DatoRegla).filter(DatoRegla.estado_id == estado_id).delete()
            for ri, rg in enumerate(sp.get("reglas_datos") or [], start=1):
                dest_key = str(rg.get("estado_destino_key") or rg.get("estado_destino_id") or "")
                dest_id = estado_key_to_id.get(dest_key) or _as_int(rg.get("estado_destino_id"))
                if not dest_id:
                    continue
                dest = db.get(Estado, dest_id)
                if not dest:
                    continue
                regla = DatoRegla(
                    estado_id=estado_id,
                    nombre=(str(rg.get("nombre") or "").strip() or None),
                    logica=(str(rg.get("logica") or "AND").strip().upper() or "AND"),
                    prioridad=int(rg.get("prioridad") or ri),
                    es_default=bool(rg.get("es_default")),
                    etapa_destino_id=dest.etapa_id,
                    estado_destino_id=dest_id,
                )
                db.add(regla)
                db.flush()
                for c in rg.get("condiciones") or []:
                    did = _as_int(c.get("dato_id"))
                    if not did:
                        continue
                    db.add(
                        DatoReglaCondicion(
                            regla_id=regla.id,
                            dato_id=did,
                            operador=(str(c.get("operador") or "==").strip() or "=="),
                            valor=str(c.get("valor") if c.get("valor") is not None else ""),
                            valor_hasta=(
                                str(c.get("valor_hasta"))
                                if c.get("valor_hasta") not in (None, "")
                                else None
                            ),
                        )
                    )

            # Mapeos input/output del API del estado
            db.query(EstadoApiInput).filter(EstadoApiInput.estado_id == estado_id).delete()
            db.query(EstadoApiOutput).filter(EstadoApiOutput.estado_id == estado_id).delete()
            if sp.get("api_call_id"):
                for mi in sp.get("mapeos_input") or []:
                    pid = _as_int(mi.get("parametro_id"))
                    if not pid:
                        continue
                    origen = (str(mi.get("origen") or "fijo").strip().lower() or "fijo")
                    db.add(
                        EstadoApiInput(
                            estado_id=estado_id,
                            parametro_id=pid,
                            origen=origen,
                            valor_fijo=(
                                str(mi.get("valor_fijo") or "").strip() or None
                                if origen == "fijo"
                                else None
                            ),
                            dato_id=_as_int(mi.get("dato_id")) if origen == "dato" else None,
                            campo_caso=(
                                str(mi.get("campo_caso") or "").strip() or None
                                if origen in ("caso", "cliente")
                                else None
                            ),
                        )
                    )
                seen_out: set[int] = set()
                for mo in sp.get("mapeos_output") or []:
                    oid = _as_int(mo.get("output_id"))
                    did = _as_int(mo.get("dato_id"))
                    if not oid or not did or oid in seen_out:
                        continue
                    seen_out.add(oid)
                    db.add(
                        EstadoApiOutput(
                            estado_id=estado_id,
                            output_id=oid,
                            dato_id=did,
                        )
                    )

    db.commit()
    flujo = cargar_flujo_completo(db, flujo_id)
    return serializar_flujo(flujo)


def catalogos_editor(db: Session) -> dict[str, Any]:
    from app.models import DatoComplementario, Documento, TipoFlujo
    from app.services.dato_formato import tipo_codigo
    from sqlalchemy.orm import selectinload as _selectinload

    apis = (
        db.query(ApiCall)
        .options(
            _selectinload(ApiCall.outputs),
            _selectinload(ApiCall.parametros),
        )
        .filter(ApiCall.activo == True)  # noqa: E712
        .order_by(ApiCall.nombre)
        .all()
    )
    datos_catalogo = [
        {
            "id": d.id,
            "nombre": d.nombre,
            "codigo": (cod := tipo_codigo(d.tipo_dato)),
            "tipo": (d.tipo_dato.nombre if d.tipo_dato else "") or "",
            "es_booleano": cod == "booleano",
        }
        for d in db.query(DatoComplementario)
        .options(_selectinload(DatoComplementario.tipo_dato))
        .filter(DatoComplementario.activo == True)  # noqa: E712
        .order_by(DatoComplementario.nombre)
    ]
    return {
        "tipos_flujo": [{"id": t.id, "nombre": t.nombre} for t in db.query(TipoFlujo).order_by(TipoFlujo.nombre)],
        "apis": [
            {
                "id": a.id,
                "nombre": a.nombre,
                "metodo": a.metodo,
                "url": a.url,
                "parametros": [
                    {
                        "id": p.id,
                        "nombre": p.nombre,
                        "ubicacion": p.ubicacion,
                        "origen": p.origen,
                        "valor_fijo": p.valor_fijo or "",
                        "dato_id": p.dato_id,
                        "campo_caso": p.campo_caso or "",
                    }
                    for p in (a.parametros or [])
                ],
                "outputs": [
                    {
                        "id": o.id,
                        "nombre": o.nombre,
                        "json_path": o.json_path,
                        "formato": o.formato,
                    }
                    for o in (a.outputs or [])
                ],
            }
            for a in apis
        ],
        "campos_caso": [{"id": k, "nombre": n} for k, n in CAMPOS_CASO],
        "documentos": [
            {"id": d.id, "nombre": d.nombre}
            for d in db.query(Documento).filter(Documento.activo == True).order_by(Documento.nombre)  # noqa: E712
        ],
        "datos": [
            {**d, "operadores": operadores_para_codigo(d["codigo"])}
            for d in datos_catalogo
        ],
        "booleano_ids": [d["id"] for d in datos_catalogo if d["es_booleano"]],
        "grupos": [
            {"id": g.id, "nombre": g.nombre}
            for g in db.query(GrupoUsuario).order_by(GrupoUsuario.nombre)
        ],
        "operadores": ["=", "!=", ">", ">=", "<", "<=", "contiene"],
        "operadores_datos": {
            "numero": list(OPS_NUMERO),
            "texto": list(OPS_TEXTO),
            "booleano": list(OPS_BOOL),
        },
    }
