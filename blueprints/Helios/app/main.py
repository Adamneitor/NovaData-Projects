import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import SECRET_KEY
from app.csrf import CSRFMiddleware, get_csrf_token
from app.embed import EmbedMiddleware
from app.routers import admin, apis, auth, casos, catalogos, flujos, platform

from starlette.middleware.base import BaseHTTPMiddleware as _BaseMiddleware
from starlette.requests import Request as _Req
from starlette.responses import Response as _Resp


class _SecurityHeadersMiddleware(_BaseMiddleware):
    """Headers de seguridad para Helios (iframe same-origin)."""
    async def dispatch(self, request: _Req, call_next) -> _Resp:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        # Helios vive en iframe same-origin; no bloquear con X-Frame-Options DENY
        response.headers.setdefault("Content-Security-Policy", "frame-ancestors 'self'")
        return response


app = FastAPI(title="NOVA · Helios BPM")
# Cookie distinta de Flask (`session`) para no pisar el login del portal NOVA
_https = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))
app.add_middleware(_SecurityHeadersMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(EmbedMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="helios_session",
    max_age=8 * 3600,
    same_site="lax",
    https_only=_https,
)
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

import logging as _logging
import traceback as _tb
from starlette.responses import HTMLResponse as _HTML

_log = _logging.getLogger("helios")

@app.exception_handler(Exception)
async def _unhandled_exception(request: _Req, exc: Exception):
    """Loguea el traceback completo en consola para diagnóstico."""
    _log.error("500 en %s %s:\n%s", request.method, request.url.path, _tb.format_exc())
    return _HTML("<h2>Error interno del servidor</h2><pre>" + str(exc) + "</pre>", status_code=500)

app.include_router(platform.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(catalogos.router)
app.include_router(apis.router)
app.include_router(flujos.router)
app.include_router(casos.router)
