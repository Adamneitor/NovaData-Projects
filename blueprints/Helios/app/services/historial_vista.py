"""Resumen visual del historial de caso (sin volcar el texto técnico de reglas)."""
from __future__ import annotations

import re
from typing import Any


def _fmt_monto(raw: str | None) -> str:
    if raw is None or str(raw).strip() == "":
        return ""
    try:
        n = float(str(raw).replace(",", "").replace(" ", ""))
        entero = abs(n - round(n)) < 0.005
        if entero:
            return f"{int(round(n)):,}".replace(",", ",")
        return f"{n:,.2f}"
    except (TypeError, ValueError):
        return str(raw)


def parsear_comentario(raw: str | None) -> dict[str, Any]:
    texto = (raw or "").strip()
    out: dict[str, Any] = {"kpis": [], "razon": None, "destino": None, "titulo": None, "resumen": None}
    if not texto:
        return out

    m_api = re.search(r"API '([^']+)'", texto)
    api = m_api.group(1) if m_api else None
    pares = dict(re.findall(r"([A-Za-zÁÉÍÓÚáéíóú_]+)=([^,)|]+)", texto))
    dictamen = (pares.get("Dictamen") or pares.get("dictamen") or "").strip()
    razon = (pares.get("Razon") or pares.get("Razón") or pares.get("razon") or "").strip()
    if not razon:
        m_r = re.search(r"Razon=([^|;]+)", texto)
        if m_r:
            razon = m_r.group(1).strip().rstrip(".")
    destino = None
    m_dest = re.search(r"[→?]\s*([^.;]+)$", texto)
    if m_dest:
        destino = m_dest.group(1).strip(" .")
        if "Confirme" in destino or "Complete" in destino:
            destino = destino.split(".")[0].strip()
    if not destino:
        m2 = re.search(r"→\s*([^.]+)", texto)
        if m2:
            destino = m2.group(1).strip()

    kpis = []
    if pares.get("Monto_DOP"):
        kpis.append({"label": "Monto DOP", "value": f"RD$ {_fmt_monto(pares['Monto_DOP'])}"})
    if pares.get("Monto_USD"):
        kpis.append({"label": "Monto USD", "value": f"US$ {_fmt_monto(pares['Monto_USD'])}"})
    if dictamen:
        kpis.append({"label": "Dictamen", "value": dictamen})

    fallo = "fallo" in texto.lower() or "falló" in texto.lower()
    if api and dictamen:
        titulo = f"{api} · {dictamen}"
    elif api and fallo:
        titulo = f"{api} · no respondió"
    elif api:
        titulo = api
    else:
        titulo = None

    resumen = None
    if fallo:
        resumen = re.sub(r"^API '[^']+' fallo:\s*", "", texto, flags=re.I)[:160]
    elif razon:
        resumen = razon
    elif destino and not api:
        resumen = destino

    out.update(
        {
            "titulo": titulo,
            "razon": razon or None,
            "destino": destino,
            "kpis": kpis,
            "resumen": resumen,
            "api": api,
        }
    )
    return out


def vista_evento(h) -> dict[str, Any]:
    raw = getattr(h, "comentario", None) or ""
    parsed = parsear_comentario(raw)
    etapa = h.etapa.nombre if getattr(h, "etapa", None) else ""
    estado = h.estado.nombre if getattr(h, "estado", None) else ""
    origen = (getattr(h, "origen", None) or "MANUAL").upper()
    titulo = parsed.get("titulo") or (" · ".join(p for p in (etapa, estado) if p) or "Movimiento")
    mostrar_cuerpo = bool(parsed.get("kpis") or parsed.get("destino") or parsed.get("resumen"))
    if raw in {"Caso creado", "Caso cancelado"}:
        mostrar_cuerpo = False
        titulo = raw
    return {
        "origen": origen,
        "titulo": titulo,
        "etapa": etapa,
        "estado": estado,
        "fecha": getattr(h, "fecha", None),
        "usuario": h.usuario.nombre if getattr(h, "usuario", None) else "Sistema",
        "kpis": parsed.get("kpis") or [],
        "destino": parsed.get("destino"),
        "resumen": parsed.get("resumen"),
        "mostrar_cuerpo": mostrar_cuerpo,
        "es_api": origen == "API",
    }
