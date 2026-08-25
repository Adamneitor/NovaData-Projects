from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import (
    PERFIL_ADMIN_CREDENCIALES,
    PERFIL_SUPER,
    get_current_user,
    require_perfil,
)
from app.config import AUTH_AD, AUTH_APP
from app.database import get_db
from app.models import AuditoriaPassword, GrupoUsuario, PerfilUsuario, PoliticaPassword, Usuario
from app.services.ambiente import reiniciar_ambiente_prueba
from app.services.password_policy import (
    asignar_password,
    evaluar_password,
    obtener_politica,
    password_vence_en,
)
from app.web import flash, render

router = APIRouter(prefix="/admin", dependencies=[Depends(require_perfil(PERFIL_ADMIN_CREDENCIALES))])


# ------------------------------- Usuarios ---------------------------------


@router.get("/usuarios")
def usuarios(request: Request, db: Session = Depends(get_db)):
    users = db.query(Usuario).order_by(Usuario.nombre).all()
    vencimientos = {u.id: password_vence_en(u) for u in users}
    return render(
        request,
        "admin/usuarios.html",
        {
            "usuarios": users,
            "perfiles": db.query(PerfilUsuario).all(),
            "grupos": db.query(GrupoUsuario).order_by(GrupoUsuario.nombre).all(),
            "auth_app": AUTH_APP,
            "auth_ad": AUTH_AD,
            "politica": obtener_politica(db),
            "vencimientos": vencimientos,
        },
    )


@router.post("/usuarios/crear")
def crear_usuario(
    request: Request,
    usuario_ad: str = Form(...),
    nombre: str = Form(...),
    tipo_autenticacion: str = Form(AUTH_APP),
    password: str = Form(""),
    pedir_cambio_password: str | None = Form(None),
    dias_vigencia_password: str = Form(""),
    perfil_id: int = Form(...),
    db: Session = Depends(get_db),
    actor: Usuario = Depends(get_current_user),
):
    tipo = tipo_autenticacion.strip().upper()
    if tipo not in (AUTH_APP, AUTH_AD):
        flash(request, "Tipo de autenticación inválido.", "danger")
        return RedirectResponse("/admin/usuarios", status_code=303)

    login = usuario_ad.strip()
    if "\\" in login:
        login = login.split("\\", 1)[1]
    if db.query(Usuario).filter(Usuario.usuario_ad == login).first():
        flash(request, "Ya existe un usuario con ese login.", "danger")
        return RedirectResponse("/admin/usuarios", status_code=303)

    vigencia = None
    if tipo == AUTH_APP and dias_vigencia_password.strip():
        try:
            vigencia = int(dias_vigencia_password.strip())
            if vigencia <= 0:
                vigencia = None
        except ValueError:
            flash(request, "Vigencia de contraseña inválida.", "danger")
            return RedirectResponse("/admin/usuarios", status_code=303)

    forzar_cambio = tipo == AUTH_APP and pedir_cambio_password == "1"

    if tipo == AUTH_APP:
        if not password.strip():
            flash(request, "Los usuarios de aplicación requieren una contraseña temporal.", "danger")
            return RedirectResponse("/admin/usuarios", status_code=303)
        pol = obtener_politica(db)
        ev = evaluar_password(password.strip(), pol)
        if not ev.valida:
            flash(request, "Contraseña no cumple la política: " + "; ".join(ev.errores), "danger")
            return RedirectResponse("/admin/usuarios", status_code=303)

    user = Usuario(
        usuario_ad=login,
        nombre=nombre.strip(),
        tipo_autenticacion=tipo,
        password_hash=None,
        debe_cambiar_password=forzar_cambio if tipo == AUTH_APP else False,
        dias_vigencia_password=vigencia if tipo == AUTH_APP else None,
        perfil_id=perfil_id,
    )
    db.add(user)
    db.flush()

    if tipo == AUTH_APP:
        asignar_password(
            db,
            user,
            password.strip(),
            actor=actor,
            evento="ALTA_ADMIN",
            forzar_cambio_siguiente=forzar_cambio,
            ip=request.client.host if request.client else None,
            detalle="Alta de usuario con contraseña temporal" if forzar_cambio else "Alta de usuario",
        )

    db.commit()
    extra = " Deberá cambiar la contraseña en su próximo login." if forzar_cambio else ""
    flash(
        request,
        f"Usuario '{login}' creado ({'Active Directory' if tipo == AUTH_AD else 'Aplicación'}).{extra}",
    )
    return RedirectResponse("/admin/usuarios", status_code=303)


@router.post("/usuarios/{usuario_id}/actualizar")
def actualizar_usuario(
    request: Request,
    usuario_id: int,
    nombre: str = Form(...),
    tipo_autenticacion: str = Form(AUTH_APP),
    perfil_id: int = Form(...),
    activo: str | None = Form(None),
    password: str = Form(""),
    pedir_cambio_password: str | None = Form(None),
    dias_vigencia_password: str = Form(""),
    db: Session = Depends(get_db),
    actor: Usuario = Depends(get_current_user),
):
    tipo = tipo_autenticacion.strip().upper()
    if tipo not in (AUTH_APP, AUTH_AD):
        flash(request, "Tipo de autenticación inválido.", "danger")
        return RedirectResponse("/admin/usuarios", status_code=303)

    user = db.get(Usuario, usuario_id)
    user.nombre = nombre.strip()
    user.perfil_id = perfil_id
    user.tipo_autenticacion = tipo
    era_activo = user.activo
    user.activo = activo == "1"
    if era_activo and not user.activo:
        user.fecha_inactivacion = datetime.now()

    if tipo == AUTH_AD:
        user.password_hash = None
        user.debe_cambiar_password = False
        user.dias_vigencia_password = None
        user.password_fecha_cambio = None
    else:
        if dias_vigencia_password.strip():
            try:
                v = int(dias_vigencia_password.strip())
                user.dias_vigencia_password = v if v > 0 else None
            except ValueError:
                flash(request, "Vigencia de contraseña inválida.", "danger")
                return RedirectResponse("/admin/usuarios", status_code=303)
        else:
            user.dias_vigencia_password = None

        forzar = pedir_cambio_password == "1"
        if password.strip():
            res = asignar_password(
                db,
                user,
                password.strip(),
                actor=actor,
                evento="RESET_ADMIN",
                forzar_cambio_siguiente=forzar,
                ip=request.client.host if request.client else None,
                detalle="Reinicio de contraseña por administrador",
            )
            if not res.valida:
                db.rollback()
                flash(request, "Contraseña no válida: " + "; ".join(res.errores), "danger")
                return RedirectResponse("/admin/usuarios", status_code=303)
        else:
            if not user.password_hash:
                flash(request, "Los usuarios de aplicación requieren contraseña.", "danger")
                return RedirectResponse("/admin/usuarios", status_code=303)
            user.debe_cambiar_password = forzar
            if forzar:
                db.add(
                    AuditoriaPassword(
                        usuario_afectado_id=user.id,
                        actor_id=actor.id,
                        evento="FORZAR_CAMBIO",
                        detalle="Administrador marcó reinicio obligatorio",
                        ip=request.client.host if request.client else None,
                    )
                )

    db.commit()
    flash(request, "Usuario actualizado.")
    return RedirectResponse("/admin/usuarios", status_code=303)


@router.post("/usuarios/{usuario_id}/grupos")
async def asignar_grupos(request: Request, usuario_id: int, db: Session = Depends(get_db)):
    form = await request.form()
    grupo_ids = [int(v) for v in form.getlist("grupo_ids")]
    user = db.get(Usuario, usuario_id)
    user.grupos = db.query(GrupoUsuario).filter(GrupoUsuario.id.in_(grupo_ids)).all() if grupo_ids else []
    db.commit()
    flash(request, f"Grupos de '{user.usuario_ad}' actualizados.")
    return RedirectResponse("/admin/usuarios", status_code=303)


# -------------------------------- Grupos ----------------------------------


@router.get("/grupos")
def grupos(request: Request, db: Session = Depends(get_db)):
    return render(
        request,
        "admin/grupos.html",
        {"grupos": db.query(GrupoUsuario).order_by(GrupoUsuario.nombre).all()},
    )


@router.post("/grupos/crear")
def crear_grupo(
    request: Request,
    nombre: str = Form(...),
    descripcion: str = Form(""),
    db: Session = Depends(get_db),
):
    if db.query(GrupoUsuario).filter(GrupoUsuario.nombre == nombre.strip()).first():
        flash(request, "Ya existe un grupo con ese nombre.", "danger")
    else:
        db.add(GrupoUsuario(nombre=nombre.strip(), descripcion=descripcion.strip() or None))
        db.commit()
        flash(request, f"Grupo '{nombre}' creado.")
    return RedirectResponse("/admin/grupos", status_code=303)


@router.post("/grupos/{grupo_id}/actualizar")
def actualizar_grupo(
    request: Request,
    grupo_id: int,
    nombre: str = Form(...),
    descripcion: str = Form(""),
    db: Session = Depends(get_db),
):
    g = db.get(GrupoUsuario, grupo_id)
    g.nombre = nombre.strip()
    g.descripcion = descripcion.strip() or None
    db.commit()
    flash(request, "Grupo actualizado.")
    return RedirectResponse("/admin/grupos", status_code=303)


@router.post("/grupos/{grupo_id}/eliminar")
def eliminar_grupo(request: Request, grupo_id: int, db: Session = Depends(get_db)):
    g = db.get(GrupoUsuario, grupo_id)
    try:
        g.usuarios = []
        db.delete(g)
        db.commit()
        flash(request, "Grupo eliminado.")
    except Exception:
        db.rollback()
        flash(request, "No se pudo eliminar: el grupo esta asociado a etapas.", "danger")
    return RedirectResponse("/admin/grupos", status_code=303)


# ------------------------ Políticas de contraseña -------------------------


@router.get("/politicas-password")
def politicas_password(request: Request, db: Session = Depends(get_db)):
    return render(
        request,
        "admin/politicas_password.html",
        {"politica": obtener_politica(db)},
    )


@router.post("/politicas-password")
def guardar_politicas_password(
    request: Request,
    longitud_minima: int = Form(...),
    mayusculas: str = Form(...),
    requiere_numero: str | None = Form(None),
    requiere_especial: str | None = Form(None),
    max_repetidos_consecutivos: int = Form(...),
    permite_espacios: str | None = Form(None),
    historial_no_reutilizar: int = Form(...),
    vigencia_default_dias: str = Form(""),
    db: Session = Depends(get_db),
    actor: Usuario = Depends(get_current_user),
):
    if longitud_minima < 6 or longitud_minima > 128:
        flash(request, "La longitud mínima debe estar entre 6 y 128.", "danger")
        return RedirectResponse("/admin/politicas-password", status_code=303)
    if mayusculas not in ("ninguna", "inicio", "final", "cualquiera"):
        flash(request, "Opción de mayúsculas inválida.", "danger")
        return RedirectResponse("/admin/politicas-password", status_code=303)

    pol = obtener_politica(db)
    pol.longitud_minima = longitud_minima
    pol.mayusculas = mayusculas
    pol.requiere_numero = requiere_numero == "1"
    pol.requiere_especial = requiere_especial == "1"
    pol.max_repetidos_consecutivos = max(0, max_repetidos_consecutivos)
    pol.permite_espacios = permite_espacios == "1"
    pol.historial_no_reutilizar = max(0, historial_no_reutilizar)
    if vigencia_default_dias.strip():
        try:
            vd = int(vigencia_default_dias.strip())
            pol.vigencia_default_dias = vd if vd > 0 else None
        except ValueError:
            flash(request, "Vigencia por defecto inválida.", "danger")
            return RedirectResponse("/admin/politicas-password", status_code=303)
    else:
        pol.vigencia_default_dias = None
    pol.fecha_modificacion = datetime.now()
    pol.modificado_por_id = actor.id
    db.add(
        AuditoriaPassword(
            usuario_afectado_id=actor.id,
            actor_id=actor.id,
            evento="POLITICA",
            detalle=(
                f"Política actualizada: min={pol.longitud_minima}, mayus={pol.mayusculas}, "
                f"num={pol.requiere_numero}, esp={pol.requiere_especial}, "
                f"rep={pol.max_repetidos_consecutivos}, hist={pol.historial_no_reutilizar}"
            ),
            ip=request.client.host if request.client else None,
        )
    )
    db.commit()
    flash(request, "Políticas de contraseña actualizadas.")
    return RedirectResponse("/admin/politicas-password", status_code=303)


# ------------------------ Ambiente de prueba ------------------------------


@router.get("/ambiente", dependencies=[Depends(require_perfil(PERFIL_SUPER))])
def ambiente(request: Request):
    return render(request, "admin/ambiente.html")


@router.post("/ambiente/reiniciar", dependencies=[Depends(require_perfil(PERFIL_SUPER))])
def reiniciar_ambiente(request: Request, db: Session = Depends(get_db)):
    try:
        reiniciar_ambiente_prueba(db)
        flash(
            request,
            "Ambiente de prueba reiniciado. Se conservaron usuarios, grupos y clientes. "
            "Flujos, APIs, documentos, datos y casos fueron eliminados.",
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        flash(request, f"No se pudo reiniciar el ambiente: {exc}", "danger")
    return RedirectResponse("/admin/ambiente", status_code=303)
