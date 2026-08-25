"""Catálogo de soluciones Nova Data Solutions (plataforma)."""

from __future__ import annotations

SOLUTIONS: list[dict] = [
    {
        "id": "helios",
        "name": "Helios",
        "tagline": "Núcleo que energiza y orquesta la originación",
        "subtitle": "Fábrica de Crédito",
        "bullets": [
            "Ventas y captación",
            "Preaprobaciones y buró",
            "Motor de decisión y aprobación",
        ],
        "active": True,
        "home_path": "/helios",
        "accent": "#5B52E8",
        "icon": "bi-sun",
    },
    {
        "id": "hermes",
        "name": "Hermes",
        "tagline": "Impulsa el uso mediante recompensas",
        "subtitle": "Programa de Fidelidad",
        "bullets": [
            "Cashback y acumulación de puntos",
            "Redención de beneficios",
            "Campañas personalizadas",
        ],
        "active": False,
        "home_path": None,
        "accent": "#34D399",
        "icon": "bi-gift",
    },
    {
        "id": "venus",
        "name": "Venus",
        "tagline": "Reactiva y fortalece la relación con el cliente",
        "subtitle": "Motivación al uso",
        "bullets": [
            "Identificación de inactivos",
            "Estrategias de reenganche",
            "Incentivos y promociones",
        ],
        "active": False,
        "home_path": None,
        "accent": "#FB7185",
        "icon": "bi-heart",
    },
    {
        "id": "zeus",
        "name": "Zeus",
        "tagline": "Optimiza la recuperación con inteligencia estratégica",
        "subtitle": "Score de cobranzas",
        "bullets": [
            "Priorización por riesgo",
            "Segmentación dinámica",
            "Gestión eficiente de colas",
        ],
        "active": False,
        "home_path": None,
        "accent": "#60A5FA",
        "icon": "bi-lightning",
    },
    {
        "id": "ares",
        "name": "Ares",
        "tagline": "Control operativo de activos físicos",
        "subtitle": "Inventario de plásticos",
        "bullets": [
            "Inventario y trazabilidad",
            "Control de stock",
            "Gestión de entrega",
        ],
        "active": False,
        "home_path": None,
        "accent": "#A8A29E",
        "icon": "bi-box-seam",
    },
]


def get_solution(solution_id: str) -> dict | None:
    sid = (solution_id or "").strip().lower()
    for s in SOLUTIONS:
        if s["id"] == sid:
            return s
    return None


SAFE_NEXT_PREFIXES = ("/helios", "/casos", "/flujos", "/apis", "/catalogos", "/admin", "/cambiar-password")


def sanitize_next(path: str | None, default: str = "/helios") -> str:
    """Solo permite rutas internas relativas seguras."""
    if not path:
        return default
    p = path.strip()
    if not p.startswith("/") or p.startswith("//") or "://" in p:
        return default
    if p == "/" or any(p == pref or p.startswith(pref + "/") for pref in SAFE_NEXT_PREFIXES):
        return p
    return default
