"""Resumen humano de logs API (sin JSON crudo en la vista operativa)."""
from __future__ import annotations

import json
from typing import Any


# Claves conocidas → etiqueta amigable (orden de preferencia en KPIs)
KPI_LABELS: list[tuple[str, str]] = [
    ("Score", "Score"),
    ("XCORE", "Score XCORE"),
    ("score", "Score"),
    ("Monto_DOP", "Monto DOP"),
    ("Monto_USD", "Monto USD"),
    ("CapacidadPago", "Capacidad de pago"),
    ("Capacidad_Pago", "Capacidad de pago"),
    ("Dictamen", "Dictamen"),
    ("Razon", "Razón"),
    ("Razón", "Razón"),
    ("Mora", "Mora"),
    ("CuentasActivas", "Cuentas activas"),
]


def _parse_json(raw: str | None) -> Any:
    if not raw or not str(raw).strip():
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def _flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, dict):
                out.update(_flatten(v, key))
            elif isinstance(v, list):
                out[key] = v
            else:
                out[key] = v
                out[str(k)] = v  # también sin prefijo
    return out


def _pick(flat: dict[str, Any], *names: str) -> Any:
    for n in names:
        if n in flat and flat[n] is not None and flat[n] != "":
            return flat[n]
    return None


def summarize_api_log(log) -> dict[str, Any]:
    """Arma un dict listo para plantilla a partir de un CasoApiLog."""
    resp = _parse_json(getattr(log, "response_json", None))
    req = _parse_json(getattr(log, "request_json", None))
    flat = _flatten(resp) if isinstance(resp, dict) else {}

    dictamen = _pick(flat, "Dictamen", "dictamen", "Decision", "Resultado")
    razon = _pick(flat, "Razon", "Razón", "razon", "Mensaje", "message")
    score = _pick(flat, "Score", "XCORE", "score", "ScoreBuro")

    kpis: list[dict[str, str]] = []
    seen: set[str] = set()
    for key, label in KPI_LABELS:
        if key in seen:
            continue
        val = flat.get(key)
        if val is None or val == "":
            continue
        if key.lower() in {"dictamen"} and dictamen is not None:
            continue  # dictamen va en el texto principal
        seen.add(key)
        kpis.append({"label": label, "value": str(val)})
        if len(kpis) >= 6:
            break

    # Si no hubo KPIs tipados, toma hasta 4 pares del response plano
    if not kpis and isinstance(resp, dict):
        for k, v in list(resp.items())[:4]:
            if isinstance(v, (dict, list)):
                continue
            kpis.append({"label": str(k), "value": str(v)})

    api_nombre = log.api.nombre if getattr(log, "api", None) else f"API #{getattr(log, 'api_id', '')}"
    exito = bool(getattr(log, "exito", False))
    titulo = "Resultado de la consulta"
    if dictamen:
        titulo = f"Dictamen: {dictamen}"
    elif not exito:
        titulo = "La integración no respondió correctamente"

    banda = None
    score_num = None
    if score is not None:
        try:
            score_num = int(float(str(score).replace(",", "")))
        except (ValueError, TypeError):
            score_num = None
        if score_num is not None:
            if score_num >= 700:
                banda = "Bueno"
            elif score_num >= 600:
                banda = "Regular"
            else:
                banda = "Bajo"

    body_preview = None
    if isinstance(req, dict):
        body = req.get("body") if isinstance(req.get("body"), dict) else req
        if isinstance(body, dict):
            # no exponer tokens
            body_preview = {
                k: v
                for k, v in body.items()
                if "token" not in k.lower() and "password" not in k.lower() and "auth" not in k.lower()
            }

    return {
        "id": getattr(log, "id", None),
        "api_nombre": api_nombre,
        "exito": exito,
        "http_status": getattr(log, "http_status", None),
        "fecha": getattr(log, "fecha", None),
        "titulo": titulo,
        "dictamen": dictamen,
        "razon": razon,
        "score": score_num if score_num is not None else score,
        "banda": banda,
        "kpis": kpis,
        "request_preview": body_preview,
        "response_raw": getattr(log, "response_json", None) or "",
        "request_raw": getattr(log, "request_json", None) or "",
        "es_buro": bool(score_num is not None or (api_nombre and "bur" in api_nombre.lower())),
        "es_motor": bool(
            dictamen or (api_nombre and ("motor" in api_nombre.lower() or "evalu" in api_nombre.lower()))
        ),
    }


def group_api_logs_by_api(logs: list) -> list[dict[str, Any]]:
    """Agrupa intentos por API: tarjeta principal = último intento + historial."""
    by_api: dict[int, list] = {}
    order: list[int] = []
    for log in logs:
        aid = getattr(log, "api_id", None) or 0
        if aid not in by_api:
            by_api[aid] = []
            order.append(aid)
        by_api[aid].append(log)

    cards = []
    for aid in order:
        intentos = by_api[aid]  # ya vienen desc por id
        latest = summarize_api_log(intentos[0])
        latest["intentos"] = [
            {
                "id": getattr(l, "id", None),
                "exito": bool(l.exito),
                "http_status": l.http_status,
                "fecha": l.fecha,
                "n": len(intentos) - i,
            }
            for i, l in enumerate(intentos)
        ]
        latest["total_intentos"] = len(intentos)
        cards.append(latest)
    return cards
