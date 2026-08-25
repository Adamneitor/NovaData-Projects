"""Motor de evaluación de reglas de transición basadas en datos adicionales.

Soporta número, texto, booleano y lista; condiciones combinadas AND/OR;
prioridad y fallback (regla default).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from app.services.dato_formato import (
    CODIGO_BOOLEANO,
    CODIGO_LISTA,
    CODIGO_MONEDA,
    CODIGO_MONEDA_DECIMAL,
    CODIGO_NUMERO,
    CODIGO_NUMERO_DECIMAL,
    CODIGO_TEXTO,
    tipo_codigo,
)

# Operadores canónicos por familia de tipo
OPS_NUMERO = (">", "<", ">=", "<=", "==", "!=", "between")
OPS_TEXTO = ("==", "!=", "contains", "startswith", "endswith")
OPS_BOOL = ("==", "!=")

_ALIAS_OP = {
    "=": "==",
    "equals": "==",
    "eq": "==",
    "ne": "!=",
    "<>": "!=",
    "gt": ">",
    "lt": "<",
    "gte": ">=",
    "lte": "<=",
    "contiene": "contains",
    "startsWith": "startswith",
    "endsWith": "endswith",
    "empieza": "startswith",
    "termina": "endswith",
}

_TRUE = {"si", "sí", "true", "1", "yes", "s", "verdadero"}
_FALSE = {"no", "false", "0", "n", "falso"}


def normalizar_operador(op: str | None) -> str:
    raw = str(op or "").strip()
    return _ALIAS_OP.get(raw, raw.lower() if raw.lower() in ("contains", "startswith", "endswith", "between") else raw)


def familia_tipo(codigo: str) -> str:
    c = (codigo or "").lower()
    if c in (CODIGO_NUMERO, CODIGO_NUMERO_DECIMAL, CODIGO_MONEDA, CODIGO_MONEDA_DECIMAL):
        return "numero"
    if c == CODIGO_BOOLEANO:
        return "booleano"
    if c in (CODIGO_TEXTO, CODIGO_LISTA) or c == "telefono" or c == "fecha":
        return "texto"
    return "texto"


def operadores_para_codigo(codigo: str) -> list[str]:
    fam = familia_tipo(codigo)
    if fam == "numero":
        return list(OPS_NUMERO)
    if fam == "booleano":
        return list(OPS_BOOL)
    return list(OPS_TEXTO)


def operador_valido_para_codigo(operador: str, codigo: str) -> bool:
    return normalizar_operador(operador) in operadores_para_codigo(codigo)


def _to_decimal(raw: Any) -> Decimal | None:
    if raw is None or raw == "":
        return None
    s = str(raw).strip().replace("$", "").replace(",", "").replace(" ", "")
    if not s:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _to_bool(raw: Any) -> bool | None:
    if raw is None or raw == "":
        return None
    s = str(raw).strip().lower()
    if s in _TRUE:
        return True
    if s in _FALSE:
        return False
    return None


def _to_text(raw: Any) -> str:
    return "" if raw is None else str(raw).strip()


def evaluar_condicion(
    *,
    codigo: str,
    operador: str,
    valor_campo: Any,
    valor_esperado: Any,
    valor_hasta: Any = None,
) -> bool:
    """Evalúa una condición atómica según el tipo del dato."""
    op = normalizar_operador(operador)
    fam = familia_tipo(codigo)
    if not operador_valido_para_codigo(op, codigo):
        return False

    if fam == "numero":
        left = _to_decimal(valor_campo)
        right = _to_decimal(valor_esperado)
        if op == "between":
            hi = _to_decimal(valor_hasta)
            if left is None or right is None or hi is None:
                return False
            lo, hi2 = (right, hi) if right <= hi else (hi, right)
            return lo <= left <= hi2
        if left is None or right is None:
            return False
        if op == ">":
            return left > right
        if op == "<":
            return left < right
        if op == ">=":
            return left >= right
        if op == "<=":
            return left <= right
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        return False

    if fam == "booleano":
        left = _to_bool(valor_campo)
        right = _to_bool(valor_esperado)
        if left is None or right is None:
            return False
        if op == "==":
            return left is right
        if op == "!=":
            return left is not right
        return False

    # texto / lista / fecha / teléfono
    left = _to_text(valor_campo)
    right = _to_text(valor_esperado)
    llow, rlow = left.lower(), right.lower()
    if op == "==":
        return llow == rlow
    if op == "!=":
        return llow != rlow
    if op == "contains":
        return rlow in llow if right else False
    if op == "startswith":
        return llow.startswith(rlow) if right else False
    if op == "endswith":
        return llow.endswith(rlow) if right else False
    return False


def cumple_regla(regla: Any, valores: dict[int, Any], meta_por_dato: dict[int, dict] | None = None) -> bool:
    """True si la regla (AND/OR sobre sus condiciones) se cumple."""
    conds = list(getattr(regla, "condiciones", None) or [])
    if getattr(regla, "es_default", False) and not conds:
        return True
    if not conds:
        return False

    logica = str(getattr(regla, "logica", None) or "AND").strip().upper()
    results: list[bool] = []
    for c in conds:
        dato_id = int(c.dato_id)
        meta = (meta_por_dato or {}).get(dato_id) or {}
        codigo = meta.get("codigo")
        if not codigo:
            dato = getattr(c, "dato", None)
            codigo = tipo_codigo(getattr(dato, "tipo_dato", None) if dato else None)
        results.append(
            evaluar_condicion(
                codigo=codigo or CODIGO_TEXTO,
                operador=c.operador,
                valor_campo=valores.get(dato_id),
                valor_esperado=c.valor,
                valor_hasta=getattr(c, "valor_hasta", None),
            )
        )

    if logica == "OR":
        return any(results)
    return all(results)


def evaluar_reglas_datos(
    reglas: list[Any],
    valores: dict[int, Any],
    meta_por_dato: dict[int, dict] | None = None,
) -> Any | None:
    """Primera regla no-default que cumple (por prioridad); si ninguna, la default."""
    ordered = sorted(
        list(reglas or []),
        key=lambda r: (
            bool(getattr(r, "es_default", False)),
            int(getattr(r, "prioridad", None) or 999),
            int(getattr(r, "id", None) or 0),
        ),
    )
    for regla in ordered:
        if getattr(regla, "es_default", False):
            continue
        if cumple_regla(regla, valores, meta_por_dato):
            return regla
    for regla in ordered:
        if getattr(regla, "es_default", False):
            return regla
    return None


def _label_op(op: str) -> str:
    op = normalizar_operador(op)
    return {
        ">": ">",
        "<": "<",
        ">=": "≥",
        "<=": "≤",
        "==": "es",
        "!=": "no es",
        "contains": "contiene",
        "startswith": "empieza con",
        "endswith": "termina con",
        "between": "está entre",
    }.get(op, op)


def preview_condicion(cond: dict[str, Any], nombre_campo: str | None = None) -> str:
    campo = nombre_campo or cond.get("campo") or cond.get("field") or f"dato #{cond.get('dato_id', '?')}"
    op = normalizar_operador(cond.get("operador") or cond.get("operator"))
    val = cond.get("valor") if cond.get("valor") is not None else cond.get("value")
    hasta = cond.get("valor_hasta") if cond.get("valor_hasta") is not None else cond.get("value_to")
    if op == "between":
        return f"{campo} {_label_op(op)} {val} y {hasta}"
    return f"{campo} {_label_op(op)} {val}"


def preview_regla(
    regla: dict[str, Any] | Any,
    nombres: dict[int, str] | None = None,
) -> str:
    """Lenguaje natural: 'Si monto > 1000 y aprobado es true…'."""
    if not isinstance(regla, dict):
        logica = getattr(regla, "logica", "AND")
        es_default = bool(getattr(regla, "es_default", False))
        conds = [
            {
                "dato_id": c.dato_id,
                "operador": c.operador,
                "valor": c.valor,
                "valor_hasta": c.valor_hasta,
            }
            for c in (getattr(regla, "condiciones", None) or [])
        ]
        nombre = getattr(regla, "nombre", None)
    else:
        logica = regla.get("logica") or regla.get("logic") or "AND"
        es_default = bool(regla.get("es_default") or regla.get("is_default"))
        conds = regla.get("condiciones") or regla.get("conditions") or []
        nombre = regla.get("nombre")

    if es_default and not conds:
        return (nombre or "Regla") + " · por defecto (si ninguna otra aplica)"

    parts = []
    for c in conds:
        did = c.get("dato_id") if isinstance(c, dict) else None
        nom = (nombres or {}).get(int(did)) if did is not None else None
        if isinstance(c, dict):
            parts.append(preview_condicion(c, nom))
        else:
            parts.append(
                preview_condicion(
                    {
                        "dato_id": c.dato_id,
                        "operador": c.operador,
                        "valor": c.valor,
                        "valor_hasta": c.valor_hasta,
                    },
                    (nombres or {}).get(int(c.dato_id)),
                )
            )

    if not parts:
        return nombre or "Sin condiciones"
    join = " y " if str(logica).upper() == "AND" else " o "
    cuerpo = join.join(parts)
    pref = f"{nombre}: " if nombre else ""
    return f"{pref}Si {cuerpo}"


def validar_regla_config(regla: dict[str, Any], catalogo_datos: list[dict] | None = None) -> list[str]:
    """Validación en tiempo de configuración. Devuelve lista de errores."""
    errores: list[str] = []
    dest = regla.get("estado_destino_key") or regla.get("estado_destino_id")
    if not dest:
        errores.append("Debe indicar un estado destino.")
    logica = str(regla.get("logica") or "AND").upper()
    if logica not in ("AND", "OR"):
        errores.append("La lógica debe ser AND u OR.")
    by_id = {int(d["id"]): d for d in (catalogo_datos or []) if d.get("id") is not None}
    conds = regla.get("condiciones") or []
    if not regla.get("es_default") and not conds:
        errores.append("Una regla no default necesita al menos una condición.")
    for i, c in enumerate(conds, start=1):
        did = c.get("dato_id")
        if did in (None, "", 0, "0"):
            errores.append(f"Condición {i}: seleccione un campo.")
            continue
        meta = by_id.get(int(did))
        codigo = (meta or {}).get("codigo") or CODIGO_TEXTO
        op = normalizar_operador(c.get("operador"))
        if not operador_valido_para_codigo(op, codigo):
            errores.append(f"Condición {i}: operador «{op}» no válido para tipo {codigo}.")
        if op == "between" and (c.get("valor_hasta") in (None, "")):
            errores.append(f"Condición {i}: between requiere valor hasta.")
        if op != "between" and c.get("valor") in (None, "") and familia_tipo(codigo) != "booleano":
            # booleano puede ser "false" / vacío raro; exigimos valor
            if familia_tipo(codigo) == "booleano" and c.get("valor") not in ("Si", "No", "true", "false", "0", "1", True, False):
                if c.get("valor") in (None, ""):
                    errores.append(f"Condición {i}: indique Sí/No.")
            elif familia_tipo(codigo) != "booleano":
                errores.append(f"Condición {i}: indique un valor.")
    return errores
