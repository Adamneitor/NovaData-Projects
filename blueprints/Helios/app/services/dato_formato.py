"""Formato y validación de datos complementarios.

Regla de oro: el valor persistido es siempre RAW (sin símbolos ni miles).
La visualización se deriva de tipo_dato + formato_visualizacion + decimales.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

# Códigos estables (independientes del nombre mostrado en BD)
CODIGO_TEXTO = "texto"
CODIGO_NUMERO = "numero"
CODIGO_NUMERO_DECIMAL = "numero_decimal"
CODIGO_TELEFONO = "telefono"
CODIGO_MONEDA = "moneda"
CODIGO_MONEDA_DECIMAL = "moneda_decimal"
CODIGO_FECHA = "fecha"
CODIGO_BOOLEANO = "booleano"
CODIGO_LISTA = "lista"

FORMATO_TELEFONO = "telefono"
FORMATO_NUMERO = "numero"
FORMATO_NUMERO_DECIMAL = "numero_decimal"
FORMATO_MONEDA = "moneda"
FORMATO_MONEDA_DECIMAL = "moneda_decimal"
FORMATO_TEXTO = "texto"

# Mapeo nombre BD (legacy + nuevos) → código
_NOMBRE_A_CODIGO: dict[str, str] = {
    "texto": CODIGO_TEXTO,
    "numero": CODIGO_NUMERO,
    "número": CODIGO_NUMERO,
    "numero decimal": CODIGO_NUMERO_DECIMAL,
    "número decimal": CODIGO_NUMERO_DECIMAL,
    "telefono": CODIGO_TELEFONO,
    "teléfono": CODIGO_TELEFONO,
    "moneda": CODIGO_MONEDA,
    "moneda decimal": CODIGO_MONEDA_DECIMAL,
    "fecha": CODIGO_FECHA,
    "booleano": CODIGO_BOOLEANO,
    "lista": CODIGO_LISTA,
}

DEFAULT_FORMATO: dict[str, str] = {
    CODIGO_TEXTO: FORMATO_TEXTO,
    CODIGO_NUMERO: FORMATO_NUMERO,
    CODIGO_NUMERO_DECIMAL: FORMATO_NUMERO_DECIMAL,
    CODIGO_TELEFONO: FORMATO_TELEFONO,
    CODIGO_MONEDA: FORMATO_MONEDA,
    CODIGO_MONEDA_DECIMAL: FORMATO_MONEDA_DECIMAL,
    CODIGO_FECHA: FORMATO_TEXTO,
    CODIGO_BOOLEANO: FORMATO_TEXTO,
    CODIGO_LISTA: FORMATO_TEXTO,
}

FORMATOS_POR_TIPO: dict[str, list[tuple[str, str]]] = {
    CODIGO_TEXTO: [(FORMATO_TEXTO, "Texto (sin formato)")],
    CODIGO_NUMERO: [(FORMATO_NUMERO, "Número entero (1,000)")],
    CODIGO_NUMERO_DECIMAL: [
        (FORMATO_NUMERO_DECIMAL, "Número decimal (1,000.50)"),
        (FORMATO_MONEDA_DECIMAL, "Moneda decimal ($1,000.50)"),
    ],
    CODIGO_TELEFONO: [(FORMATO_TELEFONO, "Teléfono (+1(000) 000-0000)")],
    CODIGO_MONEDA: [(FORMATO_MONEDA, "Moneda entera ($1,000)")],
    CODIGO_MONEDA_DECIMAL: [
        (FORMATO_MONEDA_DECIMAL, "Moneda decimal ($1,000.50)"),
        (FORMATO_NUMERO_DECIMAL, "Número decimal (1,000.50)"),
    ],
    CODIGO_FECHA: [(FORMATO_TEXTO, "Fecha (tal cual)")],
    CODIGO_BOOLEANO: [(FORMATO_TEXTO, "Booleano")],
    CODIGO_LISTA: [(FORMATO_TEXTO, "Lista")],
}

TIPOS_CON_DECIMALES = {CODIGO_NUMERO_DECIMAL, CODIGO_MONEDA_DECIMAL}
TIPOS_NUMERICOS = {
    CODIGO_NUMERO,
    CODIGO_NUMERO_DECIMAL,
    CODIGO_MONEDA,
    CODIGO_MONEDA_DECIMAL,
    CODIGO_TELEFONO,
}

# Catálogo semilla: (id, nombre, input_html, codigo)
TIPOS_DATO_CATALOGO: list[tuple[int, str, str, str]] = [
    (1, "Texto", "text", CODIGO_TEXTO),
    (2, "Numero", "number", CODIGO_NUMERO),
    (3, "Fecha", "date", CODIGO_FECHA),
    (4, "Booleano", "checkbox", CODIGO_BOOLEANO),
    (5, "Lista", "select", CODIGO_LISTA),
    (6, "Numero decimal", "text", CODIGO_NUMERO_DECIMAL),
    (7, "Telefono", "tel", CODIGO_TELEFONO),
    (8, "Moneda", "text", CODIGO_MONEDA),
    (9, "Moneda decimal", "text", CODIGO_MONEDA_DECIMAL),
]


def tipo_codigo(tipo_o_nombre: Any) -> str:
    """Obtiene el código estable desde un TipoDato, nombre o id."""
    if tipo_o_nombre is None:
        return CODIGO_TEXTO
    if hasattr(tipo_o_nombre, "codigo") and getattr(tipo_o_nombre, "codigo", None):
        return str(tipo_o_nombre.codigo).strip().lower()
    if hasattr(tipo_o_nombre, "nombre"):
        nombre = str(tipo_o_nombre.nombre or "").strip().lower()
    else:
        nombre = str(tipo_o_nombre).strip().lower()
    return _NOMBRE_A_CODIGO.get(nombre, CODIGO_TEXTO)


def resolve_formato(dato: Any = None, tipo_dato: Any = None, formato: str | None = None) -> str:
    """Resuelve formato de visualización con fallback legacy."""
    if formato and str(formato).strip():
        return str(formato).strip().lower()
    if dato is not None:
        fv = getattr(dato, "formato_visualizacion", None)
        if fv and str(fv).strip():
            return str(fv).strip().lower()
        tipo_dato = tipo_dato or getattr(dato, "tipo_dato", None)
    codigo = tipo_codigo(tipo_dato)
    return DEFAULT_FORMATO.get(codigo, FORMATO_TEXTO)


def resolve_decimales(dato: Any = None, decimales: int | None = None, tipo_dato: Any = None) -> int:
    if decimales is not None:
        return max(0, min(int(decimales), 8))
    if dato is not None:
        d = getattr(dato, "decimales", None)
        if d is not None:
            return max(0, min(int(d), 8))
        tipo_dato = tipo_dato or getattr(dato, "tipo_dato", None)
    codigo = tipo_codigo(tipo_dato if dato is None else (tipo_dato or getattr(dato, "tipo_dato", None)))
    return 2 if codigo in TIPOS_CON_DECIMALES else 0


def _solo_digitos(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _parse_decimal(raw: str) -> Decimal | None:
    """Normaliza entrada de usuario a Decimal. Acepta 1,000.50 / 1000.50 / $1.000,50."""
    s = (raw or "").strip()
    if not s:
        return None
    s = s.replace("$", "").replace(" ", "").replace("+", "")
    # Quitar paréntesis de teléfono residuales
    s = s.replace("(", "").replace(")", "").replace("-", "")
    if "," in s and "." in s:
        # Si la coma está después del punto → europeo 1.000,50
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        # Una sola coma: decimal europeo o miles ambiguo
        partes = s.split(",")
        if len(partes) == 2 and len(partes[1]) <= 2:
            s = partes[0].replace(".", "") + "." + partes[1]
        else:
            s = s.replace(",", "")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def parse_value(
    value: Any,
    tipo_dato: Any = None,
    *,
    dato: Any = None,
    decimales: int | None = None,
) -> str:
    """Convierte input de UI a valor RAW para persistir. Devuelve '' si vacío."""
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""

    codigo = tipo_codigo(tipo_dato if tipo_dato is not None else (getattr(dato, "tipo_dato", None) if dato else None))
    prec = resolve_decimales(dato=dato, decimales=decimales, tipo_dato=tipo_dato)

    if codigo == CODIGO_TELEFONO:
        return _solo_digitos(s)

    if codigo in TIPOS_NUMERICOS - {CODIGO_TELEFONO}:
        num = _parse_decimal(s)
        if num is None:
            return s  # dejar raw; validate_value lo rechazará
        if codigo in (CODIGO_NUMERO, CODIGO_MONEDA):
            return str(int(num.to_integral_value(rounding=ROUND_HALF_UP)))
        # decimal
        q = Decimal(10) ** -prec
        num = num.quantize(q, rounding=ROUND_HALF_UP)
        # Evitar notación científica; strip trailing zeros but keep at least one decimal place if needed
        normalized = format(num, "f")
        if "." in normalized:
            normalized = normalized.rstrip("0").rstrip(".")
            if prec > 0 and "." not in normalized and codigo in TIPOS_CON_DECIMALES:
                # Keep as integer string is fine for 1000.0 → 1000
                pass
        return normalized

    return s


def validate_value(
    value: Any,
    tipo_dato: Any = None,
    *,
    dato: Any = None,
    decimales: int | None = None,
    requerido: bool = False,
) -> str | None:
    """Devuelve mensaje de error o None si es válido."""
    raw = parse_value(value, tipo_dato, dato=dato, decimales=decimales)
    codigo = tipo_codigo(tipo_dato if tipo_dato is not None else (getattr(dato, "tipo_dato", None) if dato else None))

    if not raw:
        return "Este campo es obligatorio." if requerido else None

    if codigo == CODIGO_TELEFONO:
        if len(raw) < 10:
            return "Formato inválido. Ejemplo: +1(000) 000-0000 (mín. 10 dígitos)."
        if len(raw) > 15:
            return "El teléfono no puede superar 15 dígitos."
        return None

    if codigo in (CODIGO_NUMERO, CODIGO_MONEDA):
        # Rechazar decimales explícitos en la entrada del usuario
        ui = str(value or "")
        if re.search(r"[.,]\d", ui.replace(",", "")) or ("," in ui and "." in ui and ui.rfind(",") > ui.rfind(".")):
            # Heurística: si parece tener parte fraccionaria
            num = _parse_decimal(ui)
            if num is not None and num != num.to_integral_value(rounding=ROUND_HALF_UP):
                return "Solo se permiten números enteros (sin decimales)."
        if not re.fullmatch(r"-?\d+", raw):
            return "Solo se permiten números enteros (sin decimales)."
        return None

    if codigo in TIPOS_CON_DECIMALES:
        if not re.fullmatch(r"-?\d+(\.\d+)?", raw):
            return "Valor numérico inválido."
        if "." in raw:
            frac = raw.split(".", 1)[1]
            prec = resolve_decimales(dato=dato, decimales=decimales, tipo_dato=tipo_dato)
            if len(frac) > prec:
                return f"Máximo {prec} decimales permitidos."
        return None

    return None


def format_value(
    value: Any,
    tipo_dato: Any = None,
    formato_visualizacion: str | None = None,
    *,
    dato: Any = None,
    decimales: int | None = None,
    locale: str = "en_US",
) -> str:
    """Formatea un valor RAW para visualización. No altera el almacenamiento."""
    if value is None:
        return ""
    raw = str(value).strip()
    if raw == "":
        return ""

    formato = resolve_formato(dato=dato, tipo_dato=tipo_dato, formato=formato_visualizacion)
    prec = resolve_decimales(dato=dato, decimales=decimales, tipo_dato=tipo_dato)

    # Localización mínima: en_US → 1,000.50 ; es_DO/es → 1.000,50
    miles = ","
    decimal_sep = "."
    if locale.lower().startswith("es"):
        miles = "."
        decimal_sep = ","

    if formato == FORMATO_TELEFONO:
        digits = _solo_digitos(raw)
        if len(digits) == 11 and digits.startswith("1"):
            return f"+{digits[0]}({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        if len(digits) == 10:
            return f"({digits[0:3]}) {digits[3:6]}-{digits[6:]}"
        if len(digits) > 4:
            return f"+{digits}"
        return digits

    if formato in (
        FORMATO_NUMERO,
        FORMATO_NUMERO_DECIMAL,
        FORMATO_MONEDA,
        FORMATO_MONEDA_DECIMAL,
    ):
        num = _parse_decimal(raw)
        if num is None:
            return raw
        entero = formato in (FORMATO_NUMERO, FORMATO_MONEDA)
        if entero:
            num = num.to_integral_value(rounding=ROUND_HALF_UP)
            prec_use = 0
        else:
            q = Decimal(10) ** -prec
            num = num.quantize(q, rounding=ROUND_HALF_UP)
            prec_use = prec

        sign = "-" if num < 0 else ""
        num = abs(num)
        as_str = f"{num:.{prec_use}f}" if prec_use else f"{int(num)}"
        if prec_use:
            whole, frac = as_str.split(".")
        else:
            whole, frac = as_str, ""
        # miles
        parts = []
        while whole:
            parts.insert(0, whole[-3:])
            whole = whole[:-3]
        whole_fmt = miles.join(parts) if parts else "0"
        body = f"{whole_fmt}{decimal_sep}{frac}" if frac else whole_fmt
        if formato in (FORMATO_MONEDA, FORMATO_MONEDA_DECIMAL):
            return f"{sign}${body}"
        return f"{sign}{body}"

    return raw


def format_dato(dato: Any, value: Any, locale: str = "en_US") -> str:
    """Atajo Jinja: formatea usando la config del DatoComplementario."""
    return format_value(
        value,
        tipo_dato=getattr(dato, "tipo_dato", None) if dato else None,
        formato_visualizacion=getattr(dato, "formato_visualizacion", None) if dato else None,
        dato=dato,
        locale=locale,
    )


def input_attrs_for_dato(dato: Any) -> dict[str, str]:
    """Atributos HTML data-* para inputs con máscara."""
    codigo = tipo_codigo(getattr(dato, "tipo_dato", None) if dato else None)
    formato = resolve_formato(dato=dato)
    prec = resolve_decimales(dato=dato)
    return {
        "data-dato-codigo": codigo,
        "data-dato-formato": formato,
        "data-dato-decimales": str(prec),
        "inputmode": "tel" if codigo == CODIGO_TELEFONO else ("decimal" if codigo in TIPOS_NUMERICOS else "text"),
    }
