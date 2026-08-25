"""
Puente Helios (FastAPI) dentro de Nova Projects.
Carga el paquete Helios `app` sin chocar con el Flask `app.py` del portal.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HELIOS_ROOT = Path(__file__).resolve().parent / "blueprints" / "Helios"
HELIOS_PREFIXES = (
    "/casos",
    "/flujos",
    "/catalogos",
    "/apis",
    "/admin",
    "/cambiar-password",
)

_SSO_COOKIE = "nova_helios_sso"
_SSO_SALT = "nova-helios-sso-v1"
_helios_asgi_cache = None


def is_helios_path(path: str) -> bool:
    if not path:
        return False
    if path.startswith("/api/password"):
        return True
    return any(path == p or path.startswith(p + "/") for p in HELIOS_PREFIXES)


def sign_sso_token(username: str, name: str = "") -> str:
    from itsdangerous import URLSafeTimedSerializer

    secret = os.environ.get("SECRET_KEY") or os.environ.get("HELIOS_SECRET_KEY") or "dev-secret"
    ser = URLSafeTimedSerializer(secret, salt=_SSO_SALT)
    return ser.dumps({"u": username, "n": name or username})


def load_sso_token(token: str, max_age: int = 60 * 60 * 12) -> dict | None:
    from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

    secret = os.environ.get("SECRET_KEY") or os.environ.get("HELIOS_SECRET_KEY") or "dev-secret"
    ser = URLSafeTimedSerializer(secret, salt=_SSO_SALT)
    try:
        data = ser.loads(token, max_age=max_age)
        if isinstance(data, dict) and data.get("u"):
            return data
    except (BadSignature, SignatureExpired, Exception):
        return None
    return None


def _evict_flask_app_module() -> dict:
    evicted = {}
    for name in list(sys.modules):
        if name != "app" and not name.startswith("app."):
            continue
        mod = sys.modules.get(name)
        f = (getattr(mod, "__file__", None) or "").replace("\\", "/")
        is_helios = "/blueprints/Helios/" in f
        is_flask_file = f.endswith("app.py")
        if name == "app" and is_flask_file and not is_helios:
            evicted[name] = sys.modules.pop(name)
        elif name.startswith("app.") and not is_helios:
            evicted[name] = sys.modules.pop(name)
    return evicted


def get_helios_asgi():
    global _helios_asgi_cache
    if _helios_asgi_cache is not None:
        return _helios_asgi_cache

    root = str(HELIOS_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)

    _evict_flask_app_module()
    mod = sys.modules.get("app")
    if mod is not None and not hasattr(mod, "__path__"):
        sys.modules.pop("app", None)

    try:
        from app.main import app as helios_app  # type: ignore
        from app.models import Usuario  # type: ignore
        import app.auth as helios_auth  # type: ignore
    except Exception as exc:  # noqa: BLE001
        print(f"[helios_bridge] No se pudo cargar Helios: {exc}")
        return None

    if getattr(helios_app.state, "_nova_sso_ready", False):
        _helios_asgi_cache = helios_app
        return helios_app

    def apply_sso(request, db) -> None:
        if request.session.get("user_id"):
            return
        raw = request.cookies.get(_SSO_COOKIE)
        data = load_sso_token(raw) if raw else None
        if not data:
            return
        username = str(data["u"]).strip()
        if "\\" in username:
            username = username.split("\\")[-1].strip()
        user = (
            db.query(Usuario)
            .filter(Usuario.usuario_ad == username, Usuario.activo.is_(True))
            .first()
        )
        if user is None:
            from app.config import AUTH_APP  # type: ignore
            from app.services.password_policy import hash_password  # type: ignore

            perfil = 1 if username.lower() == "admin" else 4
            user = Usuario(
                usuario_ad=username,
                nombre=str(data.get("n") or username),
                tipo_autenticacion=AUTH_APP,
                password_hash=hash_password(os.urandom(16).hex()),
                debe_cambiar_password=False,
                perfil_id=perfil,
                activo=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        request.session["user_id"] = user.id
        request.session["perfil_id"] = user.perfil_id
        request.session["nombre"] = user.nombre

    helios_auth.register_sso_hook(apply_sso)
    helios_app.state._nova_sso_ready = True
    _helios_asgi_cache = helios_app
    return helios_app


SSO_COOKIE_NAME = _SSO_COOKIE
