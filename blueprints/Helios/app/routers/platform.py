from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import PERFIL_SOPORTE, PERFIL_SUPER, get_current_user
from app.database import get_db
from app.models import Caso, Etapa, EtapaGrupo, Flujo, Usuario
from app.solutions import SOLUTIONS, get_solution
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
def helios_home(
    request: Request,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sol = get_solution("helios")
    q_all = db.query(Caso)
    activos = q_all.filter(Caso.estado_general == "ACTIVO").count()
    if user.perfil_id in (PERFIL_SUPER, PERFIL_SOPORTE):
        bandeja = activos
    else:
        gids = [g.id for g in (user.grupos or [])]
        if gids:
            etapa_ids = [
                r[0]
                for r in db.query(EtapaGrupo.etapa_id)
                .filter(EtapaGrupo.grupo_id.in_(gids))
                .distinct()
                .all()
            ]
            bandeja = (
                q_all.filter(Caso.estado_general == "ACTIVO", Caso.etapa_actual_id.in_(etapa_ids)).count()
                if etapa_ids
                else 0
            )
        else:
            bandeja = 0
    comite = (
        q_all.join(Etapa, Caso.etapa_actual_id == Etapa.id)
        .filter(Caso.estado_general == "ACTIVO", Etapa.nombre.ilike("%comit%"))
        .count()
    )
    n_flujos = db.query(Flujo).filter(Flujo.activo).count()
    stats = {
        "bandeja": bandeja,
        "activos": activos,
        "pendientes": 0,
        "comite": comite,
    }
    tiles = [
        {"title": "Casos", "desc": "Tu bandeja de trabajo", "href": "/casos", "icon": "bi-kanban", "count": bandeja},
        {"title": "Clientes 360", "desc": "Ficha y casos por cliente", "href": "/catalogos/clientes", "icon": "bi-people", "count": None},
        {"title": "Flujos", "desc": f"Diseño BPM · {n_flujos} flujos", "href": "/flujos", "icon": "bi-diagram-3", "count": None},
        {"title": "APIs", "desc": "Integraciones del motor", "href": "/apis", "icon": "bi-plugin", "count": None},
        {"title": "Documentos", "desc": "Catálogo documental", "href": "/catalogos/documentos", "icon": "bi-file-earmark", "count": None},
        {"title": "Datos complementarios", "desc": "Campos del expediente", "href": "/catalogos/datos", "icon": "bi-sliders", "count": None},
        {"title": "Tipos de flujo", "desc": "Crédito · Operativo", "href": "/catalogos/tipos-flujo", "icon": "bi-tags", "count": None},
        {"title": "Seguridad", "desc": "Usuarios · grupos · políticas", "href": "/admin/usuarios", "icon": "bi-shield-lock", "count": None},
    ]
    return render(
        request,
        "plataforma/helios_home.html",
        {"solution": sol, "tiles": tiles, "usuario": user, "user": user, "stats": stats},
    )
