from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.embed import is_embed_request
from app.services.dato_formato import (
    FORMATOS_POR_TIPO,
    format_dato,
    format_value,
    input_attrs_for_dato,
    resolve_decimales,
    resolve_formato,
    tipo_codigo,
)

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def flash(request: Request, mensaje: str, categoria: str = "success") -> None:
    request.session.setdefault("_flashes", []).append({"m": mensaje, "c": categoria})


def get_flashes(request: Request) -> list[dict]:
    return request.session.pop("_flashes", [])


templates.env.globals["get_flashes"] = get_flashes
templates.env.globals["format_dato"] = format_dato
templates.env.globals["format_value"] = format_value
templates.env.globals["tipo_codigo"] = tipo_codigo
templates.env.globals["resolve_formato"] = resolve_formato
templates.env.globals["resolve_decimales"] = resolve_decimales
templates.env.globals["input_attrs_for_dato"] = input_attrs_for_dato
templates.env.globals["FORMATOS_POR_TIPO"] = FORMATOS_POR_TIPO
templates.env.globals["is_embed"] = is_embed_request
templates.env.filters["format_dato"] = lambda value, dato, locale="en_US": format_dato(dato, value, locale=locale)


def render(request: Request, template: str, context: dict | None = None):
    ctx = dict(context or {})
    ctx.setdefault("embed", is_embed_request(request))
    return templates.TemplateResponse(request, template, ctx)
