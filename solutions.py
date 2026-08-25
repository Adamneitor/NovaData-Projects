"""Catálogo de soluciones Nova (Helios, Hermes, Venus, Zeus, Ares)."""

SOLUTIONS = [
    {
        "id": "helios",
        "name": "Helios",
        "tagline": "Núcleo que energiza y orquesta la originación",
        "subtitle": "Fábrica de Crédito",
        "desc": "Originación, BPM operativo, buró y decisión en un solo flujo de trabajo.",
        "active": True,
        "home_endpoint": "helios_home",
        "icon": "sun",
        "color": "#F59E0B",
    },
    {
        "id": "hermes",
        "name": "Hermes",
        "tagline": "Impulsa el uso mediante recompensas",
        "subtitle": "Programa de Fidelidad",
        "desc": "Programa de fidelidad y recompensas para impulsar el uso de productos.",
        "active": False,
        "home_endpoint": None,
        "icon": "gift",
        "color": "#34D399",
    },
    {
        "id": "venus",
        "name": "Venus",
        "tagline": "Reactiva y fortalece la relación con el cliente",
        "subtitle": "Motivación al uso",
        "desc": "Campañas y motivadores para reactivar la relación con el cliente.",
        "active": False,
        "home_endpoint": None,
        "icon": "heart",
        "color": "#FB7185",
    },
    {
        "id": "zeus",
        "name": "Zeus",
        "tagline": "Optimiza la recuperación con inteligencia estratégica",
        "subtitle": "Score de cobranzas",
        "desc": "Score e inteligencia estratégica para optimizar la recuperación.",
        "active": False,
        "home_endpoint": None,
        "icon": "bolt",
        "color": "#60A5FA",
    },
    {
        "id": "ares",
        "name": "Ares",
        "tagline": "Control operativo de activos físicos",
        "subtitle": "Inventario de plásticos",
        "desc": "Control operativo e inventario de activos físicos (plásticos).",
        "active": False,
        "home_endpoint": None,
        "icon": "box",
        "color": "#A8A29E",
    },
]


def get_solution(solution_id: str) -> dict | None:
    sid = (solution_id or "").strip().lower()
    for s in SOLUTIONS:
        if s["id"] == sid:
            return s
    return None


SAFE_NEXT = (
    "helios_home",
    "helios_casos",
    "home",
    "portal_view",
    "admin_dashboard",
    "module_view",
    "launcher",
)


def sanitize_next_path(path: str | None, default: str = "/") -> str:
    if not path:
        return default
    p = path.strip()
    if not p.startswith("/") or p.startswith("//") or "://" in p:
        return default
    allowed = ("/helios", "/home", "/portal/", "/admin/", "/module/", "/soluciones/")
    if p == "/" or any(p == a.rstrip("/") or p.startswith(a) for a in allowed):
        return p
    return default
