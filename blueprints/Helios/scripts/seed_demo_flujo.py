"""
Seed idempotente del flujo demo «Demo Originacion TDC» para presentación Helios.

Incluye:
  - APIs Demo Motor Credito + Demo Buro Reporte (vía seed_demo_apis)
  - Datos complementarios (captura + outputs buró/motor)
  - Grupo operativo + vínculo a admin
  - Flujo BPM: Captura → Buró → Evaluación → Aprobada | Referida | Declinada
  - Reglas AUTO por Dictamen / DictamenBuro
  - Mapeos input/output por estado

Uso (desde blueprints/Helios):
  python scripts/seed_demo_flujo.py
  python scripts/seed_demo_flujo.py --base-url https://novadata-projects-production.up.railway.app
  python scripts/seed_demo_flujo.py --force   # recrea el flujo aunque tenga casos
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Reutiliza helpers de APIs/clientes demo
from scripts.seed_demo_apis import _ensure_api, _ensure_clientes  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    ApiCall,
    ApiOutput,
    ApiParametro,
    ApiRegla,
    Caso,
    CasoApiLog,
    DatoComplementario,
    Estado,
    EstadoApiInput,
    EstadoApiOutput,
    Etapa,
    EtapaDato,
    EtapaGrupo,
    Flujo,
    GrupoUsuario,
    GrupoXUsuario,
    TipoDato,
    TipoFlujo,
    Transicion,
    Usuario,
)
from app.seed import ensure_tipos_dato  # noqa: E402

FLUJO_NOMBRE = "Demo Originacion TDC"
GRUPO_NOMBRE = "Demo Operaciones"

# (nombre_dato, tipo_id, descripción)
# tipos: 1 texto, 2 numero, 4 booleano, 8 moneda
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


def _ensure_tipo_flujo(db) -> TipoFlujo:
    tf = db.query(TipoFlujo).filter(TipoFlujo.nombre == "Credito").first()
    if tf is None:
        tf = TipoFlujo(nombre="Credito")
        db.add(tf)
        db.flush()
        print(f"  + tipo flujo Credito id={tf.id}")
    return tf


def _ensure_dato(db, nombre: str, tipo_id: int, descripcion: str | None) -> DatoComplementario:
    d = db.query(DatoComplementario).filter(DatoComplementario.nombre == nombre).first()
    if d is None:
        if db.get(TipoDato, tipo_id) is None:
            raise RuntimeError(f"Falta TipoDato id={tipo_id}; corre seed base de Helios")
        d = DatoComplementario(
            nombre=nombre,
            descripcion=descripcion,
            tipo_dato_id=tipo_id,
            activo=True,
            decimales=2 if tipo_id in (6, 8, 9) else None,
        )
        db.add(d)
        db.flush()
        print(f"  + dato «{nombre}» id={d.id}")
    else:
        d.descripcion = descripcion or d.descripcion
        d.tipo_dato_id = tipo_id
        d.activo = True
    return d


def _ensure_grupo(db) -> GrupoUsuario:
    g = db.query(GrupoUsuario).filter(GrupoUsuario.nombre == GRUPO_NOMBRE).first()
    if g is None:
        g = GrupoUsuario(nombre=GRUPO_NOMBRE, descripcion="Grupo operativo para demo Helios")
        db.add(g)
        db.flush()
        print(f"  + grupo «{GRUPO_NOMBRE}» id={g.id}")
    admin = db.query(Usuario).filter(Usuario.usuario_ad == "admin").first()
    if admin is not None:
        link = (
            db.query(GrupoXUsuario)
            .filter(GrupoXUsuario.grupo_id == g.id, GrupoXUsuario.usuario_id == admin.id)
            .first()
        )
        if link is None:
            db.add(GrupoXUsuario(grupo_id=g.id, usuario_id=admin.id))
            print(f"  + admin vinculado a «{GRUPO_NOMBRE}»")
    return g


def _vincular_params_motor(db, datos: dict[str, DatoComplementario]) -> ApiCall:
    api = db.query(ApiCall).filter(ApiCall.nombre == "Demo Motor Credito").one()
    mapping = {
        "salario": datos["Salario"].id,
        "es_asalariado": datos["Asalariado"].id,
        "tiempo_laborando": datos["Tiempo laborando (meses)"].id,
    }
    for p in api.parametros or []:
        if p.nombre in mapping:
            p.origen = "dato"
            p.dato_id = mapping[p.nombre]
            p.campo_caso = None
        elif p.nombre == "cedula":
            p.origen = "caso"
            p.campo_caso = "cliente_identificacion"
            p.dato_id = None
    return api


def _vincular_params_buro(db) -> ApiCall:
    api = db.query(ApiCall).filter(ApiCall.nombre == "Demo Buro Reporte").one()
    for p in api.parametros or []:
        if p.nombre == "cedula":
            p.origen = "caso"
            p.campo_caso = "cliente_identificacion"
            p.dato_id = None
    return api


def _output_por_nombre(api: ApiCall, nombre: str) -> ApiOutput:
    for o in api.outputs or []:
        if o.nombre == nombre:
            return o
    raise RuntimeError(f"API «{api.nombre}» sin output «{nombre}»")


def _purge_flujo(db, flujo: Flujo) -> None:
    caso_ids = [c.id for c in db.query(Caso).filter(Caso.flujo_id == flujo.id).all()]
    if caso_ids:
        db.query(CasoApiLog).filter(CasoApiLog.caso_id.in_(caso_ids)).delete(
            synchronize_session=False
        )
        for c in db.query(Caso).filter(Caso.id.in_(caso_ids)).all():
            db.delete(c)
        db.flush()
    db.query(EtapaGrupo).filter(
        EtapaGrupo.etapa_id.in_([e.id for e in flujo.etapas])
    ).delete(synchronize_session=False)
    db.delete(flujo)
    db.flush()
    print(f"  ~ eliminado flujo previo «{FLUJO_NOMBRE}»")


def _add_etapa_dato(db, etapa: Etapa, dato: DatoComplementario, *, obligatorio: bool, orden: int) -> None:
    db.add(
        EtapaDato(
            etapa_id=etapa.id,
            dato_id=dato.id,
            obligatorio=obligatorio,
            orden=orden,
        )
    )


def _add_regla(
    db,
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
    db,
    *,
    tipo: TipoFlujo,
    grupo: GrupoUsuario,
    datos: dict[str, DatoComplementario],
    api_motor: ApiCall,
    api_buro: ApiCall,
) -> Flujo:
    flujo = Flujo(
        tipo_flujo_id=tipo.id,
        nombre=FLUJO_NOMBRE,
        descripcion="Originación TDC demo: captura → buró → motor → dictamen final.",
        activo=True,
    )
    db.add(flujo)
    db.flush()

    # --- Etapas ---
    e_captura = Etapa(
        flujo_id=flujo.id,
        nombre="Captura",
        descripcion="Datos laborales del solicitante",
        orden=1,
        es_final=False,
        permite_retroceso=False,
    )
    e_buro = Etapa(
        flujo_id=flujo.id,
        nombre="Consulta Buró",
        descripcion="Consulta reporte de buró demo",
        orden=2,
        es_final=False,
        permite_retroceso=True,
    )
    e_eval = Etapa(
        flujo_id=flujo.id,
        nombre="Evaluación",
        descripcion="Motor de crédito demo",
        orden=3,
        es_final=False,
        permite_retroceso=False,
    )
    e_apr = Etapa(
        flujo_id=flujo.id,
        nombre="Aprobación",
        descripcion="Caso aprobado",
        orden=4,
        es_final=True,
    )
    e_ref = Etapa(
        flujo_id=flujo.id,
        nombre="Comité / Referimiento",
        descripcion="Caso referido a comité",
        orden=5,
        es_final=True,
    )
    e_dec = Etapa(
        flujo_id=flujo.id,
        nombre="Declinada",
        descripcion="Caso declinado",
        orden=6,
        es_final=True,
    )
    for e in (e_captura, e_buro, e_eval, e_apr, e_ref, e_dec):
        db.add(e)
    db.flush()

    for e in (e_captura, e_buro, e_eval, e_apr, e_ref, e_dec):
        db.add(EtapaGrupo(etapa_id=e.id, grupo_id=grupo.id))

    # Datos por etapa
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
        [
            "Dictamen Motor",
            "Monto Aprobado DOP",
            "Monto Aprobado USD",
            "Razón Motor",
        ],
        start=1,
    ):
        _add_etapa_dato(db, e_eval, datos[key], obligatorio=False, orden=i)

    # Estados
    st_cap_ini = Estado(etapa_id=e_captura.id, nombre="En captura", es_inicial=True, cierra_etapa=False)
    st_cap_ok = Estado(etapa_id=e_captura.id, nombre="Lista para buró", es_inicial=False, cierra_etapa=True)

    st_buro = Estado(
        etapa_id=e_buro.id,
        nombre="Consultando",
        es_inicial=True,
        cierra_etapa=False,
        api_call_id=api_buro.id,
    )

    st_eval = Estado(
        etapa_id=e_eval.id,
        nombre="Ejecutando motor",
        es_inicial=True,
        cierra_etapa=False,
        api_call_id=api_motor.id,
    )

    st_apr = Estado(etapa_id=e_apr.id, nombre="Aprobada", es_inicial=True, cierra_etapa=True)
    st_ref = Estado(etapa_id=e_ref.id, nombre="Referida", es_inicial=True, cierra_etapa=True)
    st_dec = Estado(etapa_id=e_dec.id, nombre="Declinada", es_inicial=True, cierra_etapa=True)

    for s in (st_cap_ini, st_cap_ok, st_buro, st_eval, st_apr, st_ref, st_dec):
        db.add(s)
    db.flush()

    # Transiciones manuales Captura
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
    buro_out_map = {
        "Score": "Score Buró",
        "ChanceFavor": "Chance Favor",
        "EicMax": "EIC Máximo",
        "MoraMaxDias": "Mora Máx Días",
        "DictamenBuro": "Dictamen Buró",
        "Resumen": "Resumen Buró",
        "CuentasAbiertas": "Cuentas Abiertas",
    }
    for out_name, dato_name in buro_out_map.items():
        db.add(
            EstadoApiOutput(
                estado_id=st_buro.id,
                output_id=_output_por_nombre(api_buro, out_name).id,
                dato_id=datos[dato_name].id,
            )
        )

    # Reglas buró → evaluación (cualquier dictamen)
    out_db = _output_por_nombre(api_buro, "DictamenBuro")
    for i, val in enumerate(("OK", "ALERTA", "RIESGO"), start=1):
        _add_regla(
            db,
            estado=st_buro,
            output=out_db,
            valor=val,
            etapa_dest=e_eval,
            estado_dest=st_eval,
            prioridad=i,
            nombre=f"Buró {val} → Evaluación",
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
    motor_out_map = {
        "Dictamen": "Dictamen Motor",
        "Monto_DOP": "Monto Aprobado DOP",
        "Monto_USD": "Monto Aprobado USD",
        "Razon": "Razón Motor",
    }
    for out_name, dato_name in motor_out_map.items():
        db.add(
            EstadoApiOutput(
                estado_id=st_eval.id,
                output_id=_output_por_nombre(api_motor, out_name).id,
                dato_id=datos[dato_name].id,
            )
        )

    out_dictamen = _output_por_nombre(api_motor, "Dictamen")
    _add_regla(
        db,
        estado=st_eval,
        output=out_dictamen,
        valor="APROBADA",
        etapa_dest=e_apr,
        estado_dest=st_apr,
        prioridad=1,
        nombre="Motor APROBADA",
    )
    _add_regla(
        db,
        estado=st_eval,
        output=out_dictamen,
        valor="REFERIDA",
        etapa_dest=e_ref,
        estado_dest=st_ref,
        prioridad=2,
        nombre="Motor REFERIDA",
    )
    _add_regla(
        db,
        estado=st_eval,
        output=out_dictamen,
        valor="DECLINADA",
        etapa_dest=e_dec,
        estado_dest=st_dec,
        prioridad=3,
        nombre="Motor DECLINADA",
    )

    print(f"  + flujo «{FLUJO_NOMBRE}» id={flujo.id}")
    return flujo


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed flujo demo Helios (originación TDC)")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("DEMO_API_BASE_URL", "http://127.0.0.1:5012"),
        help="URL base de NOVA donde viven /demo-api/*",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recrea el flujo aunque existan casos asociados",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    print(f"Base URL demo APIs: {base}")
    db = SessionLocal()
    try:
        ensure_tipos_dato(db)
        _ensure_clientes(db)

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
            descripcion="Buró demo: Score, ChanceFavor, MoraMaxDias, EIC, DictamenBuro.",
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

        datos = {
            nombre: _ensure_dato(db, nombre, tipo_id, desc)
            for nombre, tipo_id, desc in DATOS_DEMO
        }
        api_motor = _vincular_params_motor(db, datos)
        api_buro = _vincular_params_buro(db)

        existente = db.query(Flujo).filter(Flujo.nombre == FLUJO_NOMBRE).first()
        if existente is not None:
            n_casos = db.query(Caso).filter(Caso.flujo_id == existente.id).count()
            if n_casos and not args.force:
                print(
                    f"Flujo «{FLUJO_NOMBRE}» ya existe (id={existente.id}) con {n_casos} caso(s). "
                    "Usa --force para recrearlo."
                )
                db.commit()
                return
            _purge_flujo(db, existente)

        flujo = _build_flujo(
            db,
            tipo=tipo,
            grupo=grupo,
            datos=datos,
            api_motor=api_motor,
            api_buro=api_buro,
        )
        db.commit()
        print("Listo.")
        print(f"  Flujo id={flujo.id}: Captura -> Consulta Buro -> Evaluacion -> finales")
        print("  Clientes: 001-1234567-8 (OK), 002-9876543-2 (ALERTA), 003-4567890-1 (RIESGO)")
        print("  Demo: crear caso con cliente demo -> Captura (salario/asalariado/tiempo) -> avanzar")
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
