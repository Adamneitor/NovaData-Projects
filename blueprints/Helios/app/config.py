import os
import urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

SQL_SERVER = os.getenv("HELIOS_SQL_SERVER", r"BVNBEET0110\BIDEV")
SQL_DATABASE = os.getenv("HELIOS_SQL_DATABASE", "Helios")
SQL_DRIVER = os.getenv("HELIOS_SQL_DRIVER", "ODBC Driver 17 for SQL Server")

_odbc = urllib.parse.quote_plus(
    f"DRIVER={{{SQL_DRIVER}}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};Trusted_Connection=yes;"
)
DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={_odbc}"

SECRET_KEY = os.getenv("HELIOS_SECRET_KEY", "helios-dev-secret-cambiar-en-produccion")
# Dominio AD para autenticar usuarios tipo Active Directory (sin prefijo DOMAIN\)
AD_DOMAIN = os.getenv("HELIOS_AD_DOMAIN", "BVIMENCA")

AUTH_APP = "APP"
AUTH_AD = "AD"

# Umbral UX por etapa (cualquier etapa del flujo):
# ≤ N datos configurados → edición inline en el detalle del caso.
# > N → captura/edición en formulario dedicado.
# La consulta del expediente (valores ya capturados) SIEMPRE es visible en etapas posteriores.
DATOS_INLINE_MAX = int(os.getenv("HELIOS_DATOS_INLINE_MAX", "6"))


def should_render_datos_inline(count: int) -> bool:
    """True si hay ≤ DATOS_INLINE_MAX ítems (incluye 0).
    False cuando se supera el umbral (> 6 por defecto)."""
    try:
        n = int(count)
    except (TypeError, ValueError):
        return False
    return n <= DATOS_INLINE_MAX
