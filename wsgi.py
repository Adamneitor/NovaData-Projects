"""
WSGI de entrada para Railway/gunicorn.
Carga Helios primero (paquete `app`), luego el portal Flask desde app.py
como módulo `nova_portal` para evitar el choque de nombres.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from a2wsgi import ASGIMiddleware
from werkzeug.middleware.proxy_fix import ProxyFix

ROOT = Path(__file__).resolve().parent

# 1) Helios FastAPI (paquete blueprints/Helios/app)
from helios_bridge import get_helios_asgi, is_helios_path  # noqa: E402

_helios_asgi = get_helios_asgi()
_helios_wsgi = ASGIMiddleware(_helios_asgi) if _helios_asgi is not None else None

# 2) Portal Flask: cargar app.py bajo otro nombre de módulo
_portal_path = ROOT / "app.py"
_spec = importlib.util.spec_from_file_location("nova_portal", _portal_path)
if _spec is None or _spec.loader is None:
    raise RuntimeError("No se pudo cargar app.py del portal NOVA")
_nova_portal = importlib.util.module_from_spec(_spec)
sys.modules["nova_portal"] = _nova_portal
_spec.loader.exec_module(_nova_portal)
flask_app = _nova_portal.app
# Railway / proxies: confiar en X-Forwarded-Proto para cookies Secure
flask_app.wsgi_app = ProxyFix(flask_app.wsgi_app, x_for=1, x_proto=1, x_host=1)


def application(environ, start_response):
    path = environ.get("PATH_INFO") or ""
    if _helios_wsgi is not None and is_helios_path(path):
        return _helios_wsgi(environ, start_response)
    return flask_app.wsgi_app(environ, start_response)


# Alias por si alguien apunta gunicorn a wsgi:app
app = flask_app
