"""APIs demo para presentación Helios: Motor de crédito + Buró de crédito.

Montadas en Flask bajo /demo-api/* para que Helios las consuma en Railway
o local sin levantar el mock aparte.
"""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta
from typing import Any

from flask import Blueprint, jsonify, request

demo_api_bp = Blueprint("demo_api", __name__, url_prefix="/demo-api")

TOKEN = "test-token-123"
TASA_USD = 57.5

RAZONES_APROBADA = [
    "Perfil estable con ingresos consistentes",
    "Historial laboral sólido y capacidad de pago adecuada",
    "Ingresos suficientes para el producto solicitado",
    "Evaluación positiva por antigüedad laboral",
    "Score interno favorable según política vigente",
    "Relación deuda/ingreso dentro de parámetros aceptables",
]
RAZONES_REFERIDA = [
    "Requiere revisión de comité por monto solicitado",
    "Score en banda intermedia: validar documentación adicional",
    "Inconsistencia leve en datos laborales: referir a analista",
    "Capacidad de pago borderline: decisión manual recomendada",
    "Cliente con historial mixto: evaluación humana requerida",
]
RAZONES_DECLINADA = [
    "Ingresos insuficientes para el monto evaluado",
    "Antigüedad laboral por debajo del mínimo requerido",
    "Perfil de riesgo elevado según política interna",
    "Capacidad de pago insuficiente tras simulación",
    "No cumple criterios mínimos de elegibilidad",
]

# Perfiles demo por cédula (sin guiones) — buró
_BURO_PROFILES: dict[str, dict[str, Any]] = {
    "00112345678": {
        "Nombre": "Ana María Pérez Rosario",
        "Score": 782,
        "ChanceFavor": 72,
        "ChanceContra": 28,
        "EicMin": 320000.0,
        "EicMax": 780000.0,
        "CuentasAbiertas": 2,
        "CuentasCerradas": 1,
        "MoraMaxDias": 0,
        "DictamenBuro": "OK",
        "Resumen": "Buen historial. Sin atraso vigente. Elegible para originación.",
    },
    "00298765432": {
        "Nombre": "Carlos Enrique Méndez Ruiz",
        "Score": 610,
        "ChanceFavor": 48,
        "ChanceContra": 52,
        "EicMin": 80000.0,
        "EicMax": 220000.0,
        "CuentasAbiertas": 3,
        "CuentasCerradas": 1,
        "MoraMaxDias": 45,
        "DictamenBuro": "ALERTA",
        "Resumen": "Mora histórica reciente. Referir a evaluación manual.",
    },
    "00345678901": {
        "Nombre": "Laura Beatriz Fernández Díaz",
        "Score": 420,
        "ChanceFavor": 22,
        "ChanceContra": 78,
        "EicMin": 0.0,
        "EicMax": 50000.0,
        "CuentasAbiertas": 4,
        "CuentasCerradas": 2,
        "MoraMaxDias": 120,
        "DictamenBuro": "RIESGO",
        "Resumen": "Alto riesgo. Múltiples atrasos. No recomendado sin garantías.",
    },
}


def _cedula_limpia(raw: str | None) -> str:
    return "".join(ch for ch in (raw or "") if ch.isdigit())


def _auth_ok() -> bool:
    auth = request.headers.get("Authorization") or ""
    if not auth.lower().startswith("bearer "):
        return False
    return auth.split(" ", 1)[1].strip() == TOKEN


def _rng_from_cedula(cedula: str) -> random.Random:
    seed = int(hashlib.sha256(cedula.encode("utf-8")).hexdigest()[:12], 16)
    return random.Random(seed)


def evaluar_motor(
    salario: float,
    es_asalariado: bool,
    tiempo_laborando: float,
    cedula: str,
) -> dict[str, Any]:
    """Dictamen APROBADA | REFERIDA | DECLINADA con montos demo."""
    rng = _rng_from_cedula(cedula or "0")
    # También mezcla un poco de aleatorio por request para demos en vivo
    rng2 = random.Random(rng.random() + random.random())

    score = 0.30
    if es_asalariado:
        score += 0.15
    if tiempo_laborando >= 12:
        score += 0.12
    if tiempo_laborando >= 36:
        score += 0.10
    if salario >= 30000:
        score += 0.10
    if salario >= 60000:
        score += 0.10
    score = min(0.90, max(0.12, score))

    roll = rng2.random()
    if roll < score * 0.55:
        dictamen = "APROBADA"
        base = max(15_000.0, min(500_000.0, salario * rng2.uniform(2.0, 6.5)))
        monto_dop = round(rng2.uniform(base * 0.7, min(500_000, base * 1.3)), 2)
        razon = rng2.choice(RAZONES_APROBADA)
    elif roll < score * 0.55 + 0.28:
        dictamen = "REFERIDA"
        base = max(10_000.0, min(250_000.0, salario * rng2.uniform(1.2, 3.5)))
        monto_dop = round(base, 2)
        razon = rng2.choice(RAZONES_REFERIDA)
    else:
        dictamen = "DECLINADA"
        monto_dop = round(rng2.uniform(10_000, 60_000), 2)
        razon = rng2.choice(RAZONES_DECLINADA)

    monto_usd = round(monto_dop / TASA_USD, 2)
    return {
        "Monto_DOP": monto_dop,
        "Monto_USD": monto_usd,
        "Dictamen": dictamen,
        "Razon": razon,
        "Cedula": cedula,
        "Timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


def reporte_buro(cedula: str) -> dict[str, Any]:
    key = _cedula_limpia(cedula)
    if key in _BURO_PROFILES:
        perfil = dict(_BURO_PROFILES[key])
    else:
        rng = _rng_from_cedula(key or "0")
        score = rng.randint(380, 820)
        if score >= 700:
            dictamen, favor = "OK", rng.randint(65, 88)
        elif score >= 550:
            dictamen, favor = "ALERTA", rng.randint(40, 60)
        else:
            dictamen, favor = "RIESGO", rng.randint(15, 35)
        perfil = {
            "Nombre": "Cliente Demo",
            "Score": score,
            "ChanceFavor": favor,
            "ChanceContra": 100 - favor,
            "EicMin": float(rng.randint(0, 150_000)),
            "EicMax": float(rng.randint(150_000, 800_000)),
            "CuentasAbiertas": rng.randint(0, 5),
            "CuentasCerradas": rng.randint(0, 3),
            "MoraMaxDias": 0 if dictamen == "OK" else rng.randint(15, 180),
            "DictamenBuro": dictamen,
            "Resumen": "Reporte sintético generado para demo Helios.",
        }
    venc = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
    return {
        **perfil,
        "Cedula": key,
        "FechaConsulta": datetime.utcnow().strftime("%Y-%m-%d"),
        "FechaVencimiento": venc,
        "Proveedor": "Demo Buró NOVA",
    }


@demo_api_bp.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "service": "nova-demo-apis",
            "endpoints": [
                "POST /demo-api/evaluacion",
                "POST /demo-api/buro/reporte",
            ],
            "token": "Bearer test-token-123",
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
    )


@demo_api_bp.post("/evaluacion")
def evaluacion():
    if not _auth_ok():
        return jsonify({"error": "No autorizado. Use Authorization: Bearer test-token-123"}), 401
    body = request.get_json(silent=True) or {}
    try:
        salario = float(body.get("salario") or 0)
        tiempo = float(body.get("tiempo_laborando") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "salario y tiempo_laborando deben ser numéricos"}), 400
    raw_asal = body.get("es_asalariado", False)
    if isinstance(raw_asal, str):
        asalariado = raw_asal.strip().lower() in ("1", "true", "si", "sí", "yes")
    else:
        asalariado = bool(raw_asal)
    cedula = _cedula_limpia(str(body.get("cedula") or ""))
    if salario <= 0 or not cedula:
        return jsonify({"error": "Requiere salario > 0 y cedula"}), 400
    return jsonify(evaluar_motor(salario, asalariado, tiempo, cedula))


@demo_api_bp.post("/buro/reporte")
def buro_reporte():
    if not _auth_ok():
        return jsonify({"error": "No autorizado. Use Authorization: Bearer test-token-123"}), 401
    body = request.get_json(silent=True) or {}
    cedula = _cedula_limpia(str(body.get("cedula") or body.get("identificacion") or ""))
    if len(cedula) < 5:
        return jsonify({"error": "Requiere cedula válida"}), 400
    return jsonify(reporte_buro(cedula))
