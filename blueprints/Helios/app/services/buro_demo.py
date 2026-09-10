"""Generador de reportes de buró crediticio ficticios para demo Helios.

Toda la data es 100 % ficticia. Nunca usa cédulas ni PII reales.
Los datos son determinísticos: la misma cédula siempre produce el mismo reporte.
"""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta
from typing import Any

# ───────────────────────────── Catálogos ficticios ─────────────────────────

_NOMBRES_M = [
    "Juan", "Carlos", "Pedro", "Miguel", "Rafael",
    "Luis", "José", "Andrés", "Fernando", "Ricardo",
    "Eduardo", "Alejandro", "Marcos", "Daniel", "Santiago",
]
_NOMBRES_F = [
    "María", "Ana", "Laura", "Carmen", "Lucía",
    "Rosa", "Isabel", "Paola", "Gabriela", "Sofía",
    "Elena", "Patricia", "Claudia", "Valeria", "Diana",
]
_APELLIDOS = [
    "Pérez", "García", "Rodríguez", "Martínez", "López",
    "Hernández", "Sánchez", "Ramírez", "Torres", "Díaz",
    "Reyes", "Morales", "Cruz", "Jiménez", "Castillo",
    "Bautista", "Rosario", "Méndez", "Vásquez", "Núñez",
]

_ENTIDADES = [
    "Banco Popular Dominicano",
    "Banreservas",
    "BHD León",
    "Scotiabank",
    "Banco Vimenca",
    "Asociación Popular de Ahorros y Préstamos",
    "Banco Santa Cruz",
    "Banco Caribe",
    "Asociación Cibao de Ahorros y Préstamos",
    "Banco BDI",
    "Banco Promerica",
    "Banco Ademi",
]

_PRODUCTOS = [
    ("TC Visa Gold", "TC"),
    ("TC Visa Clásica", "TC"),
    ("TC Mastercard", "TC"),
    ("TC Mastercard Gold", "TC"),
    ("PR Consumo", "PR"),
    ("PR Vehículo", "PR"),
    ("PR Hipotecario", "PR"),
    ("Línea de Crédito", "LC"),
]

_MARCAS_VEHICULOS = [
    ("Toyota", ["Corolla", "RAV4", "Hilux", "Yaris", "Camry"]),
    ("Honda", ["Civic", "CR-V", "Accord", "HR-V"]),
    ("Hyundai", ["Tucson", "Elantra", "Santa Fe", "Accent"]),
    ("Kia", ["Sportage", "Forte", "Seltos", "Sorento"]),
    ("Nissan", ["Sentra", "Pathfinder", "Kicks", "Frontier"]),
    ("Chevrolet", ["Spark", "Tracker", "Onix"]),
]

_COLORES_VEHICULO = [
    "Blanco", "Negro", "Gris", "Plateado", "Azul", "Rojo", "Verde",
]

_ACTIVIDADES = [
    "Gerente Comercial", "Contador Público", "Ingeniero Civil",
    "Médico General", "Abogado", "Administrador de Empresas",
    "Analista Financiero", "Profesor Universitario", "Arquitecto",
    "Consultor de TI", "Ejecutivo de Ventas", "Odontólogo",
]

_CALLES = [
    "Av. Winston Churchill", "Av. Abraham Lincoln", "Av. 27 de Febrero",
    "Av. Tiradentes", "Av. Máximo Gómez", "Calle El Conde",
    "Av. Sarasota", "Av. Luperón", "Av. Núñez de Cáceres",
    "Av. Independencia", "Calle Duarte", "Av. San Martín",
]

_SECTORES = [
    "Piantini", "Naco", "Evaristo Morales", "Gazcue", "Bella Vista",
    "Los Prados", "Arroyo Hondo", "Ensanche Quisqueya", "Mirador Sur",
    "La Julia", "Paraíso", "Renacimiento", "El Vergel", "Serrallés",
]

_MESES_CORTOS = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
]

_RELACIONES = ["Padre", "Madre", "Cónyuge", "Hermano/a", "Hijo/a"]

# ──────────────────────────── Utilidades internas ──────────────────────────


def _limpiar_cedula(raw: str | None) -> str:
    """Devuelve solo dígitos de la cédula."""
    return "".join(ch for ch in (raw or "") if ch.isdigit())


def _formatear_cedula(digitos: str) -> str:
    """Formatea a patrón 000-0000000-0 si tiene 11 dígitos."""
    d = digitos.ljust(11, "0")[:11]
    return f"{d[:3]}-{d[3:10]}-{d[10]}"


def _rng(cedula: str) -> random.Random:
    """Genera un RNG determinístico a partir del hash de la cédula."""
    seed = int(hashlib.sha256(cedula.encode("utf-8")).hexdigest()[:12], 16)
    return random.Random(seed)


def _mes_label(dt: datetime) -> str:
    """Ej: 'Ago 2026' o 'Ene·26' según formato requerido."""
    return f"{_MESES_CORTOS[dt.month - 1]}·{str(dt.year)[2:]}"


def _fecha_texto(dt: datetime) -> str:
    return dt.strftime("%Y/%m/%d")


# ────────────────────── Generador principal del reporte ────────────────────


def generar_reporte_buro_demo(cedula: str) -> dict[str, Any]:
    """Genera un reporte de buró crediticio completamente ficticio.

    Parámetros
    ----------
    cedula : str
        Cédula (puede incluir guiones; se limpian internamente).

    Retorna
    -------
    dict con la estructura del reporte Equifax adaptada a Helios.
    """
    key = _limpiar_cedula(cedula)
    rng = _rng(key)
    ahora = datetime.utcnow()

    # ── Perfil demográfico ──────────────────────────────────────────────
    sexo = rng.choice(["M", "F"])
    if sexo == "M":
        nombre = rng.choice(_NOMBRES_M)
    else:
        nombre = rng.choice(_NOMBRES_F)
    apellido1 = rng.choice(_APELLIDOS)
    apellido2 = rng.choice([a for a in _APELLIDOS if a != apellido1])
    apellidos = f"{apellido1} {apellido2}"
    nombre_completo = f"{nombre} {apellidos}"

    # Edad entre 23 y 68
    edad = rng.randint(23, 68)
    anio_nac = ahora.year - edad
    mes_nac = rng.randint(1, 12)
    dia_nac = rng.randint(1, 28)
    fecha_nac = f"{anio_nac}{mes_nac:02d}{dia_nac:02d}"

    # ── Perfil crediticio (score + banda) ──────────────────────────────
    # Distribución: 40 % buenos, 35 % medios, 25 % bajos
    roll = rng.random()
    if roll < 0.40:
        xcore = rng.randint(720, 950)
    elif roll < 0.75:
        xcore = rng.randint(580, 719)
    else:
        xcore = rng.randint(310, 579)

    if xcore >= 720:
        dictamen = "BUENO"
        chance_favor = rng.randint(75, 95)
    elif xcore >= 600:
        dictamen = "REGULAR"
        chance_favor = rng.randint(45, 74)
    else:
        dictamen = "ALTO RIESGO"
        chance_favor = rng.randint(10, 44)

    chance_contra = 100 - chance_favor

    # ── Capacidad económica ────────────────────────────────────────────
    if xcore >= 720:
        ingresos = float(rng.randint(55_000, 250_000))
    elif xcore >= 600:
        ingresos = float(rng.randint(25_000, 90_000))
    else:
        ingresos = float(rng.randint(12_000, 45_000))

    endeudamiento_pct = round(rng.uniform(15.0, 65.0), 1)
    comprometido = round(ingresos * endeudamiento_pct / 100, 2)
    disponible = round(ingresos - comprometido, 2)

    es_asalariado = rng.choices([1, 0], weights=[75, 25])[0]

    eic_min = round(ingresos * rng.uniform(0.15, 0.30), 2)
    eic_max = round(ingresos * rng.uniform(0.45, 0.80), 2)

    # ── Historial ──────────────────────────────────────────────────────
    historia_anios = rng.randint(2, 18)
    n_cuentas = rng.randint(2, 8)
    n_abiertas = rng.randint(1, min(n_cuentas, 6))
    n_cerradas = n_cuentas - n_abiertas

    # Uso de límite correlacionado al score
    if xcore >= 720:
        uso_limite = round(rng.uniform(5.0, 35.0), 1)
    elif xcore >= 600:
        uso_limite = round(rng.uniform(30.0, 65.0), 1)
    else:
        uso_limite = round(rng.uniform(55.0, 95.0), 1)

    # Atraso
    if xcore >= 700:
        atraso_monto = 0.0
    elif xcore >= 550:
        atraso_monto = round(rng.uniform(0, 15_000), 2)
    else:
        atraso_monto = round(rng.uniform(5_000, 80_000), 2)

    # ── Historial de Score (5–7 puntos bimestrales) ────────────────────
    n_puntos = rng.randint(5, 7)
    historial_score: list[dict[str, Any]] = []
    # Generar meses hacia atrás bimestralmente
    for i in range(n_puntos):
        meses_atras = (n_puntos - 1 - i) * 2
        dt = ahora - timedelta(days=meses_atras * 30)
        # Score fluctúa ligeramente
        delta = rng.randint(-30, 30)
        score_punto = max(300, min(999, xcore + delta - (n_puntos - 1 - i) * rng.randint(3, 12)))
        historial_score.append({
            "score": score_punto,
            "mes": _mes_label(dt),
        })
    # Asegurar que el último punto sea el score actual
    historial_score[-1]["score"] = xcore

    # ── Cuentas ────────────────────────────────────────────────────────
    cuentas: list[dict[str, Any]] = []
    entidades_usadas = rng.sample(_ENTIDADES, min(n_cuentas, len(_ENTIDADES)))

    for i in range(n_cuentas):
        entidad = entidades_usadas[i % len(entidades_usadas)]
        producto_info = rng.choice(_PRODUCTOS)
        producto, tipo_prod = producto_info

        es_abierta = i < n_abiertas
        estado = "abierta" if es_abierta else "cerrada"

        # Fecha de apertura (entre historia_anios atrás y 6 meses atrás)
        dias_apertura = rng.randint(180, historia_anios * 365)
        fecha_apertura = ahora - timedelta(days=dias_apertura)
        apertura_str = fecha_apertura.strftime("%Y-%m-%d")

        # Montos según tipo de producto
        if tipo_prod == "TC":
            aprobado = float(rng.choice([50_000, 75_000, 100_000, 150_000, 200_000, 300_000, 500_000]))
            if es_abierta:
                adeudado = round(aprobado * rng.uniform(0.05, uso_limite / 100 * 1.3), 2)
                cuota = round(adeudado * rng.uniform(0.03, 0.08), 2)
            else:
                adeudado = 0.0
                cuota = 0.0
        elif tipo_prod == "PR":
            aprobado = float(rng.choice([
                100_000, 250_000, 500_000, 750_000, 1_000_000, 2_000_000,
            ]))
            if es_abierta:
                adeudado = round(aprobado * rng.uniform(0.20, 0.85), 2)
                cuota = round(aprobado / rng.randint(24, 72), 2)
            else:
                adeudado = 0.0
                cuota = 0.0
        else:  # LC
            aprobado = float(rng.choice([200_000, 500_000, 1_000_000]))
            if es_abierta:
                adeudado = round(aprobado * rng.uniform(0.10, 0.50), 2)
                cuota = round(adeudado * 0.05, 2)
            else:
                adeudado = 0.0
                cuota = 0.0

        # Vencido según score
        if xcore >= 700:
            vencido = 0.0
        elif es_abierta and rng.random() < 0.35:
            vencido = round(rng.uniform(500, min(adeudado * 0.3, 25_000)), 2)
        else:
            vencido = 0.0

        # Vector de pago 24 meses: 0 = al día, 1 = atraso leve, 2 = atraso grave, – = sin info
        vector: list[str] = []
        meses_activos = min(24, dias_apertura // 30)
        for m in range(24):
            if m >= meses_activos:
                vector.append("-")
            elif not es_abierta and m < (24 - meses_activos):
                vector.append("-")
            elif xcore >= 700:
                vector.append("0")
            elif xcore >= 550:
                vector.append(rng.choices(["0", "1", "2"], weights=[85, 12, 3])[0])
            else:
                vector.append(rng.choices(["0", "1", "2"], weights=[55, 30, 15])[0])

        cuentas.append({
            "entidad": entidad,
            "producto": producto,
            "estado": estado,
            "apertura": apertura_str,
            "aprobado": aprobado,
            "adeudado": adeudado,
            "cuota": cuota,
            "vencido": vencido,
            "Historial_Pago": vector,
        })

    # ── Consultas previas ──────────────────────────────────────────────
    n_consultas = rng.randint(1, 6)
    consultas: list[dict[str, Any]] = []
    for i in range(n_consultas):
        dias_atras = rng.randint(5, 365)
        dt_consulta = ahora - timedelta(days=dias_atras)
        entidad_consulta = rng.choice(_ENTIDADES)
        consultas.append({
            "Fecha_Texto": _fecha_texto(dt_consulta),
            "Cliente_Consulta": entidad_consulta,
            "Mes_Label": f"{_MESES_CORTOS[dt_consulta.month - 1]} {dt_consulta.year}",
            "Es_Interna": entidad_consulta == "Banco Vimenca",
            "Repeticiones": rng.choices([1, 2, 3], weights=[70, 20, 10])[0],
        })
    # Ordenar por fecha descendente
    consultas.sort(key=lambda c: c["Fecha_Texto"], reverse=True)

    # ── Leads pre-aprobados ────────────────────────────────────────────
    leads: list[dict[str, Any]] = []
    if xcore >= 600:
        # TC aumento
        if rng.random() < 0.7:
            monto_tc = rng.choice([150_000, 200_000, 300_000, 500_000])
            leads.append({
                "tipo": "TC Aumento Límite",
                "Dictamen": "Pre-Aprobado",
                "Monto": monto_tc,
                "Cuota": round(monto_tc * 0.02, 2),
                "Moneda": "DOP",
                "Tasa": round(rng.uniform(2.95, 4.95), 2),
                "Plazo": 0,
                "Producto_Sugerido": rng.choice(["Visa Gold", "Visa Platinum", "Mastercard Gold"]),
            })
        # Préstamo consumo
        if rng.random() < 0.6:
            monto_pr = rng.choice([200_000, 350_000, 500_000, 750_000, 1_000_000])
            plazo_pr = rng.choice([24, 36, 48, 60])
            tasa_pr = round(rng.uniform(14.0, 22.0), 2)
            leads.append({
                "tipo": "PR Consumo",
                "Dictamen": "Pre-Aprobado",
                "Monto": monto_pr,
                "Cuota": round(monto_pr / plazo_pr, 2),
                "Moneda": "DOP",
                "Tasa": tasa_pr,
                "Plazo": plazo_pr,
                "Producto_Sugerido": "Préstamo Personal",
            })
        # Hipotecario (solo scores altos)
        if xcore >= 720 and rng.random() < 0.4:
            monto_hip = rng.choice([2_000_000, 3_500_000, 5_000_000])
            leads.append({
                "tipo": "PR Hipotecario",
                "Dictamen": "Pre-Aprobado",
                "Monto": monto_hip,
                "Cuota": round(monto_hip / 240, 2),
                "Moneda": "DOP",
                "Tasa": round(rng.uniform(9.0, 13.0), 2),
                "Plazo": 240,
                "Producto_Sugerido": "Hipotecario Vivienda",
            })

    # ── Localización ───────────────────────────────────────────────────

    # Teléfonos
    telefonos = [
        {
            "Telefono": f"809-{rng.randint(200, 999)}-{rng.randint(1000, 9999)}",
            "Tipo_Telefono": "Celular",
            "Lugar": 1,
        },
    ]
    if rng.random() < 0.6:
        telefonos.append({
            "Telefono": f"809-{rng.randint(200, 999)}-{rng.randint(1000, 9999)}",
            "Tipo_Telefono": "Residencia",
            "Lugar": 2,
        })
    if rng.random() < 0.3:
        telefonos.append({
            "Telefono": f"809-{rng.randint(200, 999)}-{rng.randint(1000, 9999)}",
            "Tipo_Telefono": "Trabajo",
            "Lugar": 3,
        })

    # Correos
    usuario_correo = f"{nombre.lower()}.{apellido1.lower()}"
    dominios = ["ejemplo.com", "correo.do", "mail.com.do", "demo.net"]
    correos = [{"Correo": f"{usuario_correo}@{rng.choice(dominios)}"}]

    # Direcciones
    calle = rng.choice(_CALLES)
    numero = rng.randint(10, 9999)
    sector = rng.choice(_SECTORES)
    direcciones = [
        {"Direccion": f"{calle} #{numero}, {sector}, Santo Domingo", "Orden": 1},
    ]
    if rng.random() < 0.3:
        calle2 = rng.choice([c for c in _CALLES if c != calle])
        sector2 = rng.choice([s for s in _SECTORES if s != sector])
        direcciones.append({
            "Direccion": f"{calle2} #{rng.randint(10, 9999)}, {sector2}, Santo Domingo",
            "Orden": 2,
        })

    # Familiares
    apellido_padre = apellido1
    apellido_madre = apellido2
    nombre_padre = rng.choice(_NOMBRES_M)
    nombre_madre = rng.choice(_NOMBRES_F)
    tiene_conyuge = rng.random() < 0.55
    if tiene_conyuge:
        if sexo == "M":
            nombre_conyuge = rng.choice(_NOMBRES_F) + " " + rng.choice(_APELLIDOS)
        else:
            nombre_conyuge = rng.choice(_NOMBRES_M) + " " + rng.choice(_APELLIDOS)
    else:
        nombre_conyuge = ""

    familiares = {
        "Nombre_Padre": f"{nombre_padre} {apellido_padre}",
        "Nombre_Madre": f"{nombre_madre} {apellido_madre}",
        "Nombre_Conyugue": nombre_conyuge,
        "Actividad_Comercial": rng.choice(_ACTIVIDADES),
    }

    # Vehículos
    vehiculos: list[dict[str, Any]] = []
    if rng.random() < 0.55:
        marca_info = rng.choice(_MARCAS_VEHICULOS)
        marca, modelos = marca_info
        vehiculos.append({
            "Marca": marca,
            "Modelo": rng.choice(modelos),
            "Anio": rng.randint(2016, ahora.year),
            "Placa": f"{rng.choice('ABCDEFG')}{rng.randint(100000, 999999)}",
            "Color": rng.choice(_COLORES_VEHICULO),
        })
        if rng.random() < 0.25:
            marca2, modelos2 = rng.choice([m for m in _MARCAS_VEHICULOS if m[0] != marca])
            vehiculos.append({
                "Marca": marca2,
                "Modelo": rng.choice(modelos2),
                "Anio": rng.randint(2012, ahora.year - 2),
                "Placa": f"{rng.choice('ABCDEFG')}{rng.randint(100000, 999999)}",
                "Color": rng.choice(_COLORES_VEHICULO),
            })

    # Relacionados
    relacionados: list[dict[str, Any]] = []
    relacionados.append({
        "Nombres": nombre_padre,
        "Apellidos": f"{apellido_padre} {rng.choice(_APELLIDOS)}",
        "Relacion": "Padre",
        "Cedula_Nueva": _formatear_cedula(f"{rng.randint(0, 99999999999):011d}"),
        "Edad": edad + rng.randint(20, 35),
    })
    relacionados.append({
        "Nombres": nombre_madre,
        "Apellidos": f"{apellido_madre} {rng.choice(_APELLIDOS)}",
        "Relacion": "Madre",
        "Cedula_Nueva": _formatear_cedula(f"{rng.randint(0, 99999999999):011d}"),
        "Edad": edad + rng.randint(18, 30),
    })
    if tiene_conyuge:
        partes_conyuge = nombre_conyuge.split(" ", 1)
        relacionados.append({
            "Nombres": partes_conyuge[0],
            "Apellidos": partes_conyuge[1] if len(partes_conyuge) > 1 else "",
            "Relacion": "Cónyuge",
            "Cedula_Nueva": _formatear_cedula(f"{rng.randint(0, 99999999999):011d}"),
            "Edad": edad + rng.randint(-5, 5),
        })

    localizacion = {
        "telefonos": telefonos,
        "correos": correos,
        "direcciones": direcciones,
        "familiares": familiares,
        "vehiculos": vehiculos,
        "relacionados": relacionados,
    }

    # ── Bancarización ──────────────────────────────────────────────────
    entidades_bancarizadas = list({c["entidad"] for c in cuentas if c["estado"] == "abierta"})
    bancarizado = len(entidades_bancarizadas) > 0

    # ── Fechas del reporte ─────────────────────────────────────────────
    mes_evaluacion = ahora.strftime("%Y%m01")
    fecha_vencimiento = (ahora + timedelta(days=35)).strftime("%Y%m%d")

    # ── Resumen de cuentas (para compatibilidad con buro_view) ─────────
    abiertas = [c for c in cuentas if c["estado"] == "abierta"]
    cerradas = [c for c in cuentas if c["estado"] != "abierta"]
    adeudado_total = sum(float(c["adeudado"]) for c in abiertas)
    cuotas_total = sum(float(c["cuota"]) for c in abiertas)

    resumen_cuentas = [
        {
            "tipo": "Tarjetas / Líneas DO",
            "estado": "Normal",
            "cant": sum(1 for c in abiertas if c["producto"].startswith("TC") or c["producto"].startswith("Línea")),
            "adeudado": sum(c["adeudado"] for c in abiertas if c["producto"].startswith("TC") or c["producto"].startswith("Línea")),
            "cuotas": sum(c["cuota"] for c in abiertas if c["producto"].startswith("TC") or c["producto"].startswith("Línea")),
        },
        {
            "tipo": "Préstamos DO",
            "estado": "Normal",
            "cant": sum(1 for c in abiertas if c["producto"].startswith("PR")),
            "adeudado": sum(c["adeudado"] for c in abiertas if c["producto"].startswith("PR")),
            "cuotas": sum(c["cuota"] for c in abiertas if c["producto"].startswith("PR")),
        },
        {
            "tipo": "Cerradas",
            "estado": "Cerradas",
            "cant": len(cerradas),
            "adeudado": 0,
            "cuotas": 0,
        },
    ]

    # ── Construcción del reporte final ─────────────────────────────────
    reporte: dict[str, Any] = {
        # Identificación
        "Cedula": _formatear_cedula(key),
        "Nombre": nombre,
        "Apellidos": apellidos,
        "Nombre_Completo": nombre_completo,
        "Tipo_Persona": "F",
        "Sexo": sexo,
        "Fecha_De_Nacimiento": fecha_nac,
        "Edad": edad,
        "Nacionalidad": "DOMINICANA" if sexo == "F" else "DOMINICANO",
        "Foto_Cliente": None,

        # Scoring
        "Xcore": xcore,
        "XCORE": xcore,  # alias para compatibilidad
        "Score": xcore,   # alias para compatibilidad
        "Bancarizado": bancarizado,
        "Bancarizacion_Entidades": entidades_bancarizadas,
        "ChanceRiesgoEnContra": chance_contra,
        "ChanceRiesgoFavor": chance_favor,
        "ChanceFavor": chance_favor,
        "ChanceContra": chance_contra,
        "Eic_Min": eic_min,
        "EicMin": eic_min,
        "Eic_Max": eic_max,
        "EicMax": eic_max,
        "Asalariado": es_asalariado,
        "Mes_Evaluacion": mes_evaluacion,
        "Fecha_Vencimiento": fecha_vencimiento,

        # Resumen
        "HistoriaAnios": historia_anios,
        "UsoLimitePct": uso_limite,
        "CuentasActivas": n_abiertas,
        "CuentasCerradas": n_cerradas,
        "CuentasTotales": n_cuentas,
        "AtrasoMonto": atraso_monto,
        "AtrasoTotal": atraso_monto,

        # Capacidad
        "Ingresos": ingresos,
        "Comprometido": comprometido,
        "EndeudamientoPct": endeudamiento_pct,
        "DisponibleMes": disponible,

        # Historial de Score
        "HistorialScore": historial_score,

        # Cuentas
        "Cuentas": cuentas,
        "ResumenCuentas": resumen_cuentas,

        # Consultas previas
        "ConsultasPrevias": consultas,

        # Leads
        "Leads": leads,

        # Localización
        "Localizacion": localizacion,

        # Dictamen
        "DictamenBuro": dictamen,
        "Resumen": f"Reporte demo generado para cédula {_formatear_cedula(key)}.",

        # Metadatos del reporte
        "Proveedor": "Demo Buró NOVA",
        "FechaConsulta": ahora.strftime("%Y-%m-%d"),
        "FechaVencimiento": (ahora + timedelta(days=35)).strftime("%Y-%m-%d"),
    }

    return reporte
