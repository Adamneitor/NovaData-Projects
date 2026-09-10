"""Normaliza el JSON de buró al documento visual (cuentas + vector 24M)."""
from __future__ import annotations

from typing import Any


def _celda(valor: Any) -> dict[str, str]:
    s = str(valor).strip() if valor is not None else ""
    if s.lower() in {"", "-", "na", "none", "–"}:
        return {"v": "–", "cls": "na"}
    if s.lower() in {"0", "ok"}:
        return {"v": "0", "cls": "ok"}
    if s.lower() in {"1", "late"}:
        return {"v": "1", "cls": "c1"}
    if s == "2":
        return {"v": "2", "cls": "c2"}
    return {"v": s[:2], "cls": "c3"}


def vector_cuenta(cta: dict[str, Any]) -> list[dict[str, str]]:
    hist = cta.get("Historial_Pago") or cta.get("historial") or cta.get("vector") or []
    if hist and isinstance(hist, list) and hist and isinstance(hist[0], dict):
        return [_celda(x.get("v", x.get("valor", "-"))) for x in hist]
    if hist:
        return [_celda(x) for x in hist]
    pago = cta.get("pago24") or []
    mapa = {"ok": "0", "late": "1", "na": "-"}
    return [_celda(mapa.get(str(p), p)) for p in pago]


def _num(v: Any) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(str(v).replace(",", "").replace("$", "").replace("RD", "").strip())
    except (TypeError, ValueError):
        return 0.0


def normalizar_reporte_buro(r: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(r, dict):
        return {}
    out = dict(r)
    cuentas: list[dict[str, Any]] = []
    atraso_monto = 0.0
    for raw in r.get("Cuentas") or []:
        if not isinstance(raw, dict):
            continue
        c = dict(raw)
        c["vector"] = vector_cuenta(c)
        c.setdefault("entidad", c.get("Banco") or c.get("Entidad") or "—")
        c.setdefault("producto", c.get("Tipo") or c.get("producto") or "")
        estado = (c.get("estado") or c.get("Estatus") or "").lower()
        if estado in {"abierta", "abierto", "normal", "activa"}:
            c["estado"] = "abierta"
        elif estado:
            c["estado"] = "cerrada"
        c.setdefault("apertura", c.get("Fecha_Apertura") or "")
        c.setdefault("aprobado", _num(c.get("aprobado") or c.get("Credito_Aprobado")))
        c.setdefault("adeudado", _num(c.get("adeudado") or c.get("Monto_Adeudado")))
        c.setdefault("cuota", _num(c.get("cuota") or c.get("Pago_Cuota")))
        c.setdefault("vencido", _num(c.get("vencido") or c.get("Atraso_Total")))
        atraso_monto += float(c.get("vencido") or 0)
        cuentas.append(c)
    out["Cuentas"] = cuentas
    if cuentas and not out.get("CuentasActivas"):
        out["CuentasActivas"] = sum(1 for c in cuentas if c.get("estado") == "abierta")
        out["CuentasCerradas"] = sum(1 for c in cuentas if c.get("estado") != "abierta")
    # AtrasoTotal del demo a veces es días; si hay vencidos, preferir monto
    if atraso_monto > 0:
        out["AtrasoMonto"] = atraso_monto
    else:
        out["AtrasoMonto"] = _num(out.get("AtrasoTotal"))
    return out
