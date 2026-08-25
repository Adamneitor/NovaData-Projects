"""Politicas de contraseña: validacion, scoring, hash y estimacion de crack time."""

from __future__ import annotations

import hashlib
import math
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

import bcrypt
from sqlalchemy.orm import Session

from app.models import (
    AuditoriaPassword,
    PoliticaPassword,
    Usuario,
    UsuarioPasswordHistorial,
)

MAYUS_NINGUNA = "ninguna"
MAYUS_INICIO = "inicio"
MAYUS_FINAL = "final"
MAYUS_CUALQUIERA = "cualquiera"

ESPECIALES = set("!@#$%^&*()_+-=[]{}|;:'\",.<>/?`~\\")


@dataclass
class ResultadoValidacion:
    valida: bool
    errores: list[str] = field(default_factory=list)
    nivel: str = "debil"  # debil | media | fuerte
    score: int = 0  # 0-100
    entropia_bits: float = 0.0
    crack_tiempo: str = ""
    crack_segundos: float = 0.0
    reglas: dict = field(default_factory=dict)


def obtener_politica(db: Session) -> PoliticaPassword:
    pol = db.query(PoliticaPassword).filter(PoliticaPassword.activo == True).order_by(PoliticaPassword.id).first()  # noqa: E712
    if not pol:
        pol = PoliticaPassword(
            longitud_minima=8,
            mayusculas=MAYUS_CUALQUIERA,
            requiere_numero=True,
            requiere_especial=True,
            max_repetidos_consecutivos=3,
            permite_espacios=False,
            historial_no_reutilizar=5,
            vigencia_default_dias=None,
            activo=True,
        )
        db.add(pol)
        db.commit()
        db.refresh(pol)
    return pol


def politica_a_dict(pol: PoliticaPassword) -> dict:
    return {
        "longitud_minima": pol.longitud_minima,
        "mayusculas": pol.mayusculas,
        "requiere_numero": pol.requiere_numero,
        "requiere_especial": pol.requiere_especial,
        "max_repetidos_consecutivos": pol.max_repetidos_consecutivos,
        "permite_espacios": pol.permite_espacios,
        "historial_no_reutilizar": pol.historial_no_reutilizar,
        "vigencia_default_dias": pol.vigencia_default_dias,
    }


# ---------------------------------------------------------------------------
# Hashing: bcrypt (nuevo) + PBKDF2 legado (salt$hex)
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """bcrypt con cost factor 12. Prefijo 'bcrypt$' para distinguir del legado."""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
    return "bcrypt$" + hashed.decode("utf-8")


def _verify_pbkdf2(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return secrets.compare_digest(f"{salt}${check}", stored)


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    if stored.startswith("bcrypt$"):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored[7:].encode("utf-8"))
        except ValueError:
            return False
    # Legado PBKDF2 salt$digest
    if "$" in stored:
        return _verify_pbkdf2(password, stored)
    return False


def needs_rehash(stored: str | None) -> bool:
    return bool(stored) and not stored.startswith("bcrypt$")


# ---------------------------------------------------------------------------
# Validacion de politicas
# ---------------------------------------------------------------------------


def _max_run(password: str) -> int:
    if not password:
        return 0
    mejor = actual = 1
    for i in range(1, len(password)):
        if password[i] == password[i - 1]:
            actual += 1
            mejor = max(mejor, actual)
        else:
            actual = 1
    return mejor


def validar_contra_politica(password: str, pol: PoliticaPassword) -> list[str]:
    errores: list[str] = []
    if len(password) < pol.longitud_minima:
        errores.append(f"Debe tener al menos {pol.longitud_minima} caracteres.")

    if not pol.permite_espacios and any(c.isspace() for c in password):
        errores.append("No se permiten espacios en la contraseña.")

    may = (pol.mayusculas or MAYUS_NINGUNA).lower()
    if may == MAYUS_INICIO:
        if not password or not password[0].isupper():
            errores.append("Debe comenzar con una letra mayúscula.")
    elif may == MAYUS_FINAL:
        if not password or not password[-1].isupper():
            errores.append("Debe terminar con una letra mayúscula.")
    elif may == MAYUS_CUALQUIERA:
        if not any(c.isupper() for c in password):
            errores.append("Debe incluir al menos una letra mayúscula.")

    if pol.requiere_numero and not any(c.isdigit() for c in password):
        errores.append("Debe incluir al menos un número.")

    if pol.requiere_especial and not any(c in ESPECIALES for c in password):
        errores.append("Debe incluir al menos un carácter especial (!@#$%...).")

    max_rep = pol.max_repetidos_consecutivos or 0
    if max_rep > 0 and _max_run(password) > max_rep:
        errores.append(f"No se permiten más de {max_rep} caracteres iguales consecutivos.")

    return errores


def _charset_size(password: str) -> int:
    size = 0
    if any(c.islower() for c in password):
        size += 26
    if any(c.isupper() for c in password):
        size += 26
    if any(c.isdigit() for c in password):
        size += 10
    if any(c in ESPECIALES for c in password):
        size += len(ESPECIALES)
    if any(c.isspace() for c in password):
        size += 1
    return max(size, 1)


def estimar_entropia(password: str) -> float:
    """Entropía aproximada H ≈ L * log2(N), con penalización por runs y patrones triviales."""
    if not password:
        return 0.0
    n = _charset_size(password)
    h = len(password) * math.log2(n)
    # Penaliza repeticiones consecutivas
    run = _max_run(password)
    if run >= 3:
        h -= (run - 2) * 4
    # Penaliza secuencias comunes / solo digitos o solo letras
    if password.isdigit() or password.isalpha():
        h *= 0.75
    lower = password.lower()
    for commons in ("password", "123456", "qwerty", "admin", "helios", "vimenca"):
        if commons in lower:
            h *= 0.5
            break
    return max(h, 0.0)


def formatear_tiempo(segundos: float) -> str:
    if segundos < 1:
        return "menos de 1 segundo"
    unidades = [
        (60, "segundo", "segundos"),
        (60, "minuto", "minutos"),
        (24, "hora", "horas"),
        (365, "día", "días"),
        (100, "año", "años"),
        (10, "siglo", "siglos"),
    ]
    valor = segundos
    nombre_s, nombre_p = "segundo", "segundos"
    for div, s, p in unidades:
        if valor < div:
            nombre_s, nombre_p = s, p
            break
        valor /= div
        nombre_s, nombre_p = s, p
    else:
        return "más de milenios"
    v = int(valor)
    return f"~{v} {nombre_s if v == 1 else nombre_p}"


def estimar_crack_time(entropia_bits: float, intentos_por_segundo: float = 1e10) -> tuple[float, str]:
    """
    Modelo de fuerza bruta online/offline:
    - Asume atacante offline con GPU (~10^10 intentos/s para hashes lentos es optimista;
      usamos ese techo como peor caso de amenaza para educar al usuario).
    - Tiempo medio ≈ 2^(H-1) / velocidad.
    """
    if entropia_bits <= 0:
        return 0.0, "inmediato"
    intentos = 2 ** (entropia_bits - 1)
    segs = intentos / intentos_por_segundo
    return segs, formatear_tiempo(segs)


def clasificar_fuerza(entropia_bits: float, cumple_politica: bool) -> tuple[str, int]:
    # Score 0-100 basado en entropía (referencia: ~40 débil, ~60 media, ~80+ fuerte)
    score = int(min(100, max(0, (entropia_bits / 90) * 100)))
    if not cumple_politica or entropia_bits < 40:
        return "debil", min(score, 39)
    if entropia_bits < 60:
        return "media", max(40, min(score, 69))
    return "fuerte", max(70, score)


def evaluar_password(password: str, pol: PoliticaPassword) -> ResultadoValidacion:
    errores = validar_contra_politica(password, pol)
    entropia = estimar_entropia(password)
    crack_s, crack_txt = estimar_crack_time(entropia)
    nivel, score = clasificar_fuerza(entropia, not errores)
    reglas = {
        "longitud_ok": len(password) >= pol.longitud_minima,
        "mayusculas_ok": _check_mayus(password, pol.mayusculas),
        "numero_ok": (not pol.requiere_numero) or any(c.isdigit() for c in password),
        "especial_ok": (not pol.requiere_especial) or any(c in ESPECIALES for c in password),
        "repetidos_ok": (pol.max_repetidos_consecutivos or 0) == 0
        or _max_run(password) <= pol.max_repetidos_consecutivos,
        "espacios_ok": pol.permite_espacios or not any(c.isspace() for c in password),
    }
    return ResultadoValidacion(
        valida=not errores,
        errores=errores,
        nivel=nivel,
        score=score,
        entropia_bits=round(entropia, 1),
        crack_tiempo=crack_txt,
        crack_segundos=crack_s,
        reglas=reglas,
    )


def _check_mayus(password: str, modo: str) -> bool:
    modo = (modo or MAYUS_NINGUNA).lower()
    if modo == MAYUS_NINGUNA:
        return True
    if not password:
        return False
    if modo == MAYUS_INICIO:
        return password[0].isupper()
    if modo == MAYUS_FINAL:
        return password[-1].isupper()
    return any(c.isupper() for c in password)


def resultado_a_dict(r: ResultadoValidacion) -> dict:
    return asdict(r)


# ---------------------------------------------------------------------------
# Historial, expiracion y ciclo de vida
# ---------------------------------------------------------------------------


def password_en_historial(db: Session, usuario_id: int, password: str, n: int) -> bool:
    if n <= 0:
        return False
    rows = (
        db.query(UsuarioPasswordHistorial)
        .filter(UsuarioPasswordHistorial.usuario_id == usuario_id)
        .order_by(UsuarioPasswordHistorial.id.desc())
        .limit(n)
        .all()
    )
    return any(verify_password(password, row.password_hash) for row in rows)


def password_expirada(user: Usuario) -> bool:
    if not user.dias_vigencia_password or user.dias_vigencia_password <= 0:
        return False
    if not user.password_fecha_cambio:
        return True  # nunca cambio: forzar
    limite = user.password_fecha_cambio + timedelta(days=user.dias_vigencia_password)
    return datetime.now() >= limite


def password_vence_en(user: Usuario) -> int | None:
    """Dias restantes o None si no aplica. Negativo si ya vencio."""
    if not user.dias_vigencia_password or not user.password_fecha_cambio:
        return None
    limite = user.password_fecha_cambio + timedelta(days=user.dias_vigencia_password)
    return (limite.date() - datetime.now().date()).days


def asignar_password(
    db: Session,
    user: Usuario,
    password_nueva: str,
    *,
    actor: Usuario | None,
    evento: str,
    forzar_cambio_siguiente: bool = False,
    ip: str | None = None,
    detalle: str | None = None,
) -> ResultadoValidacion:
    pol = obtener_politica(db)
    resultado = evaluar_password(password_nueva, pol)
    if not resultado.valida:
        return resultado

    if password_en_historial(db, user.id, password_nueva, pol.historial_no_reutilizar):
        resultado.valida = False
        resultado.errores.append(
            f"No puede reutilizar ninguna de sus últimas {pol.historial_no_reutilizar} contraseñas."
        )
        return resultado

    if user.password_hash and verify_password(password_nueva, user.password_hash):
        resultado.valida = False
        resultado.errores.append("La nueva contraseña debe ser distinta a la actual.")
        return resultado

    # Archivar hash actual en historial
    if user.password_hash:
        db.add(UsuarioPasswordHistorial(usuario_id=user.id, password_hash=user.password_hash))

    user.password_hash = hash_password(password_nueva)
    user.password_fecha_cambio = datetime.now()
    user.debe_cambiar_password = forzar_cambio_siguiente

    db.add(
        AuditoriaPassword(
            usuario_afectado_id=user.id,
            actor_id=actor.id if actor else user.id,
            evento=evento,
            detalle=detalle,
            ip=ip,
        )
    )
    # Poda de historial: conservar solo 2*N por usuario
    limite = max(pol.historial_no_reutilizar * 2, 10)
    viejos = (
        db.query(UsuarioPasswordHistorial)
        .filter(UsuarioPasswordHistorial.usuario_id == user.id)
        .order_by(UsuarioPasswordHistorial.id.desc())
        .offset(limite)
        .all()
    )
    for v in viejos:
        db.delete(v)

    db.flush()
    return resultado


def registrar_auditoria(
    db: Session,
    *,
    usuario_afectado_id: int,
    actor_id: int | None,
    evento: str,
    detalle: str | None = None,
    ip: str | None = None,
) -> None:
    db.add(
        AuditoriaPassword(
            usuario_afectado_id=usuario_afectado_id,
            actor_id=actor_id,
            evento=evento,
            detalle=detalle,
            ip=ip,
        )
    )
