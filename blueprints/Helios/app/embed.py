"""Modo embed: Helios sin chrome propio, dentro del shell NOVA."""
from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

EMBED_COOKIE = "nova_helios_embed"


def is_embed_request(request: Request) -> bool:
    if request.query_params.get("embed") == "1":
        return True
    return request.cookies.get(EMBED_COOKIE) == "1"


def with_embed_param(url: str) -> str:
    if not url or not url.startswith("/") or url.startswith("//"):
        return url
    parts = urlsplit(url)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    if q.get("embed") == "1":
        return url
    q["embed"] = "1"
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))


class EmbedMiddleware(BaseHTTPMiddleware):
    """Propaga embed=1 en redirects y expone request.state.embed."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        embed = is_embed_request(request)
        request.state.embed = embed
        response = await call_next(request)
        if embed and 300 <= response.status_code < 400:
            loc = response.headers.get("location")
            if loc and loc.startswith("/") and not loc.startswith("//"):
                path_only = loc.split("?", 1)[0]
                if path_only.startswith("/login") or path_only.startswith("/logout"):
                    return response
                new_loc = with_embed_param(loc)
                if new_loc != loc:
                    response.headers["location"] = new_loc
        return response
