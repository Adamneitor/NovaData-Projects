from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.auth import get_current_user
from app.models import Usuario
from app.solutions import SOLUTIONS, get_solution, sanitize_next
from app.web import render

router = APIRouter(tags=["plataforma"])


@router.get("/")
def catalogo(request: Request):
    """Página pública: catálogo de soluciones Nova."""
    return render(
        request,
        "plataforma/catalogo.html",
        {
            "solutions": SOLUTIONS,
            "logged": bool(request.session.get("user_id")),
        },
    )


@router.get("/entrar/{solution_id}")
def entrar_solucion(solution_id: str, request: Request):
    """
    Click en una solución del catálogo.
    Activa → login (si hace falta) o home del producto.
    Locked → vuelve al catálogo con flag de próximamente.
    """
    sol = get_solution(solution_id)
    if not sol:
        return RedirectResponse("/", status_code=303)
    if not sol["active"]:
        return RedirectResponse(f"/?locked={sol['id']}", status_code=303)

    target = sol["home_path"] or "/helios"
    if not request.session.get("user_id"):
        return RedirectResponse(f"/login?next={target}", status_code=303)
    return RedirectResponse(target, status_code=303)


@router.get("/helios")
def helios_home(request: Request, user: Usuario = Depends(get_current_user)):
    sol = get_solution("helios")
    tiles = [
        {
            "title": "BPM operativo",
            "desc": "Flujos, casos, documentos y datos complementarios",
            "href": "/casos",
            "status": "activo",
            "icon": "bi-briefcase",
        },
        {
            "title": "Captación & Ventas",
            "desc": "Prospectos y canales de originación",
            "href": None,
            "status": "pronto",
            "icon": "bi-people",
        },
        {
            "title": "Preaprobaciones & Buró",
            "desc": "Consultas y dictámenes vía APIs del flujo",
            "href": "/apis",
            "status": "parcial",
            "icon": "bi-shield-check",
        },
        {
            "title": "Motor de decisión",
            "desc": "Políticas y ruteo de aprobación",
            "href": None,
            "status": "pronto",
            "icon": "bi-gear",
        },
        {
            "title": "Analítica de originación",
            "desc": "Embudo, SLA y tasas",
            "href": None,
            "status": "pronto",
            "icon": "bi-graph-up",
        },
        {
            "title": "Diseño BPM",
            "desc": "Flujos, catálogos y configuración",
            "href": "/flujos",
            "status": "activo",
            "icon": "bi-diagram-3",
        },
    ]
    return render(
        request,
        "plataforma/helios_home.html",
        {"solution": sol, "tiles": tiles, "user": user},
    )
