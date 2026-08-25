import os
import urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

_NOVA_ROOT = BASE_DIR.parent.parent
_INSTANCE = _NOVA_ROOT / "instance"
_INSTANCE.mkdir(exist_ok=True)


def _fix_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def _sqlite_url() -> str:
    sqlite_path = _INSTANCE / "helios.db"
    return f"sqlite:///{sqlite_path.as_posix()}"


def _mssql_url() -> str:
    SQL_SERVER = os.getenv("HELIOS_SQL_SERVER", r"BVNBEET0110\BIDEV")
    SQL_DATABASE = os.getenv("HELIOS_SQL_DATABASE", "Helios")
    SQL_DRIVER = os.getenv("HELIOS_SQL_DRIVER", "ODBC Driver 17 for SQL Server")
    _odbc = urllib.parse.quote_plus(
        f"DRIVER={{{SQL_DRIVER}}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};Trusted_Connection=yes;"
    )
    return f"mssql+pyodbc:///?odbc_connect={_odbc}"


def _resolve_database_url() -> str:
    explicit = os.getenv("HELIOS_DATABASE_URL")
    if explicit:
        return _fix_url(explicit)

    if os.getenv("HELIOS_USE_MSSQL") == "1":
        return _mssql_url()

    railway = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))
    shared = os.getenv("DATABASE_URL")
    if railway and shared:
        return _fix_url(shared)

    # Por defecto (Nova Projects embebido): SQLite operativo sin VPN/SQL Server
    return _sqlite_url()


DATABASE_URL = _resolve_database_url()

# Compat con scripts/servicios que importan estos nombres
SQL_SERVER = os.getenv("HELIOS_SQL_SERVER", r"BVNBEET0110\BIDEV")
SQL_DATABASE = os.getenv("HELIOS_SQL_DATABASE", "Helios")
SQL_DRIVER = os.getenv("HELIOS_SQL_DRIVER", "ODBC Driver 17 for SQL Server")

SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv(
    "HELIOS_SECRET_KEY", "helios-dev-secret-cambiar-en-produccion"
)
AD_DOMAIN = os.getenv("HELIOS_AD_DOMAIN", "BVIMENCA")

AUTH_APP = "APP"
AUTH_AD = "AD"

DATOS_INLINE_MAX = int(os.getenv("HELIOS_DATOS_INLINE_MAX", "6"))


def should_render_datos_inline(count: int) -> bool:
    try:
        n = int(count)
    except (TypeError, ValueError):
        return False
    return n <= DATOS_INLINE_MAX
