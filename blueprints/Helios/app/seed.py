from datetime import datetime

from sqlalchemy.orm import Session

from app.config import AUTH_APP
from app.models import PerfilUsuario, PoliticaPassword, TipoDato, TipoFlujo, Usuario
from app.services.dato_formato import TIPOS_DATO_CATALOGO
from app.services.password_policy import hash_password, obtener_politica

PERFILES = [
    (1, "Super Usuario", "Tiene todos los accesos"),
    (2, "Administrador de Credenciales", "Crea usuarios y asigna el nivel de acceso"),
    (3, "Soporte Operativo", "Puede cambiar etapas, reasignar casos, etc."),
    (4, "Operativo", "Trabaja los casos en las etapas donde su grupo interviene"),
]

TIPOS_FLUJO = ["Credito", "Operativo"]


def ensure_tipos_dato(db: Session) -> None:
    """Inserta o actualiza el catálogo de tipos (idempotente)."""
    for tid, nombre, input_html, codigo in TIPOS_DATO_CATALOGO:
        existente = db.get(TipoDato, tid)
        if existente is None:
            db.add(TipoDato(id=tid, nombre=nombre, input_html=input_html, codigo=codigo))
        else:
            existente.nombre = nombre
            existente.input_html = input_html
            existente.codigo = codigo


def seed(db: Session) -> None:
    if db.query(PerfilUsuario).count() == 0:
        for pid, nombre, desc in PERFILES:
            db.add(PerfilUsuario(id=pid, nombre=nombre, descripcion=desc))

    ensure_tipos_dato(db)

    if db.query(TipoFlujo).count() == 0:
        for nombre in TIPOS_FLUJO:
            db.add(TipoFlujo(nombre=nombre))

    if db.query(Usuario).count() == 0:
        db.add(
            Usuario(
                usuario_ad="admin",
                nombre="Administrador Helios",
                tipo_autenticacion=AUTH_APP,
                password_hash=hash_password("admin"),
                debe_cambiar_password=False,
                password_fecha_cambio=datetime.now(),
                perfil_id=1,
                activo=True,
            )
        )

    db.commit()
    # Asegura politica global por defecto
    if db.query(PoliticaPassword).count() == 0:
        obtener_politica(db)
