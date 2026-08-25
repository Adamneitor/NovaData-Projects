from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.auth import (
    authenticate_user,
    get_user_for_password_change,
    limpiar_login_fallidos,
    login_rate_limited,
    registrar_login_fallido,
    usuario_debe_cambiar_password,
)
from app.config import AUTH_APP, SQL_DATABASE, SQL_SERVER
from app.database import get_db
from app.models import Usuario
from app.services.password_policy import (
    asignar_password,
    evaluar_password,
    obtener_politica,
    password_expirada,
    politica_a_dict,
    registrar_auditoria,
    resultado_a_dict,
    verify_password,
)
from app.solutions import sanitize_next
from app.web import flash, render

router = APIRouter()


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _login_redirect(next_path: str) -> str:
    q = sanitize_next(next_path, "/helios")
    if q and q != "/helios":
        from urllib.parse import quote
        return f"/login?next={quote(q, safe='/')}"
    return "/login?next=/helios"


@router.get("/login")
def login_form(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(sanitize_next(request.query_params.get("next"), "/helios"), status_code=303)
    next_path = sanitize_next(request.query_params.get("next"), "/helios")
    return render(request, "login.html", {"next_path": next_path})


@router.post("/login")
def login(
    request: Request,
    usuario: str = Form(...),
    password: str = Form(...),
    next: str = Form("/helios"),
    db: Session = Depends(get_db),
):
    next_path = sanitize_next(next, "/helios")
    login_name = usuario.strip()
    if "\\" in login_name:
        login_name = login_name.split("\\", 1)[1]

    rate_key = f"{_client_ip(request)}|{login_name.lower()}"
    if login_rate_limited(rate_key):
        flash(
            request,
            "Demasiados intentos fallidos. Espere 5 minutos e intente de nuevo.",
            "danger",
        )
        return RedirectResponse(_login_redirect(next_path), status_code=303)

    try:
        user = db.query(Usuario).filter(Usuario.usuario_ad == login_name).first()
    except OperationalError:
        flash(
            request,
            f"No se pudo conectar a SQL Server ({SQL_SERVER} / BD {SQL_DATABASE}). "
            "Verifique red/VPN o defina HELIOS_SQL_SERVER en la sesión.",
            "danger",
        )
        return RedirectResponse(_login_redirect(next_path), status_code=303)
    if not user or not user.activo or not authenticate_user(user, password, db):
        registrar_login_fallido(rate_key)
        if user:
            registrar_auditoria(
                db,
                usuario_afectado_id=user.id,
                actor_id=None,
                evento="LOGIN_FALLIDO",
                detalle="Credenciales inválidas",
                ip=_client_ip(request),
            )
            db.commit()
        flash(request, "Usuario o contraseña incorrectos.", "danger")
        return RedirectResponse(_login_redirect(next_path), status_code=303)

    limpiar_login_fallidos(rate_key)
    db.commit()  # persist rehash if any

    # Expiración -> forzar cambio
    if (user.tipo_autenticacion or AUTH_APP).upper() == AUTH_APP and password_expirada(user):
        user.debe_cambiar_password = True
        registrar_auditoria(
            db,
            usuario_afectado_id=user.id,
            actor_id=user.id,
            evento="EXPIRACION",
            detalle="Contraseña expirada: se exige cambio",
            ip=_client_ip(request),
        )
        db.commit()

    request.session["user_id"] = user.id
    request.session["user_nombre"] = user.nombre
    request.session["perfil_id"] = user.perfil_id

    if usuario_debe_cambiar_password(user):
        motivo = "expiró" if password_expirada(user) else "debe reiniciarse"
        flash(request, f"Su contraseña {motivo}. Establezca una nueva antes de continuar.", "warning")
        return RedirectResponse("/cambiar-password", status_code=303)
    return RedirectResponse(next_path, status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@router.get("/cambiar-password")
def cambiar_password_form(
    request: Request,
    user: Usuario = Depends(get_user_for_password_change),
    db: Session = Depends(get_db),
):
    if (user.tipo_autenticacion or AUTH_APP).upper() != AUTH_APP:
        return RedirectResponse("/helios", status_code=303)
    pol = obtener_politica(db)
    return render(
        request,
        "cambiar_password.html",
        {
            "obligatorio": usuario_debe_cambiar_password(user),
            "usuario": user,
            "politica": pol,
            "politica_json": politica_a_dict(pol),
            "por_expiracion": password_expirada(user),
        },
    )


@router.post("/cambiar-password")
def cambiar_password(
    request: Request,
    password_actual: str = Form(...),
    password_nueva: str = Form(...),
    password_confirmacion: str = Form(...),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_user_for_password_change),
):
    if (user.tipo_autenticacion or AUTH_APP).upper() != AUTH_APP:
        flash(request, "Los usuarios de Active Directory no cambian contraseña aquí.", "warning")
        return RedirectResponse("/casos", status_code=303)

    if not verify_password(password_actual, user.password_hash):
        flash(request, "La contraseña actual es incorrecta.", "danger")
        return RedirectResponse("/cambiar-password", status_code=303)

    if password_nueva != password_confirmacion:
        flash(request, "La confirmación no coincide con la nueva contraseña.", "danger")
        return RedirectResponse("/cambiar-password", status_code=303)

    evento = "CAMBIO_EXPIRACION" if password_expirada(user) else "CAMBIO_USUARIO"
    res = asignar_password(
        db,
        user,
        password_nueva,
        actor=user,
        evento=evento,
        forzar_cambio_siguiente=False,
        ip=_client_ip(request),
        detalle="Cambio de contraseña por el usuario",
    )
    if not res.valida:
        db.rollback()
        flash(request, "Contraseña no válida: " + "; ".join(res.errores), "danger")
        return RedirectResponse("/cambiar-password", status_code=303)

    db.commit()
    flash(request, "Contraseña actualizada correctamente.")
    return RedirectResponse("/helios", status_code=303)


@router.get("/api/password/politica")
def api_politica(db: Session = Depends(get_db)):
    return JSONResponse(politica_a_dict(obtener_politica(db)))


@router.post("/api/password/evaluar")
async def api_evaluar(request: Request, db: Session = Depends(get_db)):
    """Evaluación en tiempo real (no autentica; solo score/validación de reglas)."""
    data = await request.json()
    password = str(data.get("password") or "")
    pol = obtener_politica(db)
    return JSONResponse(resultado_a_dict(evaluar_password(password, pol)))
