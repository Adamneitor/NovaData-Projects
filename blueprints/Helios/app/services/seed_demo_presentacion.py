"""
Seed de presentación Helios — flujo multi-rol + catálogos + casos.

Flujo «Demo Originacion TDC»:
  Ejecutivo → Documentación → Buró → Evaluación Motor
    → Aprobación Gerente | Comité Referimiento | Declinada
    → Formalización (si aprobado)

Roles/grupos: Ejecutivo de Servicio, Analista de Crédito,
Gerente Análisis de Crédito, Comité de Crédito, Operaciones Cierre.

Idempotente. CLI / helios_bridge / init_helios_db.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.config import AUTH_APP
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
from app.services.password_policy import hash_password

FLUJO_NOMBRE = "Demo Originacion TDC"

HEADERS_JSON = (
    '{"Authorization":"Bearer test-token-123","Content-Type":"application/json"}'
)

# (usuario_ad, nombre, password, perfil_id, grupo)
DEMO_USERS = [
    ("ejecutivo", "María López · Ejecutivo Servicio", "demo123", 4, "Ejecutivo de Servicio"),
    ("analista", "Pedro Gómez · Analista Crédito", "demo123", 4, "Analista de Crédito"),
    ("gerente", "Sofía Reyes · Gerente Análisis", "demo123", 4, "Gerente Análisis de Crédito"),
    ("comite", "Comité Crédito Demo", "demo123", 4, "Comité de Crédito"),
    ("operaciones", "Luis Méndez · Operaciones", "demo123", 4, "Operaciones Cierre"),
]

GRUPOS = [
    ("Ejecutivo de Servicio", "Captura y documentación con el cliente"),
    ("Analista de Crédito", "Consulta buró y evaluación motor"),
    ("Gerente Análisis de Crédito", "Aprueba originaciones sugeridas por motor"),
    ("Comité de Crédito", "Decide casos referidos"),
    ("Operaciones Cierre", "Formalización y cierre operativo"),
]

DEMO_CLIENTES = [
    ("001-1234567-8", "Ana María Pérez Rosario", "809-555-0101"),
    ("002-9876543-2", "Carlos Enrique Méndez Ruiz", "829-555-0202"),
    ("003-4567890-1", "Laura Beatriz Fernández Díaz", "849-555-0303"),
    ("004-1112233-4", "José Miguel Santos Peña", "809-555-0404"),
    ("005-2223344-5", "Patricia Elena Vargas Núñez", "829-555-0505"),
    ("006-3334455-6", "Ricardo Antonio Cruz Mejía", "849-555-0606"),
    ("007-4445566-7", "Carmen Isabel Torres Acosta", "809-555-0707"),
    ("008-5556677-8", "Miguel Ángel Rosario Feliz", "829-555-0808"),
    ("009-6667788-9", "Yolanda Mercedes Díaz Polanco", "849-555-0909"),
    ("010-7778899-0", "Francisco Javier Peña Ortiz", "809-555-1010"),
    ("011-8889900-1", "Empresa Demo SRL", "809-555-1111"),
    ("012-9990011-2", "Inversiones Nova RD", "829-555-1212"),
]

DATOS_DEMO = [
    ("Producto solicitado", 5, "Tipo de producto TDC"),
    ("Monto solicitado DOP", 8, "Monto que pide el cliente"),
    ("Salario", 8, "Ingreso mensual del solicitante (DOP)"),
    ("Asalariado", 4, "Indica si es asalariado"),
    ("Tiempo laborando (meses)", 2, "Antigüedad laboral en meses"),
    ("Empleador", 1, "Nombre del empleador"),
    ("Observación ejecutivo", 1, "Notas de captura"),
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
    ("Dictamen Gerente", 5, "Confirma o ajusta la aprobación"),
    ("Comentario Gerente", 1, "Justificación gerencial"),
    ("Dictamen Comité", 5, "Resolución del comité"),
    ("Motivo Decl Soft", 1, "Motivo de declinación"),
]

DOCS_DEMO = [
    ("Cédula de identidad", "Documento de identidad del solicitante"),
    ("Carta laboral", "Constancia de empleo e ingresos"),
    ("Estado de cuenta", "Extracto bancario reciente"),
    ("Formulario KYC", "Conozca su cliente firmado"),
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
                tipo_identificacion="Cedula" if not ident.startswith("01") else "Cedula",
                identificacion=ident,
                telefono=tel,
                correo=f"{ident.replace('-', '')}@demo.nova.local",
            )
            # RNC-like for empresas
            if "SRL" in nombre or "Inversiones" in nombre:
                c.tipo_identificacion = "RNC"
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
        opts = None
        if nombre == "Producto solicitado":
            opts = "TDC Clasica;TDC Gold;TDC Platinum;TDC Empresarial"
        elif nombre == "Dictamen Gerente":
            opts = "Confirmar aprobacion;Ajustar monto;Enviar a comite"
        elif nombre == "Dictamen Comité":
            opts = "Aprobar;Declinar;Solicitar info"
        d = DatoComplementario(
            nombre=nombre,
            descripcion=descripcion,
            tipo_dato_id=tipo_id,
            opciones=opts,
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


def _ensure_grupos_y_users(db: Session) -> dict[str, GrupoUsuario]:
    grupos: dict[str, GrupoUsuario] = {}
    for nombre, desc in GRUPOS:
        g = db.query(GrupoUsuario).filter(GrupoUsuario.nombre == nombre).first()
        if g is None:
            g = GrupoUsuario(nombre=nombre, descripcion=desc)
            db.add(g)
            db.flush()
            _log(f"+ grupo {nombre}")
        grupos[nombre] = g

    # Admin en todos los grupos (puede operar la demo completa)
    admin = db.query(Usuario).filter(Usuario.usuario_ad == "admin").first()
    if admin:
        for g in grupos.values():
            link = (
                db.query(GrupoXUsuario)
                .filter(GrupoXUsuario.grupo_id == g.id, GrupoXUsuario.usuario_id == admin.id)
                .first()
            )
            if link is None:
                db.add(GrupoXUsuario(grupo_id=g.id, usuario_id=admin.id))

    for user_ad, nombre, pwd, perfil, gname in DEMO_USERS:
        u = db.query(Usuario).filter(Usuario.usuario_ad == user_ad).first()
        if u is None:
            u = Usuario(
                usuario_ad=user_ad,
                nombre=nombre,
                tipo_autenticacion=AUTH_APP,
                password_hash=hash_password(pwd),
                debe_cambiar_password=False,
                password_fecha_cambio=datetime.now(),
                perfil_id=perfil,
                activo=True,
            )
            db.add(u)
            db.flush()
            _log(f"+ usuario {user_ad} / {pwd}")
        g = grupos[gname]
        link = (
            db.query(GrupoXUsuario)
            .filter(GrupoXUsuario.grupo_id == g.id, GrupoXUsuario.usuario_id == u.id)
            .first()
        )
        if link is None:
            db.add(GrupoXUsuario(grupo_id=g.id, usuario_id=u.id))
    return grupos


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
    grupos: dict[str, GrupoUsuario],
    datos: dict[str, DatoComplementario],
    docs: dict[str, Documento],
    api_motor: ApiCall,
    api_buro: ApiCall,
) -> Flujo:
    flujo = Flujo(
        tipo_flujo_id=tipo.id,
        nombre=FLUJO_NOMBRE,
        descripcion=(
            "Originacion TDC multi-rol: Ejecutivo captura → Analista buró/motor → "
            "Gerente aprueba | Comité refiere | Declinada | Formalización."
        ),
        activo=True,
    )
    db.add(flujo)
    db.flush()

    # Etapas
    e_cap = Etapa(flujo_id=flujo.id, nombre="1. Captura", descripcion="Ejecutivo de Servicio", orden=1)
    e_doc = Etapa(flujo_id=flujo.id, nombre="2. Documentacion", descripcion="KYC y evidencias", orden=2, permite_retroceso=True)
    e_buro = Etapa(flujo_id=flujo.id, nombre="3. Consulta Buro", descripcion="Analista · API buró", orden=3)
    e_eval = Etapa(flujo_id=flujo.id, nombre="4. Evaluacion Motor", descripcion="Analista · API motor", orden=4)
    e_apr = Etapa(flujo_id=flujo.id, nombre="5. Aprobacion Gerente", descripcion="Gerente Análisis", orden=5, permite_retroceso=True)
    e_ref = Etapa(flujo_id=flujo.id, nombre="5b. Comite / Referimiento", descripcion="Comité de Crédito", orden=6, es_final=False)
    e_dec = Etapa(flujo_id=flujo.id, nombre="5c. Declinada", descripcion="Cierre declinado", orden=7, es_final=True)
    e_form = Etapa(flujo_id=flujo.id, nombre="6. Formalizacion", descripcion="Operaciones · cierre", orden=8, es_final=True)
    for e in (e_cap, e_doc, e_buro, e_eval, e_apr, e_ref, e_dec, e_form):
        db.add(e)
    db.flush()

    # Grupos por etapa
    asign = {
        e_cap: ["Ejecutivo de Servicio"],
        e_doc: ["Ejecutivo de Servicio"],
        e_buro: ["Analista de Crédito"],
        e_eval: ["Analista de Crédito"],
        e_apr: ["Gerente Análisis de Crédito"],
        e_ref: ["Comité de Crédito", "Gerente Análisis de Crédito"],
        e_dec: ["Analista de Crédito", "Gerente Análisis de Crédito"],
        e_form: ["Operaciones Cierre"],
    }
    for etapa, names in asign.items():
        for n in names:
            db.add(EtapaGrupo(etapa_id=etapa.id, grupo_id=grupos[n].id))

    # Docs
    db.add(EtapaDocumento(etapa_id=e_cap.id, documento_id=docs["Cédula de identidad"].id, obligatorio=True))
    db.add(EtapaDocumento(etapa_id=e_doc.id, documento_id=docs["Carta laboral"].id, obligatorio=True))
    db.add(EtapaDocumento(etapa_id=e_doc.id, documento_id=docs["Estado de cuenta"].id, obligatorio=False))
    db.add(EtapaDocumento(etapa_id=e_doc.id, documento_id=docs["Formulario KYC"].id, obligatorio=True))

    # Datos captura
    for i, key in enumerate(
        ["Producto solicitado", "Monto solicitado DOP", "Salario", "Asalariado", "Tiempo laborando (meses)", "Empleador", "Observación ejecutivo"],
        start=1,
    ):
        _add_etapa_dato(db, e_cap, datos[key], obligatorio=key != "Observación ejecutivo", orden=i)

    for i, key in enumerate(
        ["Score Buró", "Chance Favor", "EIC Máximo", "Mora Máx Días", "Dictamen Buró", "Resumen Buró", "Cuentas Abiertas"],
        start=1,
    ):
        _add_etapa_dato(db, e_buro, datos[key], obligatorio=False, orden=i)

    for i, key in enumerate(
        ["Dictamen Motor", "Monto Aprobado DOP", "Monto Aprobado USD", "Razón Motor"],
        start=1,
    ):
        _add_etapa_dato(db, e_eval, datos[key], obligatorio=False, orden=i)

    _add_etapa_dato(db, e_apr, datos["Dictamen Gerente"], obligatorio=True, orden=1)
    _add_etapa_dato(db, e_apr, datos["Comentario Gerente"], obligatorio=False, orden=2)
    _add_etapa_dato(db, e_ref, datos["Dictamen Comité"], obligatorio=True, orden=1)
    _add_etapa_dato(db, e_dec, datos["Motivo Decl Soft"], obligatorio=False, orden=1)

    # Estados
    st_cap_ini = Estado(etapa_id=e_cap.id, nombre="En captura", es_inicial=True)
    st_cap_ok = Estado(etapa_id=e_cap.id, nombre="Captura completa", cierra_etapa=True)
    st_doc_ini = Estado(etapa_id=e_doc.id, nombre="Pendiente documentos", es_inicial=True)
    st_doc_ok = Estado(etapa_id=e_doc.id, nombre="Documentacion OK", cierra_etapa=True)
    st_buro = Estado(etapa_id=e_buro.id, nombre="Consultando buro", es_inicial=True, api_call_id=api_buro.id)
    st_eval = Estado(etapa_id=e_eval.id, nombre="Ejecutando motor", es_inicial=True, api_call_id=api_motor.id)
    st_apr_ini = Estado(etapa_id=e_apr.id, nombre="Pendiente gerente", es_inicial=True)
    st_apr_ok = Estado(etapa_id=e_apr.id, nombre="Aprobado por gerente", cierra_etapa=True)
    st_ref_ini = Estado(etapa_id=e_ref.id, nombre="En comite", es_inicial=True)
    st_ref_apr = Estado(etapa_id=e_ref.id, nombre="Comite aprueba", cierra_etapa=True)
    st_ref_dec = Estado(etapa_id=e_ref.id, nombre="Comite declina", cierra_etapa=True)
    st_dec = Estado(etapa_id=e_dec.id, nombre="Declinada", es_inicial=True, cierra_etapa=True)
    st_form = Estado(etapa_id=e_form.id, nombre="Formalizado", es_inicial=True, cierra_etapa=True)

    estados = [
        st_cap_ini, st_cap_ok, st_doc_ini, st_doc_ok, st_buro, st_eval,
        st_apr_ini, st_apr_ok, st_ref_ini, st_ref_apr, st_ref_dec, st_dec, st_form,
    ]
    for s in estados:
        db.add(s)
    db.flush()

    # Transiciones manuales
    trans = [
        (st_cap_ini, e_cap, st_cap_ok),
        (st_cap_ok, e_doc, st_doc_ini),
        (st_doc_ini, e_doc, st_doc_ok),
        (st_doc_ok, e_buro, st_buro),
        (st_apr_ini, e_apr, st_apr_ok),
        (st_apr_ok, e_form, st_form),
        (st_apr_ini, e_ref, st_ref_ini),  # gerente puede enviar a comité
        (st_ref_ini, e_ref, st_ref_apr),
        (st_ref_ini, e_ref, st_ref_dec),
        (st_ref_apr, e_form, st_form),
        (st_ref_dec, e_dec, st_dec),
    ]
    for origen, etapa_d, destino in trans:
        db.add(
            Transicion(
                estado_origen_id=origen.id,
                etapa_destino_id=etapa_d.id,
                estado_destino_id=destino.id,
            )
        )

    # Mapeos buró
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

    # Buró → Evaluación (siempre post-buró)
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

    # Mapeos motor
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

    # Post evaluación: Aprobación | Referimiento | Declinada
    out_dictamen = _output(api_motor, "Dictamen")
    _add_regla(db, estado=st_eval, output=out_dictamen, valor="APROBADA", etapa_dest=e_apr, estado_dest=st_apr_ini, prioridad=1, nombre="Motor -> Gerente")
    _add_regla(db, estado=st_eval, output=out_dictamen, valor="REFERIDA", etapa_dest=e_ref, estado_dest=st_ref_ini, prioridad=2, nombre="Motor -> Comite")
    _add_regla(db, estado=st_eval, output=out_dictamen, valor="DECLINADA", etapa_dest=e_dec, estado_dest=st_dec, prioridad=3, nombre="Motor -> Declinada")

    _log(f"+ flujo {FLUJO_NOMBRE} id={flujo.id} (8 etapas multi-rol)")
    return flujo


def _set_dato(db, caso, dato, valor, usuario, next_dato):
    row = db.query(CasoDato).filter(CasoDato.caso_id == caso.id, CasoDato.dato_id == dato.id).first()
    if row is None:
        next_dato[0] += 1
        db.add(
            CasoDato(
                id=next_dato[0],
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


def _mover(db, caso, etapa, estado, usuario, comentario, next_hist):
    from sqlalchemy import func

    from app.models import CasoHistorial

    caso.etapa_actual_id = etapa.id
    caso.estado_actual_id = estado.id
    next_hist[0] = max(next_hist[0], int(db.query(func.max(CasoHistorial.id)).scalar() or 0)) + 1
    db.add(
        CasoHistorial(
            id=next_hist[0],
            caso_id=caso.id,
            etapa_id=etapa.id,
            estado_id=estado.id,
            usuario_id=usuario.id,
            comentario=comentario,
            origen="SISTEMA",
        )
    )
    db.flush()


def _ensure_casos_demo(db, flujo, clientes, datos):
    if db.query(Caso).filter(Caso.flujo_id == flujo.id).count() > 0:
        _log("casos demo ya existen; omitidos")
        return

    admin = db.query(Usuario).filter(Usuario.usuario_ad == "admin").first()
    if not admin:
        return

    from sqlalchemy import func

    from app.models import CasoHistorial
    from app.services import motor

    etapas = {e.orden: e for e in flujo.etapas}
    e1, e2, e3, e4, e5, e5b, e5c, e6 = [etapas[i] for i in (1, 2, 3, 4, 5, 6, 7, 8)]

    def st0(e):
        for s in e.estados:
            if s.es_inicial:
                return s
        return e.estados[0]

    next_hist = [0]
    next_dato = [int(db.query(func.max(CasoDato.id)).scalar() or 0)]

    def nuevo(cliente):
        return motor.crear_caso(db, flujo, admin, cliente.id)

    def d(caso, key, val):
        next_dato[0] = max(next_dato[0], int(db.query(func.max(CasoDato.id)).scalar() or 0))
        _set_dato(db, caso, datos[key], val, admin, next_dato)

    # 1 Ana — Captura (ejecutivo)
    c1 = nuevo(clientes["001-1234567-8"])
    d(c1, "Producto solicitado", "TDC Gold")
    d(c1, "Monto solicitado DOP", "150000")
    d(c1, "Salario", "45000")
    d(c1, "Asalariado", "true")
    d(c1, "Tiempo laborando (meses)", "24")
    d(c1, "Empleador", "Banco Demo SA")
    _log(f"+ caso #{c1.id} Captura (Ana / ejecutivo)")

    # 2 Carlos — Consulta Buró
    c2 = nuevo(clientes["002-9876543-2"])
    d(c2, "Producto solicitado", "TDC Clasica")
    d(c2, "Monto solicitado DOP", "80000")
    d(c2, "Salario", "28000")
    d(c2, "Asalariado", "true")
    d(c2, "Tiempo laborando (meses)", "10")
    d(c2, "Empleador", "Comercial del Este")
    _mover(db, c2, e3, st0(e3), admin, "Demo: en Consulta Buro", next_hist)
    d(c2, "Score Buró", "640")
    d(c2, "Dictamen Buró", "ALERTA")
    d(c2, "Resumen Buró", "Mora reciente leve")
    _log(f"+ caso #{c2.id} Consulta Buro (Carlos / analista)")

    # 3 Laura — Aprobación Gerente (post motor APROBADA)
    c3 = nuevo(clientes["003-4567890-1"])
    d(c3, "Producto solicitado", "TDC Platinum")
    d(c3, "Monto solicitado DOP", "250000")
    d(c3, "Salario", "62000")
    d(c3, "Asalariado", "true")
    d(c3, "Tiempo laborando (meses)", "48")
    d(c3, "Dictamen Buró", "OK")
    d(c3, "Dictamen Motor", "APROBADA")
    d(c3, "Monto Aprobado DOP", "185000")
    d(c3, "Razón Motor", "Perfil solvente")
    _mover(db, c3, e5, st0(e5), admin, "Demo: pendiente gerente", next_hist)
    _log(f"+ caso #{c3.id} Aprobacion Gerente (Laura)")

    # 4 José — Comité
    c4 = nuevo(clientes["004-1112233-4"])
    d(c4, "Producto solicitado", "TDC Gold")
    d(c4, "Salario", "35000")
    d(c4, "Asalariado", "true")
    d(c4, "Tiempo laborando (meses)", "18")
    d(c4, "Dictamen Motor", "REFERIDA")
    d(c4, "Razón Motor", "Monto requiere comité")
    _mover(db, c4, e5b, st0(e5b), admin, "Demo: en comite", next_hist)
    _log(f"+ caso #{c4.id} Comite (Jose)")

    # 5 Patricia — Formalizado CERRADO
    c5 = nuevo(clientes["005-2223344-5"])
    d(c5, "Producto solicitado", "TDC Clasica")
    d(c5, "Salario", "55000")
    d(c5, "Dictamen Motor", "APROBADA")
    d(c5, "Dictamen Gerente", "Confirmar aprobacion")
    d(c5, "Monto Aprobado DOP", "120000")
    _mover(db, c5, e6, st0(e6), admin, "Demo: formalizado", next_hist)
    c5.estado_general = "CERRADO"
    _log(f"+ caso #{c5.id} Formalizacion CERRADO (Patricia)")

    # 6 Ricardo — Declinada
    c6 = nuevo(clientes["006-3334455-6"])
    d(c6, "Salario", "12000")
    d(c6, "Asalariado", "false")
    d(c6, "Tiempo laborando (meses)", "3")
    d(c6, "Dictamen Motor", "DECLINADA")
    d(c6, "Motivo Decl Soft", "Ingresos insuficientes")
    _mover(db, c6, e5c, st0(e5c), admin, "Demo: declinado", next_hist)
    c6.estado_general = "CERRADO"
    _log(f"+ caso #{c6.id} Declinada (Ricardo)")


def run_seed_demo(
    db: Session,
    *,
    base_url: str | None = None,
    force: bool = False,
    with_casos: bool = True,
) -> dict[str, Any]:
    base = resolve_demo_api_base(base_url)
    _log(f"base URL APIs: {base}")

    ensure_tipos_dato(db)
    clientes = _ensure_clientes(db)
    grupos = _ensure_grupos_y_users(db)

    _ensure_api(
        db,
        nombre="Demo Motor Credito",
        descripcion="Motor demo: Dictamen APROBADA / REFERIDA / DECLINADA + montos.",
        url=f"{base}/demo-api/evaluacion",
        parametros=[
            {"nombre": "salario", "ubicacion": "body", "origen": "dato"},
            {"nombre": "es_asalariado", "ubicacion": "body", "origen": "dato"},
            {"nombre": "tiempo_laborando", "ubicacion": "body", "origen": "dato"},
            {"nombre": "cedula", "ubicacion": "body", "origen": "caso", "campo_caso": "cliente_identificacion"},
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
        descripcion="Buro demo: Score, ChanceFavor, Mora, EIC, DictamenBuro.",
        url=f"{base}/demo-api/buro/reporte",
        parametros=[
            {"nombre": "cedula", "ubicacion": "body", "origen": "caso", "campo_caso": "cliente_identificacion"},
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
    docs = _ensure_docs(db)
    datos = {n: _ensure_dato(db, n, tid, desc) for n, tid, desc in DATOS_DEMO}
    api_motor, api_buro = _vincular_params(db, datos)

    existente = db.query(Flujo).filter(Flujo.nombre == FLUJO_NOMBRE).first()
    if existente is not None:
        n_casos = db.query(Caso).filter(Caso.flujo_id == existente.id).count()
        # Si el flujo viejo tiene < 8 etapas, recrear
        n_etapas = len(existente.etapas or [])
        if (n_casos and not force and n_etapas >= 8):
            _log(f"flujo ya existe id={existente.id} con {n_casos} caso(s)")
            if with_casos:
                _ensure_casos_demo(db, existente, clientes, datos)
            return {"flujo_id": existente.id, "created": False, "base_url": base}
        _purge_flujo(db, existente)

    flujo = _build_flujo(
        db, tipo=tipo, grupos=grupos, datos=datos, docs=docs, api_motor=api_motor, api_buro=api_buro
    )
    if with_casos:
        _ensure_casos_demo(db, flujo, clientes, datos)
    return {"flujo_id": flujo.id, "created": True, "base_url": base}
