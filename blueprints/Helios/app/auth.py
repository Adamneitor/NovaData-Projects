import time
from collections import defaultdict

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import AD_DOMAIN, AUTH_AD, AUTH_APP
from app.database import get_db
from app.models import Usuario
from app.services.password_policy import (
    hash_password,
    needs_rehash,
    password_expirada,
    verify_password,
)

PERFIL_SUPER = 1
PERFIL_ADMIN_CREDENCIALES = 2
PERFIL_SOPORTE = 3
PERFIL_OPERATIVO = 4

# Rate limiting simple en memoria (por proceso). En producción: Redis.
_LOGIN_FAILS: dict[str, list[float]] = defaultdict(list)
_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_WINDOW_SEC = 300  # 5 minutos
_LOGIN_LOCK_SEC = 300

# Hook opcional (Nova Projects) para SSO vía cookie firmada
_SSO_HOOK = None


def register_sso_hook(fn) -> None:
    global _SSO_HOOK
    _SSO_HOOK = fn


def login_rate_limited(key: str) -> bool:
    ahora = time.time()
    eventos = [t for t in _LOGIN_FAILS[key] if ahora - t < _LOGIN_WINDOW_SEC]
    _LOGIN_FAILS[key] = eventos
    return len(eventos) >= _LOGIN_MAX_ATTEMPTS


def registrar_login_fallido(key: str) -> None:
    _LOGIN_FAILS[key].append(time.time())


def limpiar_login_fallidos(key: str) -> None:
    _LOGIN_FAILS.pop(key, None)


def authenticate_ad(username: str, password: str, domain: str | None = None) -> bool:
    """Valida credenciales contra Active Directory via LogonUser de Windows."""
    import ctypes
    from ctypes import wintypes

    domain = (domain or AD_DOMAIN or "").strip()
    login = username.strip()
    if "\\" in login:
        partes = login.split("\\", 1)
        domain = partes[0] or domain
        login = partes[1]
    elif "@" in login:
        login = login.split("@", 1)[0]

    if not login or not password:
        return False

    advapi32 = ctypes.windll.advapi32
    handle = wintypes.HANDLE()
    LOGON32_LOGON_NETWORK = 3
    LOGON32_PROVIDER_DEFAULT = 0
    ok = advapi32.LogonUserW(
        login,
        domain or None,
        password,
        LOGON32_LOGON_NETWORK,
        LOGON32_PROVIDER_DEFAULT,
        ctypes.byref(handle),
    )
    if not ok:
        return False
    ctypes.windll.kernel32.CloseHandle(handle)
    return True


def authenticate_user(user: Usuario, password: str, db: Session | None = None) -> bool:
    tipo = (user.tipo_autenticacion or AUTH_APP).upper()
    if tipo == AUTH_AD:
        return authenticate_ad(user.usuario_ad, password)
    ok = verify_password(password, user.password_hash)
    # Rotación transparente de PBKDF2 legado -> bcrypt
    if ok and db is not None and needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.flush()
    return ok


def usuario_debe_cambiar_password(user: Usuario) -> bool:
    if (user.tipo_autenticacion or AUTH_APP).upper() != AUTH_APP:
        return False
    return bool(user.debe_cambiar_password) or password_expirada(user)


def _login_location(request: Request, *, sso_failed: bool = False) -> str:
    path = request.url.path or "/casos"
    from urllib.parse import quote

    # Dentro del shell NOVA: volver al workspace, no a /casos a pantalla completa
    try:
        from app.embed import is_embed_request

        embed = is_embed_request(request)
    except Exception:
        embed = False

    if embed and path not in ("/",) and not path.startswith("/login"):
        next_w = f"/helios/w?to={quote(path, safe='/')}"
        base = f"/login?next={quote(next_w, safe='/?=&')}"
    elif path.startswith("/login") or path == "/":
        base = "/login?next=/helios"
    else:
        base = f"/login?next={quote(path, safe='/')}"

    if sso_failed or request.cookies.get("nova_helios_sso"):
        sep = "&" if "?" in base else "?"
        base = f"{base}{sep}sso=fail"
    return base


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Usuario:
    sso_present = bool(request.cookies.get("nova_helios_sso"))
    if _SSO_HOOK is not None:
        try:
            _SSO_HOOK(request, db)
        except Exception as exc:  # noqa: BLE001
            print(f"[helios auth] SSO hook error: {exc}")
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": _login_location(request, sso_failed=sso_present)},
        )
    user = db.get(Usuario, user_id)
    if not user or not user.activo:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER, headers={"Location": _login_location(request)}
        )
    if usuario_debe_cambiar_password(user):
        path = request.url.path
        if path not in ("/cambiar-password", "/logout", "/api/password/evaluar"):
            raise HTTPException(
                status_code=status.HTTP_303_SEE_OTHER,
                headers={"Location": "/cambiar-password"},
            )
    return user


def get_user_for_password_change(request: Request, db: Session = Depends(get_db)) -> Usuario:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"}
        )
    user = db.get(Usuario, user_id)
    if not user or not user.activo:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"}
        )
    return user


def require_perfil(*perfiles: int):
    def checker(user: Usuario = Depends(get_current_user)) -> Usuario:
        if user.perfil_id not in perfiles and user.perfil_id != PERFIL_SUPER:
            raise HTTPException(status_code=403, detail="No tiene permisos para esta seccion")
        return user

    return checker
