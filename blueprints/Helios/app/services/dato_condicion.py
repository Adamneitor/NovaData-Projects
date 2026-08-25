"""Evaluación de reglas condicionales entre datos adicionales de una etapa."""

from __future__ import annotations

from typing import Any

TRUE_VALUES = frozenset({"si", "sí", "true", "1", "yes", "s"})
FALSE_VALUES = frozenset({"no", "false", "0", "n"})


def valor_es_verdadero(valor: Any) -> bool:
    s = str(valor or "").strip().lower()
    if not s:
        return False
    return s in TRUE_VALUES


def condicion_cumplida(valor_controlador: Any, condicion: str | None = "true") -> bool:
    """La condición por defecto es que el booleano sea verdadero (Si/true)."""
    esperado = (condicion or "true").strip().lower()
    es_true = valor_es_verdadero(valor_controlador)
    if esperado in TRUE_VALUES or esperado in ("true", "si", "sí"):
        return es_true
    if esperado in FALSE_VALUES or esperado == "false":
        return not es_true
    # Comparación literal
    return str(valor_controlador or "").strip().lower() == esperado


def evaluar_campo(
    ed: Any,
    valores: dict[int, str],
) -> dict[str, Any]:
    """Estado runtime de un EtapaDato (o dict compatible).

    Retorna:
      enabled, required, condition_met, depends_on, controller_value
    """
    depende = getattr(ed, "depende_de_dato_id", None)
    if depende is None and isinstance(ed, dict):
        depende = ed.get("depende_de_dato_id") or ed.get("depends_on")

    obligatorio_base = bool(
        getattr(ed, "obligatorio", None)
        if not isinstance(ed, dict)
        else ed.get("obligatorio")
    )
    req_si = bool(
        getattr(ed, "requerido_si_cumple", None)
        if not isinstance(ed, dict)
        else ed.get("requerido_si_cumple", ed.get("required_when"))
    )
    dis_si_no = bool(
        getattr(ed, "deshabilitar_si_no_cumple", None)
        if not isinstance(ed, dict)
        else ed.get("deshabilitar_si_no_cumple", ed.get("disable_when_false"))
    )
    condicion = (
        getattr(ed, "condicion_valor", None)
        if not isinstance(ed, dict)
        else ed.get("condicion_valor", ed.get("condition"))
    ) or "true"

    if not depende:
        return {
            "enabled": True,
            "required": obligatorio_base,
            "condition_met": True,
            "depends_on": None,
            "controller_value": None,
        }

    ctrl_val = valores.get(int(depende), "")
    met = condicion_cumplida(ctrl_val, condicion)
    # Si disable_when_false: deshabilitar cuando NO se cumple
    enabled = True if met else (not dis_si_no)

    # required_when: obligatorio solo si condición cumplida y enabled
    # si no: obligatorio base aplica solo mientras enabled
    if req_si:
        required = bool(enabled and met)
    else:
        required = bool(enabled and obligatorio_base)

    return {
        "enabled": enabled,
        "required": required,
        "condition_met": met,
        "depends_on": int(depende),
        "controller_value": ctrl_val,
    }


def es_efectivamente_requerido(ed: Any, valores: dict[int, str]) -> bool:
    st = evaluar_campo(ed, valores)
    return bool(st["enabled"] and st["required"])


def serializar_regla(ed: Any) -> dict[str, Any]:
    depende = getattr(ed, "depende_de_dato_id", None)
    return {
        "depends_on": int(depende) if depende else None,
        "condition": (getattr(ed, "condicion_valor", None) or "true") if depende else None,
        "required_when": bool(getattr(ed, "requerido_si_cumple", False)) if depende else False,
        "disable_when_false": bool(getattr(ed, "deshabilitar_si_no_cumple", False)) if depende else False,
    }
