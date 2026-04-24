"""
Rutas del blueprint de Buró de Crédito.

Todas las vistas se apoyan en datos de ejemplo (mock_data.py). No hay
acceso a bases de datos, web services ni servicios externos.
"""
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from functools import wraps

from flask import Blueprint, redirect, render_template, request, session, url_for

from .mock_data import listado_demo, obtener_cliente


buro_bp = Blueprint(
    "buro_credito",
    __name__,
    url_prefix="/module/buro-credito",
    template_folder="templates",
    static_folder="static",
    static_url_path="/static/buro_credito",
)


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return wrapper


@buro_bp.app_template_filter("moneda_sola")
def moneda_sola(valor):
    """Formatea un número como `1,234.56`. Seguro ante None/strings."""
    try:
        return f"{float(valor):,.2f}"
    except (TypeError, ValueError):
        return "0.00"


@buro_bp.app_template_filter("badge_info")
def badge_info(estatus):
    """Devuelve (clase CSS, icono) para un estatus de cuenta."""
    if not estatus:
        return ("estatus-default", "ℹ")
    estatus = str(estatus).upper()
    mapa = {
        "CREDITO_ABIERTO": ("estatus-abierto", "↗"),
        "CICLO_1": ("estatus-ciclo-1", "⚠"),
        "CICLO_2": ("estatus-ciclo-2", "⚠"),
        "CREDITO_CASTIGADO": ("estatus-malo", "✕"),
        "CREDITO_EN_LEGAL": ("estatus-malo", "✕"),
        "SEVERO": ("estatus-malo", "✕"),
        "ACUERDO_DE_PAGO": ("estatus-acuerdo", "▣"),
        "CREDITO_CERRADO": ("estatus-cerrado", "▢"),
    }
    return mapa.get(estatus, ("estatus-default", "ℹ"))


def _agrupar_resumen(cuentas):
    """Agrupa montos por (tipo producto, moneda, estado)."""
    resumen = defaultdict(
        lambda: defaultdict(
            lambda: {
                "Cantidad": 0,
                "Monto_Adeudado": Decimal(0),
                "Monto_Atraso": Decimal(0),
                "Cuotas": Decimal(0),
            }
        )
    )

    mapa_estatus = {
        "ACUERDO_DE_PAGO": "Acuerdo",
        "CICLO_1": "Atraso 30",
        "CICLO_2": "Atraso 60",
        "CREDITO_ABIERTO": "Normal",
        "CREDITO_CASTIGADO": "Castigo",
        "CREDITO_CERRADO": "Cerradas",
        "CREDITO_EN_LEGAL": "Legal",
        "SEVERO": "Atraso 90+",
    }

    for cuenta in cuentas:
        banco = cuenta.get("Banco") or ""
        tipo = "Tarjetas" if "TCR" in banco else "Prestamos"
        moneda = cuenta.get("Moneda") or "DO"
        estado = mapa_estatus.get(cuenta.get("EstatusEstandarizado"), "N/A")

        bucket = resumen[(tipo, moneda)][estado]
        bucket["Cantidad"] += 1
        bucket["Monto_Adeudado"] += Decimal(str(cuenta.get("Monto_Adeudado") or 0))
        bucket["Monto_Atraso"] += Decimal(str(cuenta.get("Atraso_Total") or 0))
        bucket["Cuotas"] += Decimal(str(cuenta.get("Pago_Cuota") or 0))

    return resumen


@buro_bp.route("/")
@login_required
def formulario():
    """Formulario de consulta del reporte."""
    return render_template(
        "buro_credito/formulario.html",
        demo_cedulas=listado_demo(),
    )


@buro_bp.route("/reporte", methods=["POST"])
@login_required
def generar_reporte_post():
    cedula = request.form.get("cedula", "")
    return _render_reporte(cedula)


@buro_bp.route("/reporte/<cedula>")
@login_required
def generar_reporte_get(cedula):
    return _render_reporte(cedula)


def _render_reporte(cedula_raw: str):
    cliente = obtener_cliente(cedula_raw)

    if not cliente:
        return render_template(
            "buro_credito/formulario.html",
            demo_cedulas=listado_demo(),
            error=(
                "No se encontró información crediticia para esa cédula. "
                "Verifica el formato o selecciona una consulta reciente."
            ),
            intento=cedula_raw,
        )

    cuentas = cliente["cuentas"]
    return render_template(
        "buro_credito/reporte.html",
        datos=cliente["datos"],
        cuentas=cuentas,
        resumen=_agrupar_resumen(cuentas),
        leads=cliente["leads"],
        fecha_generacion=datetime.now().strftime("%d/%m/%Y %H:%M"),
        now=datetime.now(),
    )
