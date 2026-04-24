"""
Datos de ejemplo para el blueprint de Buró de Crédito.

Todo el contenido es ficticio y se utiliza únicamente para demostrar la
interfaz del módulo. No se conecta a ninguna base de datos ni servicio
externo. Los nombres, cédulas y montos son completamente inventados.
"""
from datetime import datetime, timedelta


def _fecha(delta_dias: int) -> str:
    return (datetime.now() + timedelta(days=delta_dias)).strftime("%Y%m%d")


MOCK_CLIENTES = {
    "00112345678": {
        "datos": {
            "Nombre": "Ana María",
            "Apellidos": "Pérez Rosario",
            "Cedula": "001-1234567-8",
            "Fecha_De_Nacimiento": "19880514",
            "Edad": 37,
            "Xcore": 782,
            "ChanceRiesgoFavor": "72%",
            "ChanceRiesgoEnContra": "28%",
            "Mes_Evaluacion": "202411",
            "Eic_Min": 320000.00,
            "Eic_Max": 780000.00,
            "Fecha_Vencimiento": _fecha(30),
            "Foto_Cliente": None,
        },
        "cuentas": [
            {
                "Banco": "Entidad Demo A — TCR / CREDITO_ABIERTO",
                "Fecha_Apertura": "20210318",
                "Mes_Consolidado": "202411",
                "Fecha_Ult_Transaccion": "20241105",
                "Moneda": "DO",
                "Credito_Aprobado": 150000.00,
                "Monto_Adeudado": 84250.75,
                "Pago_Cuota": 8500.00,
                "Atraso_Total": 0,
                "Historial_Pago": list("000000000000000000000000"),
                "EstatusEstandarizado": "CREDITO_ABIERTO",
            },
            {
                "Banco": "Entidad Demo B — PR / CREDITO_ABIERTO",
                "Fecha_Apertura": "20220701",
                "Mes_Consolidado": "202411",
                "Fecha_Ult_Transaccion": "20241102",
                "Moneda": "DO",
                "Credito_Aprobado": 500000.00,
                "Monto_Adeudado": 312580.00,
                "Pago_Cuota": 14200.00,
                "Atraso_Total": 0,
                "Historial_Pago": list("000000000000000000000000"),
                "EstatusEstandarizado": "CREDITO_ABIERTO",
            },
            {
                "Banco": "Entidad Demo C — TCR / CREDITO_CERRADO",
                "Fecha_Apertura": "20190205",
                "Mes_Consolidado": "202411",
                "Fecha_Ult_Transaccion": "20230615",
                "Moneda": "US",
                "Credito_Aprobado": 2500.00,
                "Monto_Adeudado": 0,
                "Pago_Cuota": 0,
                "Atraso_Total": 0,
                "Historial_Pago": list("00000000000000000000----"),
                "EstatusEstandarizado": "CREDITO_CERRADO",
            },
        ],
        "leads": [
            {
                "tipo": "Limite TC",
                "es_tc": True,
                "orden": 1,
                "lineas": [
                    {
                        "Tipo_Lead": "Limite TC",
                        "Codigo_Iso_3_Char": "DOP",
                        "Monto": 185000.00,
                        "Cuota": 0,
                        "Plazo": None,
                        "Tasa": None,
                        "Dictamen": "Pre-aprobado",
                        "Producto_Sugerido": "Clásica Oro",
                    },
                    {
                        "Tipo_Lead": "Limite TC",
                        "Codigo_Iso_3_Char": "USD",
                        "Monto": 3500.00,
                        "Cuota": 0,
                        "Plazo": None,
                        "Tasa": None,
                        "Dictamen": "Pre-aprobado",
                    },
                ],
            },
            {
                "tipo": "Préstamo Consumo",
                "es_tc": False,
                "orden": 2,
                "lineas": [
                    {
                        "Tipo_Lead": "Préstamo Consumo",
                        "Codigo_Iso_3_Char": "DOP",
                        "Monto": 450000.00,
                        "Plazo": 48,
                        "Tasa": 19.50,
                        "Cuota": 13750.00,
                        "Dictamen": "Pre-aprobado",
                        "Producto_Sugerido": None,
                    }
                ],
            },
        ],
    },
    "00298765432": {
        "datos": {
            "Nombre": "Carlos",
            "Apellidos": "Díaz Martínez",
            "Cedula": "002-9876543-2",
            "Fecha_De_Nacimiento": "19761122",
            "Edad": 48,
            "Xcore": 615,
            "ChanceRiesgoFavor": "52%",
            "ChanceRiesgoEnContra": "48%",
            "Mes_Evaluacion": "202411",
            "Eic_Min": 120000.00,
            "Eic_Max": 280000.00,
            "Fecha_Vencimiento": _fecha(-5),
            "Foto_Cliente": None,
        },
        "cuentas": [
            {
                "Banco": "Entidad Demo A — TCR / CICLO_1",
                "Fecha_Apertura": "20200412",
                "Mes_Consolidado": "202411",
                "Fecha_Ult_Transaccion": "20241001",
                "Moneda": "DO",
                "Credito_Aprobado": 80000.00,
                "Monto_Adeudado": 78420.00,
                "Pago_Cuota": 4500.00,
                "Atraso_Total": 4500.00,
                "Historial_Pago": list("0000000000000000000000001"),
                "EstatusEstandarizado": "CICLO_1",
            },
            {
                "Banco": "Entidad Demo D — PR / CREDITO_ABIERTO",
                "Fecha_Apertura": "20180816",
                "Mes_Consolidado": "202411",
                "Fecha_Ult_Transaccion": "20241101",
                "Moneda": "DO",
                "Credito_Aprobado": 300000.00,
                "Monto_Adeudado": 87500.00,
                "Pago_Cuota": 9800.00,
                "Atraso_Total": 0,
                "Historial_Pago": list("000000000000000000000000"),
                "EstatusEstandarizado": "CREDITO_ABIERTO",
            },
        ],
        "leads": [
            {
                "tipo": "Préstamo Consolidación",
                "es_tc": False,
                "orden": 3,
                "lineas": [
                    {
                        "Tipo_Lead": "Préstamo Consolidación",
                        "Codigo_Iso_3_Char": "DOP",
                        "Monto": 165000.00,
                        "Plazo": 36,
                        "Tasa": 22.00,
                        "Cuota": 6300.00,
                        "Dictamen": "Aprobado",
                        "Producto_Sugerido": None,
                    }
                ],
            }
        ],
    },
    "00355512399": {
        "datos": {
            "Nombre": "Luis Alberto",
            "Apellidos": "Gómez Herrera",
            "Cedula": "003-5551239-9",
            "Fecha_De_Nacimiento": "19920930",
            "Edad": 33,
            "Xcore": 540,
            "ChanceRiesgoFavor": "38%",
            "ChanceRiesgoEnContra": "62%",
            "Mes_Evaluacion": "202411",
            "Eic_Min": 80000.00,
            "Eic_Max": 150000.00,
            "Fecha_Vencimiento": _fecha(60),
            "Foto_Cliente": None,
        },
        "cuentas": [
            {
                "Banco": "Entidad Demo E — TCR / CICLO_2",
                "Fecha_Apertura": "20220210",
                "Mes_Consolidado": "202411",
                "Fecha_Ult_Transaccion": "20240920",
                "Moneda": "DO",
                "Credito_Aprobado": 50000.00,
                "Monto_Adeudado": 52180.00,
                "Pago_Cuota": 2800.00,
                "Atraso_Total": 5600.00,
                "Historial_Pago": list("000000000000000000000112"),
                "EstatusEstandarizado": "CICLO_2",
            },
            {
                "Banco": "Entidad Demo F — PR / CREDITO_CASTIGADO",
                "Fecha_Apertura": "20190620",
                "Mes_Consolidado": "202411",
                "Fecha_Ult_Transaccion": "20230210",
                "Moneda": "DO",
                "Credito_Aprobado": 120000.00,
                "Monto_Adeudado": 42350.00,
                "Pago_Cuota": 0,
                "Atraso_Total": 42350.00,
                "Historial_Pago": list("000001112233333------"),
                "EstatusEstandarizado": "CREDITO_CASTIGADO",
            },
        ],
        "leads": [],
    },
}


def cedula_limpia(raw: str) -> str:
    """Normaliza la cédula quitando cualquier carácter no numérico."""
    return "".join(c for c in (raw or "") if c.isdigit())


def obtener_cliente(cedula: str):
    """Devuelve la data del cliente mock o None si no existe."""
    return MOCK_CLIENTES.get(cedula_limpia(cedula))


def listado_demo():
    """Cédulas de ejemplo disponibles para el formulario."""
    return [
        (c, d["datos"]["Nombre"] + " " + d["datos"]["Apellidos"])
        for c, d in MOCK_CLIENTES.items()
    ]
