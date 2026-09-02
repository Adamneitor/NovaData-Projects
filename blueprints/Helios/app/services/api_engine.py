"""Ejecucion de API calls configurados y evaluacion de reglas de direccionamiento."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session, selectinload

from app.models import (
    ApiCall,
    ApiParametro,
    ApiRegla,
    Caso,
    CasoApiLog,
    DatoComplementario,
    Estado,
    EstadoApiInput,
)
from app.services.api_mapeo import resolver_origen
from app.services.dato_formato import CODIGO_BOOLEANO, tipo_codigo

# Nova Projects root (…/blueprints/Helios/app/services → 4 niveles arriba)
_NOVA_ROOT = Path(__file__).resolve().parents[4]


@dataclass
class ResultadoApi:
    exito: bool
    http_status: int | None = None
    outputs: dict[str, object] = field(default_factory=dict)
    error: str | None = None
    request_json: str | None = None
    response_json: str | None = None


_TRUE_TOKENS = {"si", "sí", "true", "1", "yes", "s", "verdadero"}
_FALSE_TOKENS = {"no", "false", "0", "n", "falso"}


def _mapeo_input_por_parametro(estado: Estado | None) -> dict[int, EstadoApiInput]:
    if not estado:
        return {}
    return {m.parametro_id: m for m in (getattr(estado, "mapeos_input", None) or [])}


def _es_booleano_helios(raw: object) -> bool:
    if raw is None:
        return False
    return str(raw).strip().lower() in _TRUE_TOKENS | _FALSE_TOKENS


def booleano_a_api(raw: object) -> int | None:
    """Convierte Si/No (u equivalentes) a 1/0 para el request del API."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool):
        return 1 if raw else 0
    if isinstance(raw, (int, float)) and raw in (0, 1):
        return int(raw)
    s = str(raw).strip().lower()
    if s in _TRUE_TOKENS:
        return 1
    if s in _FALSE_TOKENS:
        return 0
    return None


def _codigo_dato(db: Session, dato_id: int | None) -> str | None:
    if not dato_id:
        return None
    dato = (
        db.query(DatoComplementario)
        .options(selectinload(DatoComplementario.tipo_dato))
        .filter(DatoComplementario.id == dato_id)
        .first()
    )
    if not dato:
        return None
    return tipo_codigo(dato.tipo_dato)


def _coerce_valor_api(raw: object, codigo: str | None) -> object | None:
    """Normaliza valores Helios al tipo esperado por APIs externos."""
    if raw is None:
        return None
    cod = (codigo or "").lower()

    if cod == CODIGO_BOOLEANO or (cod == "" and _es_booleano_helios(raw)):
        return booleano_a_api(raw)

    if cod in ("numero", "numero_decimal", "moneda", "moneda_decimal"):
        s = str(raw).strip().replace("$", "").replace(",", "").replace(" ", "")
        if not s:
            return None
        try:
            if cod in ("numero",) and "." not in s:
                return int(s)
            return float(s)
        except ValueError:
            return raw

    # Si/No sueltos (p.ej. valor fijo o dato mal tipado) → 1/0
    if _es_booleano_helios(raw):
        return booleano_a_api(raw)

    return raw


def _valor_parametro(
    param: ApiParametro,
    caso: Caso,
    db: Session,
    override: EstadoApiInput | None = None,
) -> object | None:
    """Resuelve el valor: override del estado si existe, si no el ApiParametro del catálogo.

    Booleanos Helios (Si/No) → 1/0; números/moneda → number JSON.
    """
    if override is not None:
        origen = override.origen
        valor_fijo = override.valor_fijo
        dato_id = override.dato_id
        campo_caso = override.campo_caso
    else:
        origen = param.origen
        valor_fijo = param.valor_fijo
        dato_id = param.dato_id
        campo_caso = param.campo_caso

    raw = resolver_origen(
        origen=origen,
        valor_fijo=valor_fijo,
        dato_id=dato_id,
        campo_caso=campo_caso,
        caso=caso,
        db=db,
    )
    if raw is None:
        return None

    origen_n = (origen or "fijo").strip().lower()
    codigo = _codigo_dato(db, dato_id) if origen_n == "dato" else None
    if origen_n == "fijo" and _es_booleano_helios(raw):
        codigo = CODIGO_BOOLEANO
    return _coerce_valor_api(raw, codigo)


def _extraer_json_path(data: object, path: str) -> object:
    """Extrae un valor de la respuesta usando ruta con puntos, ej. 'resultado.score'
    o 'items.0.valor'."""
    if not path:
        return None
    actual = data
    for parte in path.split("."):
        if isinstance(actual, dict):
            actual = actual.get(parte)
        elif isinstance(actual, list):
            try:
                actual = actual[int(parte)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return actual


def _extraer_output(data: object, out) -> object:
    """Extrae un ApiOutput con fallbacks si el JsonPath no coincide exactamente.

    Orden: json_path → último segmento del path → nombre del output.
    """
    path = (out.json_path or "").strip()
    valor = _extraer_json_path(data, path) if path else None
    if valor is None and path and "." in path:
        valor = _extraer_json_path(data, path.rsplit(".", 1)[-1])
    if valor is None and isinstance(data, dict):
        nombre = (out.nombre or "").strip()
        if nombre:
            valor = data.get(nombre)
            if valor is None:
                # match case-insensitive de clave
                low = {str(k).lower(): v for k, v in data.items()}
                valor = low.get(nombre.lower())
    return valor


def _formatear(valor: object, formato: str) -> object:
    if valor is None:
        return None
    if formato == "numero":
        try:
            return float(valor)
        except (TypeError, ValueError):
            return None
    if formato == "booleano":
        if isinstance(valor, bool):
            return valor
        if isinstance(valor, (int, float)):
            return bool(valor)
        return str(valor).strip().lower() in ("true", "1", "si", "sí", "yes")
    return str(valor)


def _demo_apis_module():
    """Carga demo_apis del root Nova sin depender del paquete Flask activo."""
    root = str(_NOVA_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    import demo_apis  # type: ignore

    return demo_apis


def _auth_bearer_ok(headers: dict) -> bool:
    auth = ""
    for k, v in (headers or {}).items():
        if str(k).lower() == "authorization":
            auth = str(v or "")
            break
    if not auth.lower().startswith("bearer "):
        return False
    return auth.split(" ", 1)[1].strip() == "test-token-123"


def _as_bool(raw: object) -> bool:
    if isinstance(raw, str):
        return raw.strip().lower() in ("1", "true", "si", "sí", "yes")
    return bool(raw)


def _try_demo_api_inprocess(
    url: str, body: dict, headers: dict
) -> tuple[int, dict] | None:
    """
    Si la URL apunta a /demo-api/* del mismo portal, ejecuta in-process.
    Evita que Helios se llame a sí mismo por HTTP (deadlock con gunicorn -w 1).
    """
    path = (urlparse(url).path or "").rstrip("/")
    if "/demo-api/" not in path:
        return None

    demo = _demo_apis_module()
    if not _auth_bearer_ok(headers):
        return 401, {"error": "No autorizado. Use Authorization: Bearer test-token-123"}

    if path.endswith("/demo-api/evaluacion"):
        try:
            salario = float(body.get("salario") or 0)
            tiempo = float(body.get("tiempo_laborando") or 0)
        except (TypeError, ValueError):
            return 400, {"error": "salario y tiempo_laborando deben ser numéricos"}
        cedula = demo._cedula_limpia(str(body.get("cedula") or ""))
        if salario <= 0 or not cedula:
            return 400, {"error": "Requiere salario > 0 y cedula"}
        return 200, demo.evaluar_motor(salario, _as_bool(body.get("es_asalariado", False)), tiempo, cedula)

    if path.endswith("/demo-api/buro/reporte"):
        cedula = demo._cedula_limpia(
            str(body.get("cedula") or body.get("identificacion") or "")
        )
        if len(cedula) < 5:
            return 400, {"error": "Requiere cedula válida"}
        return 200, demo.reporte_buro(cedula)

    return None


def ejecutar_api(
    api: ApiCall,
    caso: Caso,
    db: Session,
    estado_id: int | None = None,
    estado: Estado | None = None,
) -> ResultadoApi:
    headers = {}
    if api.headers_json:
        try:
            headers = json.loads(api.headers_json)
        except json.JSONDecodeError:
            pass

    url = api.url
    query: dict[str, str] = {}
    body: dict[str, object] = {}

    overrides = _mapeo_input_por_parametro(estado)
    for p in api.parametros:
        valor = _valor_parametro(p, caso, db, overrides.get(p.id))
        if p.ubicacion == "path":
            url = url.replace("{" + p.nombre + "}", "" if valor is None else str(valor))
        elif p.ubicacion == "query":
            if valor is not None:
                query[p.nombre] = str(valor)
        elif p.ubicacion == "header":
            if valor is not None:
                headers[p.nombre] = str(valor)
        else:  # body
            body[p.nombre] = valor

    resultado = ResultadoApi(exito=False)
    resultado.request_json = json.dumps(
        {"url": url, "metodo": api.metodo, "query": query, "body": body}, ensure_ascii=False
    )

    try:
        # Evita deadlock gunicorn (-w 1): no hacer HTTP al mismo proceso /demo-api/*
        inproc = _try_demo_api_inprocess(url, body, headers)
        if inproc is not None:
            status, data_or_err = inproc
            resultado.http_status = status
            if status >= 400:
                resultado.response_json = json.dumps(data_or_err, ensure_ascii=False)[:100_000]
                resultado.error = (
                    data_or_err.get("error")
                    if isinstance(data_or_err, dict)
                    else str(data_or_err)
                )
            else:
                data = data_or_err if isinstance(data_or_err, dict) else {}
                resultado.response_json = json.dumps(data, ensure_ascii=False)[:100_000]
                for out in api.outputs:
                    resultado.outputs[out.nombre] = _formatear(
                        _extraer_output(data, out), out.formato
                    )
                resultado.exito = True
        else:
            timeout = httpx.Timeout(
                connect=5.0,
                read=float(min(int(api.timeout_seg or 15), 20)),
                write=10.0,
                pool=5.0,
            )
            with httpx.Client(timeout=timeout) as client:
                kwargs: dict = {"params": query, "headers": headers}
                if api.metodo.upper() in ("POST", "PUT", "PATCH"):
                    kwargs["json"] = body
                respuesta = client.request(api.metodo.upper(), url, **kwargs)
            resultado.http_status = respuesta.status_code
            resultado.response_json = respuesta.text[:100_000]
            respuesta.raise_for_status()
            data = respuesta.json()
            for out in api.outputs:
                resultado.outputs[out.nombre] = _formatear(
                    _extraer_output(data, out), out.formato
                )
            resultado.exito = True
    except Exception as exc:  # noqa: BLE001 - se reporta el error al usuario
        resultado.error = str(exc)

    db.add(
        CasoApiLog(
            caso_id=caso.id,
            api_id=api.id,
            estado_id=estado_id or (estado.id if estado else None),
            request_json=resultado.request_json,
            response_json=resultado.response_json,
            http_status=resultado.http_status,
            exito=resultado.exito,
        )
    )
    db.flush()
    return resultado


def preview_request(
    api: ApiCall,
    caso: Caso,
    db: Session,
    estado: Estado | None = None,
) -> dict:
    """Construye el request que se enviaría (sin ejecutar HTTP). Útil para Test API."""
    headers: dict[str, str] = {}
    if api.headers_json:
        try:
            headers = json.loads(api.headers_json)
        except json.JSONDecodeError:
            pass
    url = api.url
    query: dict[str, str] = {}
    body: dict[str, object] = {}
    overrides = _mapeo_input_por_parametro(estado)
    for p in api.parametros:
        valor = _valor_parametro(p, caso, db, overrides.get(p.id))
        if p.ubicacion == "path":
            url = url.replace("{" + p.nombre + "}", "" if valor is None else str(valor))
        elif p.ubicacion == "query":
            if valor is not None:
                query[p.nombre] = str(valor)
        elif p.ubicacion == "header":
            if valor is not None:
                headers[p.nombre] = str(valor)
        else:
            body[p.nombre] = valor
    return {"url": url, "metodo": api.metodo, "headers": headers, "query": query, "body": body}


def _comparar(valor: object, operador: str, esperado: str) -> bool:
    if valor is None:
        return False
    if operador in (">", ">=", "<", "<="):
        try:
            v, e = float(valor), float(esperado)
        except (TypeError, ValueError):
            return False
        return {">": v > e, ">=": v >= e, "<": v < e, "<=": v <= e}[operador]
    v_str = str(valor).strip().lower()
    e_str = esperado.strip().lower()
    if operador == "=":
        return v_str == e_str
    if operador == "!=":
        return v_str != e_str
    if operador == "contiene":
        return e_str in v_str
    return False


def _condiciones_regla(regla: ApiRegla) -> list[tuple[str, str, str]]:
    """Lista (nombre_output, operador, valor) de la regla (condiciones o legado)."""
    conds = list(getattr(regla, "condiciones", None) or [])
    if conds:
        out = []
        for c in conds:
            nombre = c.output.nombre if getattr(c, "output", None) else None
            if not nombre:
                continue
            out.append((nombre, c.operador or "=", c.valor or ""))
        return out
    if regla.output_id and getattr(regla, "output", None):
        return [(regla.output.nombre, regla.operador or "=", regla.valor or "")]
    return []


def cumple_regla_api(regla: ApiRegla, outputs: dict[str, object]) -> bool:
    bits = [
        _comparar(outputs.get(nombre), op, valor)
        for nombre, op, valor in _condiciones_regla(regla)
    ]
    if not bits:
        return False
    logica = str(getattr(regla, "logica", None) or "AND").strip().upper()
    if logica == "OR":
        return any(bits)
    return all(bits)


def preview_regla_api(regla: ApiRegla) -> str:
    parts = []
    for nombre, op, valor in _condiciones_regla(regla):
        parts.append(f"{nombre} {op} {valor}")
    if not parts:
        return getattr(regla, "nombre", None) or "Regla API"
    join = " y " if str(getattr(regla, "logica", None) or "AND").upper() == "AND" else " o "
    pref = f"{regla.nombre}: " if getattr(regla, "nombre", None) else ""
    return f"{pref}Si {join.join(parts)}"


def evaluar_reglas(reglas: list[ApiRegla], outputs: dict[str, object]) -> ApiRegla | None:
    """Primera regla (por prioridad) cuyas condiciones AND/OR se cumplen."""
    for regla in sorted(reglas, key=lambda r: (int(getattr(r, "prioridad", None) or 999), int(getattr(r, "id", None) or 0))):
        if cumple_regla_api(regla, outputs):
            return regla
    return None


def outputs_desde_response(api: ApiCall, response_json: str | None) -> dict[str, object]:
    """Reconstruye outputs a partir del JSON de respuesta guardado en el log."""
    if not response_json:
        return {}
    try:
        data = json.loads(response_json)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, object] = {}
    for o in api.outputs or []:
        out[o.nombre] = _formatear(_extraer_output(data, o), o.formato)
    return out
