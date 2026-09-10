"""
Protección CSRF para Helios (FastAPI/Starlette).
Token por sesión, validado en POST/PUT/DELETE de formularios.
Peticiones JSON con header X-Requested-With se consideran seguras (SameSite Lax).
"""
from __future__ import annotations

import re
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

CSRF_TOKEN_KEY = "_csrf_token"
CSRF_HEADER = "x-csrf-token"
CSRF_FORM_FIELD = "csrf_token"
_UNSAFE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
_EXEMPT_PREFIXES = ("/casos/api/", "/apis/api/", "/flujos/api/", "/catalogos/api/")

_MULTIPART_TOKEN_RE = re.compile(
    rb'name="csrf_token"\r?\n\r?\n([^\r\n-]+)', re.DOTALL
)


def get_csrf_token(request: Request) -> str:
    """Obtiene o genera el token CSRF de la sesión."""
    token = request.session.get(CSRF_TOKEN_KEY)
    if not token:
        token = secrets.token_hex(32)
        request.session[CSRF_TOKEN_KEY] = token
    return token


def _is_json_xhr(request: Request) -> bool:
    ct = request.headers.get("content-type", "")
    xhr = request.headers.get("x-requested-with", "")
    return "application/json" in ct or xhr.lower() == "xmlhttprequest"


def _is_exempt(path: str) -> bool:
    return any(path.startswith(p) for p in _EXEMPT_PREFIXES)


def _extract_token_from_body(body: bytes, content_type: str) -> str:
    """Extrae el csrf_token del body según el content-type."""
    if not body:
        return ""
    if "multipart/form-data" in content_type:
        m = _MULTIPART_TOKEN_RE.search(body)
        return m.group(1).decode("utf-8", errors="replace").strip() if m else ""
    if b"csrf_token=" in body:
        from urllib.parse import parse_qs
        parsed = parse_qs(body.decode("utf-8", errors="replace"))
        return (parsed.get("csrf_token") or [""])[0]
    return ""


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method not in _UNSAFE_METHODS:
            return await call_next(request)

        if _is_json_xhr(request):
            return await call_next(request)

        if _is_exempt(request.url.path):
            return await call_next(request)

        expected = request.session.get(CSRF_TOKEN_KEY)
        if not expected:
            get_csrf_token(request)
            return await call_next(request)

        submitted = request.headers.get(CSRF_HEADER) or ""

        if not submitted:
            try:
                body = await request.body()
                ct = request.headers.get("content-type", "")
                submitted = _extract_token_from_body(body, ct)
            except Exception:
                submitted = ""

        if not submitted or not secrets.compare_digest(submitted, expected):
            return Response(
                "Token CSRF inválido o ausente. Recargue la página e intente de nuevo.",
                status_code=403,
            )

        return await call_next(request)
