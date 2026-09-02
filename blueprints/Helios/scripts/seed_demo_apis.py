"""
Registra en Helios las 2 APIs demo (idempotente) para la presentación:

  1) Demo Motor Credito  → APROBADA | REFERIDA | DECLINADA
  2) Demo Buro Reporte   → Score, mora, EIC, DictamenBuro

Uso (desde blueprints/Helios):
  python scripts/seed_demo_apis.py
  python scripts/seed_demo_apis.py --base-url https://novadata-projects-production.up.railway.app

Variables:
  DEMO_API_BASE_URL  URL pública de NOVA (default: http://127.0.0.1:5012)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import SessionLocal
from app.models import ApiCall, ApiOutput, ApiParametro, Cliente

HEADERS = json.dumps(
    {
        "Authorization": "Bearer test-token-123",
        "Content-Type": "application/json",
    }
)

DEMO_CLIENTES = [
    ("001-1234567-8", "00112345678", "Ana María Pérez Rosario", "809-555-0101"),
    ("002-9876543-2", "00298765432", "Carlos Enrique Méndez Ruiz", "829-555-0202"),
    ("003-4567890-1", "00345678901", "Laura Beatriz Fernández Díaz", "849-555-0303"),
]


def _ensure_api(
    db,
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
            headers_json=HEADERS,
            timeout_seg=30,
            activo=True,
        )
        db.add(api)
        db.flush()
        print(f"  + creada API «{nombre}» id={api.id}")
    else:
        api.descripcion = descripcion
        api.metodo = "POST"
        api.url = url
        api.headers_json = HEADERS
        api.timeout_seg = 30
        api.activo = True
        # limpia params/outputs previos para re-seed limpio
        for p in list(api.parametros or []):
            db.delete(p)
        for o in list(api.outputs or []):
            db.delete(o)
        db.flush()
        print(f"  ~ actualizada API «{nombre}» id={api.id}")

    for p in parametros:
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
    for o in outputs:
        db.add(
            ApiOutput(
                api_id=api.id,
                nombre=o["nombre"],
                json_path=o["json_path"],
                formato=o.get("formato", "texto"),
            )
        )
    return api


def _ensure_clientes(db) -> None:
    for ident, _digits, nombre, tel in DEMO_CLIENTES:
        exists = db.query(Cliente).filter(Cliente.identificacion == ident).first()
        if exists:
            continue
        db.add(
            Cliente(
                nombre_completo=nombre,
                tipo_identificacion="Cedula",
                identificacion=ident,
                telefono=tel,
                correo=f"{ident.replace('-', '')}@demo.nova.local",
            )
        )
        print(f"  + cliente demo {ident} — {nombre}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed APIs demo Helios")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("DEMO_API_BASE_URL", "http://127.0.0.1:5012"),
        help="URL base de NOVA donde viven /demo-api/*",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    print(f"Base URL demo APIs: {base}")
    db = SessionLocal()
    try:
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

        db.commit()
        print("Listo. Configura el flujo en Helios:")
        print("  1) Estado Consulta Buró  → API «Demo Buro Reporte»")
        print("  2) Estado Evaluación     → API «Demo Motor Credito»")
        print("  3) Reglas AUTO por Dictamen = APROBADA | REFERIDA | DECLINADA")
        print("Clientes demo (cédula): 001-1234567-8 (OK), 002-9876543-2 (ALERTA), 003-4567890-1 (RIESGO)")
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
