"""Lógica pura de las APIs demo (motor + buró) sin Flask ni HTTP.

Usado in-process por Helios para evitar deadlock gunicorn al llamar /demo-api/*.
"""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta
from typing import Any

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


def cedula_limpia(raw: str | None) -> str:
    return "".join(ch for ch in (raw or "") if ch.isdigit())


def _rng_from_cedula(cedula: str) -> random.Random:
    seed = int(hashlib.sha256(cedula.encode("utf-8")).hexdigest()[:12], 16)
    return random.Random(seed)


def as_bool(raw: object) -> bool:
    if isinstance(raw, str):
        return raw.strip().lower() in ("1", "true", "si", "sí", "yes")
    return bool(raw)


def evaluar_motor(
    salario: float,
    es_asalariado: bool,
    tiempo_laborando: float,
    cedula: str,
) -> dict[str, Any]:
    rng = _rng_from_cedula(cedula or "0")
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

    return {
        "Monto_DOP": monto_dop,
        "Monto_USD": round(monto_dop / TASA_USD, 2),
        "Dictamen": dictamen,
        "Razon": razon,
        "Cedula": cedula,
        "Timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


def reporte_buro(cedula: str) -> dict[str, Any]:
    key = cedula_limpia(cedula)
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


def ejecutar_demo_por_path(path: str, body: dict, headers: dict) -> tuple[int, dict] | None:
    """Si path es /demo-api/*, ejecuta y devuelve (status, json)."""
    p = (path or "").rstrip("/")
    if "/demo-api/" not in p:
        return None

    auth = ""
    for k, v in (headers or {}).items():
        if str(k).lower() == "authorization":
            auth = str(v or "")
            break
    if not auth.lower().startswith("bearer ") or auth.split(" ", 1)[1].strip() != "test-token-123":
        return 401, {"error": "No autorizado. Use Authorization: Bearer test-token-123"}

    if p.endswith("/demo-api/evaluacion"):
        try:
            salario = float(body.get("salario") or 0)
            tiempo = float(body.get("tiempo_laborando") or 0)
        except (TypeError, ValueError):
            return 400, {"error": "salario y tiempo_laborando deben ser numéricos"}
        cedula = cedula_limpia(str(body.get("cedula") or ""))
        if salario <= 0 or not cedula:
            return 400, {"error": "Requiere salario > 0 y cedula"}
        return 200, evaluar_motor(salario, as_bool(body.get("es_asalariado", False)), tiempo, cedula)

    if p.endswith("/demo-api/buro/reporte"):
        cedula = cedula_limpia(str(body.get("cedula") or body.get("identificacion") or ""))
        if len(cedula) < 5:
            return 400, {"error": "Requiere cedula válida"}
        return 200, reporte_buro(cedula)

    return None
