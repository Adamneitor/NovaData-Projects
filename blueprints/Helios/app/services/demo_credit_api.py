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
    venc = (datetime.utcnow() + timedelta(days=45)).strftime("%Y-%m-%d")
    ingresos = float(perfil.get("EicMax") or 0) * 0.12 or 92400.0
    comprometido = round(ingresos * 0.34, 2)
    disponible = round(ingresos - comprometido, 2)
    score = int(perfil.get("Score") or 0)
    hist = [
        {"mes": "Ene·26", "score": max(380, score - 57)},
        {"mes": "May·26", "score": max(380, score - 28)},
        {"mes": "Sep·26", "score": score},
    ]
    cuentas = [
        {
            "entidad": "Banco Vimenca, C. por A.",
            "producto": "TCR Tarjeta",
            "estado": "abierta",
            "apertura": "06/2023",
            "aprobado": 220000,
            "adeudado": 45429,
            "cuota": 1202,
            "vencido": 0,
        },
        {
            "entidad": "Asociación Cibao de Ahorros y Préstamos",
            "producto": "TCR Tarjeta",
            "estado": "abierta",
            "apertura": "09/2020",
            "aprobado": 150000,
            "adeudado": 140,
            "cuota": 0,
            "vencido": 0,
        },
    ]
    return {
        **perfil,
        "XCORE": score,
        "Cedula": key,
        "FechaConsulta": datetime.utcnow().strftime("%Y-%m-%d"),
        "FechaVencimiento": venc,
        "Proveedor": "Demo Buró NOVA",
        "Asalariado": "Sí",
        "Ingresos": ingresos,
        "Comprometido": comprometido,
        "EndeudamientoPct": 34,
        "DisponibleMes": disponible,
        "HistoriaAnios": 6,
        "UsoLimitePct": 12,
        "CuentasActivas": perfil.get("CuentasAbiertas") or 2,
        "CuentasTotales": (perfil.get("CuentasAbiertas") or 2) + (perfil.get("CuentasCerradas") or 5),
        "AtrasoTotal": float(perfil.get("MoraMaxDias") or 0),
        "HistorialScore": hist,
        "Cuentas": cuentas,
    }


def _es_path_motor(p: str) -> bool:
    return p.endswith("/demo-api/evaluacion") or p.endswith("/api/evaluacion")


def _es_path_buro(p: str) -> bool:
    return p.endswith("/demo-api/buro/reporte") or p.endswith("/api/buro/reporte")


def ejecutar_demo_por_path(path: str, body: dict, headers: dict) -> tuple[int, dict] | None:
    """Ejecuta el mock local (puerto 3000 o /demo-api/*) sin HTTP."""
    p = (path or "").rstrip("/")
    if not (_es_path_motor(p) or _es_path_buro(p)):
        return None

    auth = ""
    for k, v in (headers or {}).items():
        if str(k).lower() == "authorization":
            auth = str(v or "")
            break
    token_ok = auth.lower().startswith("bearer ") and auth.split(" ", 1)[1].strip() == "test-token-123"
    if auth and not token_ok:
        return 401, {"error": "No autorizado. Use Authorization: Bearer test-token-123"}

    if _es_path_motor(p):
        from app.services.dato_formato import _parse_decimal

        try:
            sal_raw = body.get("salario")
            tim_raw = body.get("tiempo_laborando") or body.get("tiempo")
            sal_num = _parse_decimal(str(sal_raw)) if sal_raw not in (None, "") else None
            tim_num = _parse_decimal(str(tim_raw)) if tim_raw not in (None, "") else None
            salario = float(sal_num) if sal_num is not None else float(sal_raw or 0)
            tiempo = float(tim_num) if tim_num is not None else float(tim_raw or 0)
        except (TypeError, ValueError):
            return 400, {"error": "salario y tiempo_laborando deben ser numéricos"}
        cedula = cedula_limpia(str(body.get("cedula") or ""))
        faltan = []
        if salario <= 0:
            faltan.append("Salario")
        if not cedula:
            faltan.append("cédula del cliente")
        if faltan:
            return 400, {
                "error": "Complete " + ", ".join(faltan) + " y vuelva a ejecutar el Motor de Crédito TC."
            }
        asal = body.get("es_asalariado", body.get("asalariado", False))
        return 200, evaluar_motor(salario, as_bool(asal), tiempo, cedula)

    if _es_path_buro(p):
        cedula = cedula_limpia(str(body.get("cedula") or body.get("identificacion") or ""))
        if len(cedula) < 5:
            return 400, {"error": "Requiere cedula válida"}
        return 200, reporte_buro(cedula)

    return None
