"""
Seed de presentación Helios: APIs, catálogo, flujo BPM, grupo y casos dummy.

Idempotente. Se invoca desde helios_bridge / init_helios_db / CLI.
"""
from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    ApiCall,
    ApiOutput,
    ApiParametro,
    ApiRegla,
    Caso,
    CasoApiLog,
    CasoDato,
    Cliente,
    DatoComplementario,
    Documento,
    Estado,
    EstadoApiInput,
    EstadoApiOutput,
    Etapa,
    EtapaDato,
    EtapaDocumento,
    EtapaGrupo,
    Flujo,
    GrupoUsuario,
    GrupoXUsuario,
    TipoDato,
    TipoFlujo,
    Transicion,
    Usuario,
)
from app.seed import ensure_tipos_dato

# motor import no requerido: casos demo se crean con IDs explicitos (SQLite BigInt)

FLUJO_NOMBRE = "Demo Originacion TDC"
GRUPO_NOMBRE = "Demo Operaciones"

HEADERS_JSON = (
    '{"Authorization":"Bearer test-token-123","Content-Type":"application/json"}'
)

DEMO_CLIENTES = [
    ("001-1234567-8", "Ana María Pérez Rosario", "809-555-0101"),
    ("002-9876543-2", "Carlos Enrique Méndez Ruiz", "829-555-0202"),
    ("003-4567890-1", "Laura Beatriz Fernández Díaz", "849-555-0303"),
]

DATOS_DEMO = [
    ("Salario", 8, "Ingreso mensual del solicitante (DOP)"),
    ("Asalariado", 4, "Indica si es asalariado"),
    ("Tiempo laborando (meses)", 2, "Antigüedad laboral en meses"),
    ("Score Buró", 2, "Score del reporte de buró (API)"),
    ("Chance Favor", 2, "Chance a favor (API buró)"),
    ("EIC Máximo", 8, "EIC máximo reportado (API)"),
    ("Mora Máx Días", 2, "Mora máxima en días (API)"),
    ("Dictamen Buró", 1, "OK | ALERTA | RIESGO (API)"),
    ("Resumen Buró", 1, "Resumen textual del buró (API)"),
    ("Cuentas Abiertas", 2, "Cantidad de cuentas abiertas (API)"),
    ("Dictamen Motor", 1, "APROBADA | REFERIDA | DECLINADA (API)"),
    ("Monto Aprobado DOP", 8, "Monto sugerido en DOP (API)"),
    ("Monto Aprobado USD", 8, "Monto sugerido en USD (API)"),
    ("Razón Motor", 1, "Motivo del dictamen del motor (API)"),
]

DOCS_DEMO = [
    ("Cédula de identidad", "Documento de identidad del solicitante"),
    ("Carta laboral", "Constancia de empleo e ingresos"),
]


def resolve_demo_api_base(base_url: str | None = None) -> str:
    if base_url:
        return base_url.rstrip("/")
    env = os.environ.get("DEMO_API_BASE_URL")
    if env:
        return env.rstrip("/")
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN") or ""
    if domain.strip():
        d = domain.strip()
        if not d.startswith("http"):
            d = "https://" + d
        return d.rstrip("/")
    # Fallback presentación NOVA en Railway
    if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"):
        return "https://novadata-projects-production.up.railway.app"
    return "http://127.0.0.1:5012"


def _log(msg: str) -> None:
    print(f"[helios-demo] {msg}")


def _ensure_clientes(db: Session) -> dict[str, Cliente]:
    out: dict[str, Cliente] = {}
    for ident, nombre, tel in DEMO_CLIENTES:
        c = db.query(Cliente).filter(Cliente.identificacion == ident).first()
        if c is None:
            c = Cliente(
                nombre_completo=nombre,
                tipo_identificacion="Cedula",
                identificacion=ident,
                telefono=tel,
                correo=f"{ident.replace('-', '')}@demo.nova.local",
            )
            db.add(c)
            db.flush()
            _log(f"+ cliente {ident}")
        out[ident] = c
    return out


def _ensure_api(
    db: Session,
    *,
    nombre: str,
    descripcion: str,
    url: str,
    parametros: list[dict],
    outputs: list[dict],
) -> ApiCall:
    """Upsert API sin borrar params/outputs (evita romper FKs de reglas/mapeos)."""
    api = db.query(ApiCall).filter(ApiCall.nombre == nombre).first()
    if api is None:
        api = ApiCall(
            nombre=nombre,
            descripcion=descripcion,
            metodo="POST",
            url=url,
            headers_json=HEADERS_JSON,
            timeout_seg=30,
            activo=True,
        )
        db.add(api)
        db.flush()
        _log(f"+ API {nombre} id={api.id}")
    else:
        api.descripcion = descripcion
        api.metodo = "POST"
        api.url = url
        api.headers_json = HEADERS_JSON
        api.timeout_seg = 30
        api.activo = True
        _log(f"~ API {nombre} id={api.id}")

    existing_params = {p.nombre: p for p in (api.parametros or [])}
    for p in parametros:
        row = existing_params.get(p["nombre"])
        if row is None:
            db.add(
                ApiParametro(
                    api_id=api.id,
                    nombre=p["nombre"],
                    ubicacion=p.get("ubicacion", "body"),
                    origen=p.get("origen", "dato"),
                    valor_fijo=p.get("valor_fijo"),
                    campo_caso=p.get("campo_caso"),
                    dato_id=p.get("dato_id"),
                )
            )
        else:
            row.ubicacion = p.get("ubicacion", "body")
            row.origen = p.get("origen", "dato")
            row.valor_fijo = p.get("valor_fijo")
            row.campo_caso = p.get("campo_caso")
            if p.get("dato_id") is not None:
                row.dato_id = p.get("dato_id")

    existing_outs = {o.nombre: o for o in (api.outputs or [])}
    for o in outputs:
        row = existing_outs.get(o["nombre"])
        if row is None:
            db.add(
                ApiOutput(
                    api_id=api.id,
                    nombre=o["nombre"],
                    json_path=o["json_path"],
                    formato=o.get("formato", "texto"),
                )
            )
        else:
            row.json_path = o["json_path"]
            row.formato = o.get("formato", "texto")
    db.flush()
    return api


def _ensure_tipo_flujo(db: Session) -> TipoFlujo:
    tf = db.query(TipoFlujo).filter(TipoFlujo.nombre == "Credito").first()
    if tf is None:
        tf = TipoFlujo(nombre="Credito")
        db.add(tf)
        db.flush()
    return tf


def _ensure_dato(db: Session, nombre: str, tipo_id: int, descripcion: str | None) -> DatoComplementario:
    d = db.query(DatoComplementario).filter(DatoComplementario.nombre == nombre).first()
    if d is None:
        if db.get(TipoDato, tipo_id) is None:
            raise RuntimeError(f"Falta TipoDato id={tipo_id}")
        d = DatoComplementario(
            nombre=nombre,
            descripcion=descripcion,
            tipo_dato_id=tipo_id,
            activo=True,
            decimales=2 if tipo_id in (6, 8, 9) else None,
        )
        db.add(d)
        db.flush()
        _log(f"+ dato {nombre}")
    else:
        d.descripcion = descripcion or d.descripcion
        d.tipo_dato_id = tipo_id
        d.activo = True
    return d


def _ensure_docs(db: Session) -> dict[str, Documento]:
    out: dict[str, Documento] = {}
    for nombre, desc in DOCS_DEMO:
        d = db.query(Documento).filter(Documento.nombre == nombre).first()
        if d is None:
            d = Documento(nombre=nombre, descripcion=desc, activo=True)
            db.add(d)
            db.flush()
            _log(f"+ documento {nombre}")
        else:
            d.descripcion = desc
            d.activo = True
        out[nombre] = d
    return out


def _ensure_grupo(db: Session) -> GrupoUsuario:
    g = db.query(GrupoUsuario).filter(GrupoUsuario.nombre == GRUPO_NOMBRE).first()
    if g is None:
        g = GrupoUsuario(nombre=GRUPO_NOMBRE, descripcion="Grupo operativo para demo Helios")
        db.add(g)
        db.flush()
        _log(f"+ grupo {GRUPO_NOMBRE}")
    admin = db.query(Usuario).filter(Usuario.usuario_ad == "admin").first()
    if admin is not None:
        link = (
            db.query(GrupoXUsuario)
            .filter(GrupoXUsuario.grupo_id == g.id, GrupoXUsuario.usuario_id == admin.id)
            .first()
        )
        if link is None:
            db.add(GrupoXUsuario(grupo_id=g.id, usuario_id=admin.id))
    return g


def _vincular_params(db: Session, datos: dict[str, DatoComplementario]) -> tuple[ApiCall, ApiCall]:
    motor_api = db.query(ApiCall).filter(ApiCall.nombre == "Demo Motor Credito").one()
    buro_api = db.query(ApiCall).filter(ApiCall.nombre == "Demo Buro Reporte").one()
    mapping = {
        "salario": datos["Salario"].id,
        "es_asalariado": datos["Asalariado"].id,
        "tiempo_laborando": datos["Tiempo laborando (meses)"].id,
    }
    for p in motor_api.parametros or []:
        if p.nombre in mapping:
            p.origen = "dato"
            p.dato_id = mapping[p.nombre]
            p.campo_caso = None
        elif p.nombre == "cedula":
            p.origen = "caso"
            p.campo_caso = "cliente_identificacion"
            p.dato_id = None
    for p in buro_api.parametros or []:
        if p.nombre == "cedula":
            p.origen = "caso"
            p.campo_caso = "cliente_identificacion"
            p.dato_id = None
    return motor_api, buro_api


def _output(api: ApiCall, nombre: str) -> ApiOutput:
    for o in api.outputs or []:
        if o.nombre == nombre:
            return o
    raise RuntimeError(f"API {api.nombre} sin output {nombre}")


def _purge_flujo(db: Session, flujo: Flujo) -> None:
    caso_ids = [c.id for c in db.query(Caso).filter(Caso.flujo_id == flujo.id).all()]
    if caso_ids:
        db.query(CasoApiLog).filter(CasoApiLog.caso_id.in_(caso_ids)).delete(
            synchronize_session=False
        )
        for c in db.query(Caso).filter(Caso.id.in_(caso_ids)).all():
            db.delete(c)
        db.flush()
    etapa_ids = [e.id for e in flujo.etapas]
    if etapa_ids:
        db.query(EtapaGrupo).filter(EtapaGrupo.etapa_id.in_(etapa_ids)).delete(
            synchronize_session=False
        )
    db.delete(flujo)
    db.flush()
    _log(f"~ eliminado flujo {FLUJO_NOMBRE}")


def _add_etapa_dato(db: Session, etapa: Etapa, dato: DatoComplementario, *, obligatorio: bool, orden: int) -> None:
    db.add(EtapaDato(etapa_id=etapa.id, dato_id=dato.id, obligatorio=obligatorio, orden=orden))


def _add_regla(
    db: Session,
    *,
    estado: Estado,
    output: ApiOutput,
    valor: str,
    etapa_dest: Etapa,
    estado_dest: Estado,
    prioridad: int,
    nombre: str,
) -> None:
    db.add(
        ApiRegla(
            estado_id=estado.id,
            output_id=output.id,
            operador="=",
            valor=valor,
            etapa_destino_id=etapa_dest.id,
            estado_destino_id=estado_dest.id,
            prioridad=prioridad,
            logica="AND",
            modo_ejecucion="AUTO",
            nombre=nombre,
        )
    )


def _build_flujo(
    db: Session,
    *,
    tipo: TipoFlujo,
    grupo: GrupoUsuario,
    datos: dict[str, DatoComplementario],
    docs: dict[str, Documento],
    api_motor: ApiCall,
    api_buro: ApiCall,
) -> Flujo:
    flujo = Flujo(
        tipo_flujo_id=tipo.id,
        nombre=FLUJO_NOMBRE,
        descripcion="Originacion TDC demo: captura -> buro -> motor -> dictamen final.",
        activo=True,
    )
    db.add(flujo)
    db.flush()

    e_captura = Etapa(
        flujo_id=flujo.id, nombre="Captura", descripcion="Datos laborales", orden=1, es_final=False
    )
    e_buro = Etapa(
        flujo_id=flujo.id, nombre="Consulta Buro", descripcion="Reporte buro demo", orden=2, es_final=False, permite_retroceso=True
    )
    e_eval = Etapa(
        flujo_id=flujo.id, nombre="Evaluacion", descripcion="Motor de credito demo", orden=3, es_final=False
    )
    e_apr = Etapa(flujo_id=flujo.id, nombre="Aprobacion", descripcion="Caso aprobado", orden=4, es_final=True)
    e_ref = Etapa(
        flujo_id=flujo.id, nombre="Comite / Referimiento", descripcion="Referido a comite", orden=5, es_final=True
    )
    e_dec = Etapa(flujo_id=flujo.id, nombre="Declinada", descripcion="Caso declinado", orden=6, es_final=True)
    for e in (e_captura, e_buro, e_eval, e_apr, e_ref, e_dec):
        db.add(e)
    db.flush()

    for e in (e_captura, e_buro, e_eval, e_apr, e_ref, e_dec):
        db.add(EtapaGrupo(etapa_id=e.id, grupo_id=grupo.id))

    for nombre_doc, oblig in (("Cédula de identidad", True), ("Carta laboral", False)):
        db.add(
            EtapaDocumento(
                etapa_id=e_captura.id,
                documento_id=docs[nombre_doc].id,
                obligatorio=oblig,
            )
        )

    _add_etapa_dato(db, e_captura, datos["Salario"], obligatorio=True, orden=1)
    _add_etapa_dato(db, e_captura, datos["Asalariado"], obligatorio=True, orden=2)
    _add_etapa_dato(db, e_captura, datos["Tiempo laborando (meses)"], obligatorio=True, orden=3)

    for i, key in enumerate(
        [
            "Score Buró",
            "Chance Favor",
            "EIC Máximo",
            "Mora Máx Días",
            "Dictamen Buró",
            "Resumen Buró",
            "Cuentas Abiertas",
        ],
        start=1,
    ):
        _add_etapa_dato(db, e_buro, datos[key], obligatorio=False, orden=i)

    for i, key in enumerate(
        ["Dictamen Motor", "Monto Aprobado DOP", "Monto Aprobado USD", "Razón Motor"],
        start=1,
    ):
        _add_etapa_dato(db, e_eval, datos[key], obligatorio=False, orden=i)

    st_cap_ini = Estado(etapa_id=e_captura.id, nombre="En captura", es_inicial=True, cierra_etapa=False)
    st_cap_ok = Estado(etapa_id=e_captura.id, nombre="Lista para buro", es_inicial=False, cierra_etapa=True)
    st_buro = Estado(
        etapa_id=e_buro.id, nombre="Consultando", es_inicial=True, cierra_etapa=False, api_call_id=api_buro.id
    )
    st_eval = Estado(
        etapa_id=e_eval.id, nombre="Ejecutando motor", es_inicial=True, cierra_etapa=False, api_call_id=api_motor.id
    )
    st_apr = Estado(etapa_id=e_apr.id, nombre="Aprobada", es_inicial=True, cierra_etapa=True)
    st_ref = Estado(etapa_id=e_ref.id, nombre="Referida", es_inicial=True, cierra_etapa=True)
    st_dec = Estado(etapa_id=e_dec.id, nombre="Declinada", es_inicial=True, cierra_etapa=True)
    for s in (st_cap_ini, st_cap_ok, st_buro, st_eval, st_apr, st_ref, st_dec):
        db.add(s)
    db.flush()

    db.add(
        Transicion(
            estado_origen_id=st_cap_ini.id,
            etapa_destino_id=e_captura.id,
            estado_destino_id=st_cap_ok.id,
        )
    )
    db.add(
        Transicion(
            estado_origen_id=st_cap_ok.id,
            etapa_destino_id=e_buro.id,
            estado_destino_id=st_buro.id,
        )
    )

    for p in api_buro.parametros or []:
        if p.nombre == "cedula":
            db.add(
                EstadoApiInput(
                    estado_id=st_buro.id,
                    parametro_id=p.id,
                    origen="caso",
                    campo_caso="cliente_identificacion",
                )
            )
    for out_name, dato_name in {
        "Score": "Score Buró",
        "ChanceFavor": "Chance Favor",
        "EicMax": "EIC Máximo",
        "MoraMaxDias": "Mora Máx Días",
        "DictamenBuro": "Dictamen Buró",
        "Resumen": "Resumen Buró",
        "CuentasAbiertas": "Cuentas Abiertas",
    }.items():
        db.add(
            EstadoApiOutput(
                estado_id=st_buro.id,
                output_id=_output(api_buro, out_name).id,
                dato_id=datos[dato_name].id,
            )
        )

    out_db = _output(api_buro, "DictamenBuro")
    for i, val in enumerate(("OK", "ALERTA", "RIESGO"), start=1):
        _add_regla(
            db,
            estado=st_buro,
            output=out_db,
            valor=val,
            etapa_dest=e_eval,
            estado_dest=st_eval,
            prioridad=i,
            nombre=f"Buro {val} -> Evaluacion",
        )

    motor_in = {
        "salario": ("dato", datos["Salario"].id, None),
        "es_asalariado": ("dato", datos["Asalariado"].id, None),
        "tiempo_laborando": ("dato", datos["Tiempo laborando (meses)"].id, None),
        "cedula": ("caso", None, "cliente_identificacion"),
    }
    for p in api_motor.parametros or []:
        if p.nombre not in motor_in:
            continue
        origen, dato_id, campo = motor_in[p.nombre]
        db.add(
            EstadoApiInput(
                estado_id=st_eval.id,
                parametro_id=p.id,
                origen=origen,
                dato_id=dato_id,
                campo_caso=campo,
            )
        )
    for out_name, dato_name in {
        "Dictamen": "Dictamen Motor",
        "Monto_DOP": "Monto Aprobado DOP",
        "Monto_USD": "Monto Aprobado USD",
        "Razon": "Razón Motor",
    }.items():
        db.add(
            EstadoApiOutput(
                estado_id=st_eval.id,
                output_id=_output(api_motor, out_name).id,
                dato_id=datos[dato_name].id,
            )
        )

    out_dictamen = _output(api_motor, "Dictamen")
    for valor, etapa_d, estado_d, prio, nom in (
        ("APROBADA", e_apr, st_apr, 1, "Motor APROBADA"),
        ("REFERIDA", e_ref, st_ref, 2, "Motor REFERIDA"),
        ("DECLINADA", e_dec, st_dec, 3, "Motor DECLINADA"),
    ):
        _add_regla(
            db,
            estado=st_eval,
            output=out_dictamen,
            valor=valor,
            etapa_dest=etapa_d,
            estado_dest=estado_d,
            prioridad=prio,
            nombre=nom,
        )

    _log(f"+ flujo {FLUJO_NOMBRE} id={flujo.id}")
    return flujo


def _set_dato(
    db: Session,
    caso: Caso,
    dato: DatoComplementario,
    valor: str,
    usuario: Usuario,
    *,
    next_dato_id: list[int],
) -> None:
    row = (
        db.query(CasoDato)
        .filter(CasoDato.caso_id == caso.id, CasoDato.dato_id == dato.id)
        .first()
    )
    if row is None:
        next_dato_id[0] += 1
        db.add(
            CasoDato(
                id=next_dato_id[0],
                caso_id=caso.id,
                dato_id=dato.id,
                etapa_id=caso.etapa_actual_id,
                valor=valor,
                usuario_adicion_id=usuario.id,
            )
        )
        db.flush()
    else:
        row.valor = valor


def _mover(
    db: Session,
    caso: Caso,
    etapa: Etapa,
    estado: Estado,
    usuario: Usuario,
    comentario: str,
    *,
    next_hist_id: list[int],
) -> None:
    from app.models import CasoHistorial

    caso.etapa_actual_id = etapa.id
    caso.estado_actual_id = estado.id
    next_hist_id[0] += 1
    db.add(
        CasoHistorial(
            id=next_hist_id[0],
            caso_id=caso.id,
            etapa_id=etapa.id,
            estado_id=estado.id,
            usuario_id=usuario.id,
            comentario=comentario,
            origen="SISTEMA",
        )
    )
    db.flush()


def _etapa_por_orden(flujo: Flujo, orden: int) -> Etapa:
    for e in flujo.etapas:
        if e.orden == orden:
            return e
    raise RuntimeError(f"Etapa orden={orden} no encontrada")


def _estado_inicial(etapa: Etapa) -> Estado:
    for s in etapa.estados:
        if s.es_inicial:
            return s
    if etapa.estados:
        return etapa.estados[0]
    raise RuntimeError(f"Etapa {etapa.nombre} sin estados")


def _ensure_casos_demo(
    db: Session,
    flujo: Flujo,
    clientes: dict[str, Cliente],
    datos: dict[str, DatoComplementario],
) -> None:
    if db.query(Caso).filter(Caso.flujo_id == flujo.id).count() > 0:
        _log("casos demo ya existen; omitidos")
        return

    admin = db.query(Usuario).filter(Usuario.usuario_ad == "admin").first()
    if admin is None:
        _log("sin admin; no se crean casos")
        return

    e_cap = _etapa_por_orden(flujo, 1)
    e_buro = _etapa_por_orden(flujo, 2)
    e_apr = _etapa_por_orden(flujo, 4)
    st_cap = _estado_inicial(e_cap)
    st_buro = _estado_inicial(e_buro)
    st_apr = _estado_inicial(e_apr)

    from sqlalchemy import func
    from app.models import CasoHistorial

    next_caso = [int(db.query(func.max(Caso.id)).scalar() or 0)]
    next_hist = [int(db.query(func.max(CasoHistorial.id)).scalar() or 0)]
    next_dato = [int(db.query(func.max(CasoDato.id)).scalar() or 0)]

    def _nuevo(cliente: Cliente) -> Caso:
        next_caso[0] += 1
        caso = Caso(
            id=next_caso[0],
            flujo_id=flujo.id,
            cliente_id=cliente.id,
            etapa_actual_id=e_cap.id,
            estado_actual_id=st_cap.id,
            creado_por_id=admin.id,
        )
        db.add(caso)
        db.flush()
        _mover(db, caso, e_cap, st_cap, admin, "Caso demo creado", next_hist_id=next_hist)
        return caso

    def _d(caso: Caso, key: str, valor: str) -> None:
        _set_dato(db, caso, datos[key], valor, admin, next_dato_id=next_dato)

    c1 = _nuevo(clientes["001-1234567-8"])
    _d(c1, "Salario", "45000")
    _d(c1, "Asalariado", "true")
    _d(c1, "Tiempo laborando (meses)", "24")
    _log(f"+ caso #{c1.id} Captura (Ana)")

    c2 = _nuevo(clientes["002-9876543-2"])
    _d(c2, "Salario", "28000")
    _d(c2, "Asalariado", "true")
    _d(c2, "Tiempo laborando (meses)", "10")
    _mover(db, c2, e_buro, st_buro, admin, "Demo: posicionado en Consulta Buro", next_hist_id=next_hist)
    _d(c2, "Score Buró", "640")
    _d(c2, "Chance Favor", "58")
    _d(c2, "EIC Máximo", "120000")
    _d(c2, "Mora Máx Días", "45")
    _d(c2, "Dictamen Buró", "ALERTA")
    _d(c2, "Resumen Buró", "Demo: mora reciente leve")
    _d(c2, "Cuentas Abiertas", "4")
    _log(f"+ caso #{c2.id} Consulta Buro (Carlos)")

    c3 = _nuevo(clientes["003-4567890-1"])
    _d(c3, "Salario", "62000")
    _d(c3, "Asalariado", "true")
    _d(c3, "Tiempo laborando (meses)", "48")
    _d(c3, "Score Buró", "782")
    _d(c3, "Dictamen Buró", "OK")
    _d(c3, "Dictamen Motor", "APROBADA")
    _d(c3, "Monto Aprobado DOP", "185000")
    _d(c3, "Monto Aprobado USD", "3217.39")
    _d(c3, "Razón Motor", "Demo: perfil solvente")
    _mover(db, c3, e_apr, st_apr, admin, "Demo: caso aprobado", next_hist_id=next_hist)
    c3.estado_general = "CERRADO"
    _log(f"+ caso #{c3.id} Aprobacion CERRADO (Laura)")


def run_seed_demo(
    db: Session,
    *,
    base_url: str | None = None,
    force: bool = False,
    with_casos: bool = True,
) -> dict[str, Any]:
    """Siembra catálogo + APIs + flujo (+ casos). No hace commit (el caller decide)."""
    base = resolve_demo_api_base(base_url)
    _log(f"base URL APIs: {base}")

    ensure_tipos_dato(db)
    clientes = _ensure_clientes(db)

    _ensure_api(
        db,
        nombre="Demo Motor Credito",
        descripcion="Motor demo: Dictamen APROBADA / REFERIDA / DECLINADA + montos.",
        url=f"{base}/demo-api/evaluacion",
        parametros=[
            {"nombre": "salario", "ubicacion": "body", "origen": "dato"},
            {"nombre": "es_asalariado", "ubicacion": "body", "origen": "dato"},
            {"nombre": "tiempo_laborando", "ubicacion": "body", "origen": "dato"},
            {
                "nombre": "cedula",
                "ubicacion": "body",
                "origen": "caso",
                "campo_caso": "cliente_identificacion",
            },
        ],
        outputs=[
            {"nombre": "Dictamen", "json_path": "Dictamen", "formato": "texto"},
            {"nombre": "Monto_DOP", "json_path": "Monto_DOP", "formato": "numero"},
            {"nombre": "Monto_USD", "json_path": "Monto_USD", "formato": "numero"},
            {"nombre": "Razon", "json_path": "Razon", "formato": "texto"},
        ],
    )
    _ensure_api(
        db,
        nombre="Demo Buro Reporte",
        descripcion="Buro demo: Score, ChanceFavor, MoraMaxDias, EIC, DictamenBuro.",
        url=f"{base}/demo-api/buro/reporte",
        parametros=[
            {
                "nombre": "cedula",
                "ubicacion": "body",
                "origen": "caso",
                "campo_caso": "cliente_identificacion",
            },
        ],
        outputs=[
            {"nombre": "Score", "json_path": "Score", "formato": "numero"},
            {"nombre": "ChanceFavor", "json_path": "ChanceFavor", "formato": "numero"},
            {"nombre": "EicMax", "json_path": "EicMax", "formato": "numero"},
            {"nombre": "MoraMaxDias", "json_path": "MoraMaxDias", "formato": "numero"},
            {"nombre": "DictamenBuro", "json_path": "DictamenBuro", "formato": "texto"},
            {"nombre": "Resumen", "json_path": "Resumen", "formato": "texto"},
            {"nombre": "CuentasAbiertas", "json_path": "CuentasAbiertas", "formato": "numero"},
        ],
    )

    tipo = _ensure_tipo_flujo(db)
    grupo = _ensure_grupo(db)
    docs = _ensure_docs(db)
    datos = {n: _ensure_dato(db, n, tid, desc) for n, tid, desc in DATOS_DEMO}
    api_motor, api_buro = _vincular_params(db, datos)

    existente = db.query(Flujo).filter(Flujo.nombre == FLUJO_NOMBRE).first()
    if existente is not None:
        n_casos = db.query(Caso).filter(Caso.flujo_id == existente.id).count()
        if n_casos and not force:
            _log(f"flujo ya existe id={existente.id} con {n_casos} caso(s)")
            # Asegura URLs de API actualizadas aunque el flujo no se recree
            if with_casos:
                _ensure_casos_demo(db, existente, clientes, datos)
            return {"flujo_id": existente.id, "created": False, "base_url": base}
        _purge_flujo(db, existente)

    flujo = _build_flujo(
        db,
        tipo=tipo,
        grupo=grupo,
        datos=datos,
        docs=docs,
        api_motor=api_motor,
        api_buro=api_buro,
    )
    if with_casos:
        _ensure_casos_demo(db, flujo, clientes, datos)
    return {"flujo_id": flujo.id, "created": True, "base_url": base}
