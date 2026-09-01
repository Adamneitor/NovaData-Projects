"""Catálogo de soluciones Nova (Helios, Hermes, Venus, Zeus, Ares)."""
from __future__ import annotations

import os

SOLUTIONS = [
    {
        "id": "helios",
        "name": "Helios",
        "tagline": "Núcleo que energiza y orquesta la originación",
        "subtitle": "Fábrica de Crédito",
        "desc": "Originación, BPM operativo, buró y decisión en un solo flujo de trabajo.",
        "pitch": "Opera solicitudes de punta a punta con BPM, catálogos y APIs en un solo lienzo.",
        "hub_line": "Fábrica de Crédito · originación, BPM, buró y decisión",
        "capabilities": [
            "Ventas y captación",
            "Preaprobaciones y buró",
            "Motor de decisión y aprobación",
        ],
        "active": True,
        "home_endpoint": "helios_home",
        "icon": "sun",
        "color": "#5B52E8",
    },
    {
        "id": "hermes",
        "name": "Hermes",
        "tagline": "Impulsa el uso mediante recompensas",
        "subtitle": "Programa de Fidelidad",
        "desc": "Cashback, redención y campañas personalizadas.",
        "pitch": "Diseña programas de puntos y recompensas que activen el uso recurrente.",
        "hub_line": "Cashback, redención y campañas personalizadas.",
        "capabilities": [
            "Cashback y acumulación de puntos",
            "Redención de beneficios",
            "Campañas personalizadas",
        ],
        "active": False,
        "home_endpoint": None,
        "icon": "gift",
        "color": "#5FA98F",
    },
    {
        "id": "venus",
        "name": "Venus",
        "tagline": "Reactiva y fortalece la relación con el cliente",
        "subtitle": "Motivación al uso",
        "desc": "Inactivos, reenganche e incentivos.",
        "pitch": "Campañas de reactivación con segmentación y motivadores de uso.",
        "hub_line": "Inactivos, reenganche e incentivos.",
        "capabilities": [
            "Identificación de inactivos",
            "Estrategias de reenganche",
            "Incentivos y promociones",
        ],
        "active": False,
        "home_endpoint": None,
        "icon": "heart",
        "color": "#C4808F",
    },
    {
        "id": "zeus",
        "name": "Zeus",
        "tagline": "Optimiza la recuperación con inteligencia estratégica",
        "subtitle": "Score de cobranzas",
        "desc": "Riesgo, segmentación y colas.",
        "pitch": "Prioriza gestión de cobranza con score e inteligencia de recuperación.",
        "hub_line": "Riesgo, segmentación y colas.",
        "capabilities": [
            "Priorización por riesgo",
            "Segmentación dinámica",
            "Gestión eficiente de colas",
        ],
        "active": False,
        "home_endpoint": None,
        "icon": "bolt",
        "color": "#7B9BC9",
    },
    {
        "id": "ares",
        "name": "Ares",
        "tagline": "Control operativo de activos físicos",
        "subtitle": "Inventario de plásticos",
        "desc": "Trazabilidad, stock y entrega.",
        "pitch": "Controla inventario físico y trazabilidad operativa de activos.",
        "hub_line": "Trazabilidad, stock y entrega.",
        "capabilities": [
            "Inventario y trazabilidad",
            "Control de stock",
            "Gestión de entrega",
        ],
        "active": False,
        "home_endpoint": None,
        "icon": "box",
        "color": "#9E9BA6",
    },
]


def get_solution(solution_id: str) -> dict | None:
    sid = (solution_id or "").strip().lower()
    for s in SOLUTIONS:
        if s["id"] == sid:
            return s
    return None


def default_entitlements() -> set[str]:
    """Productos del plan (demo). Override: NOVA_ENTITLEMENTS=helios,hermes"""
    raw = os.environ.get("NOVA_ENTITLEMENTS", "helios")
    ids = {x.strip().lower() for x in raw.split(",") if x.strip()}
    valid = {s["id"] for s in SOLUTIONS}
    return ids & valid or {"helios"}


def enrich_solutions(entitled: set[str] | None = None) -> list[dict]:
    """Agrega entitled/status para hub y marketing."""
    entitled = entitled if entitled is not None else default_entitlements()
    out: list[dict] = []
    for s in SOLUTIONS:
        item = dict(s)
        is_entitled = item["id"] in entitled
        item["entitled"] = is_entitled
        if is_entitled and item.get("active"):
            item["status"] = "live"
        elif is_entitled:
            item["status"] = "roadmap"
        else:
            item["status"] = "contractable"
        out.append(item)
    return out


SAFE_NEXT = (
    "helios_home",
    "helios_casos",
    "home",
    "portal_view",
    "admin_dashboard",
    "module_view",
    "launcher",
    "hub",
    "contacto",
)


def sanitize_next_path(path: str | None, default: str = "/") -> str:
    if not path:
        return default
    p = path.strip()
    if not p.startswith("/") or p.startswith("//") or "://" in p:
        return default
    allowed = (
        "/helios",
        "/casos",
        "/flujos",
        "/catalogos",
        "/apis",
        "/admin",
        "/cambiar-password",
        "/home",
        "/portal/",
        "/admin/",
        "/module/",
        "/soluciones/",
        "/entrar/",
        "/app",
        "/contacto",
        "/explorar",
    )
    if p == "/" or any(p == a.rstrip("/") or p.startswith(a) for a in allowed):
        return p
    return default
