"""
Migra Helios.bak (SQL Server) → SQLite local y opcionalmente Postgres (Railway).

Requisito: instancia SQL Server **2025** (el .bak es v17). No se puede restaurar
en SQL 2016 del banco ni leer el .bak directo en Postgres/SQLite.

Uso típico:
  1) Instalar SQL Server 2025 Express (winget) o Docker mssql 2025
  2) python scripts/migrate_helios_bak.py --restore --bak "C:\\...\\Helios.bak"
  3) python scripts/migrate_helios_bak.py --to-sqlite
  4) python scripts/migrate_helios_bak.py --to-postgres  (usa DATABASE_URL / HELIOS_DATABASE_URL)

Adjuntos: copie la carpeta uploads del Helios origen a blueprints/Helios/uploads
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELIOS = ROOT / "blueprints" / "Helios"
if str(HELIOS) not in sys.path:
    sys.path.insert(0, str(HELIOS))

DEFAULT_BAK = Path(
    r"c:\Users\adsanchez\OneDrive - Banco Multiple Vimenca\Desktop\Helios.bak"
)
DEFAULT_UPLOADS_SRC = Path(
    r"c:\Users\adsanchez\OneDrive - Banco Multiple Vimenca\Desktop\Helios\uploads"
)
SQLITE_OUT = ROOT / "instance" / "helios.db"


def _pyodbc_connect(server: str, database: str = "master"):
    import pyodbc

    driver = os.getenv("HELIOS_SQL_DRIVER", "ODBC Driver 17 for SQL Server")
    cs = (
        f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};"
        "Trusted_Connection=yes;TrustServerCertificate=yes;"
    )
    return pyodbc.connect(cs, autocommit=True, timeout=60)


def cmd_restore(bak: Path, server: str, db_name: str) -> None:
    if not bak.is_file():
        raise SystemExit(f"No existe bak: {bak}")
    # Copiar bak a TEMP local (SQL local puede leerlo)
    staging = Path(os.environ.get("TEMP", r"C:\Temp")) / "Helios_restore.bak"
    shutil.copy2(bak, staging)
    bak_sql = str(staging)
    print("staging", bak_sql)

    cn = _pyodbc_connect(server, "master")
    cur = cn.cursor()
    cur.execute("RESTORE FILELISTONLY FROM DISK = ?", bak_sql)
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    data = next(r for r in rows if r["Type"] == "D")
    log = next(r for r in rows if r["Type"] == "L")
    print("logical", data["LogicalName"], log["LogicalName"])

    cur.execute(
        "SELECT CAST(SERVERPROPERTY('InstanceDefaultDataPath') AS nvarchar(4000)), "
        "CAST(SERVERPROPERTY('InstanceDefaultLogPath') AS nvarchar(4000))"
    )
    data_dir, log_dir = cur.fetchone()
    data_dir = (data_dir or str(Path(os.environ["TEMP"]))).rstrip("\\") + "\\"
    log_dir = (log_dir or data_dir).rstrip("\\") + "\\"
    mdf = f"{data_dir}{db_name}.mdf"
    ldf = f"{log_dir}{db_name}_log.ldf"

    cur.execute("SELECT 1 FROM sys.databases WHERE name = ?", db_name)
    exists = cur.fetchone() is not None
    if exists:
        cur.execute(f"ALTER DATABASE [{db_name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE")
    replace = ", REPLACE" if exists else ""
    sql = f"""
RESTORE DATABASE [{db_name}]
FROM DISK = N'{bak_sql.replace("'", "''")}'
WITH MOVE N'{data["LogicalName"].replace("'", "''")}' TO N'{mdf.replace("'", "''")}',
     MOVE N'{log["LogicalName"].replace("'", "''")}' TO N'{ldf.replace("'", "''")}',
     RECOVERY{replace}
"""
    print("RESTORE…")
    cur.execute(sql)
    while cur.nextset():
        pass
    if exists:
        cur.execute(f"ALTER DATABASE [{db_name}] SET MULTI_USER")
    cur.execute("SELECT name, state_desc FROM sys.databases WHERE name = ?", db_name)
    print("OK", cur.fetchone())
    cn.close()


def _table_names(cur) -> list[str]:
    cur.execute(
        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_TYPE='BASE TABLE' AND TABLE_SCHEMA='dbo' ORDER BY 1"
    )
    return [r[0] for r in cur.fetchall()]


def _copy_table(src_cur, dest_conn, table: str) -> int:
    src_cur.execute(f"SELECT * FROM dbo.[{table}]")
    cols = [d[0] for d in src_cur.description]
    rows = src_cur.fetchall()
    if not cols:
        return 0
    # crear tabla simple en sqlite/postgres via SQLAlchemy dump de filas
    placeholders = ",".join(["?"] * len(cols)) if dest_conn.dialect == "sqlite" else ",".join(["%s"] * len(cols))
    # usamos sqlite3 / psycopg según dialecto
    return _insert_rows(dest_conn, table, cols, rows)


class _Dest:
    def __init__(self, kind: str, conn):
        self.dialect = kind
        self.conn = conn


def _insert_rows(dest: _Dest, table: str, cols: list[str], rows) -> int:
    if not rows:
        return 0
    col_sql = ", ".join(f'"{c}"' for c in cols)
    if dest.dialect == "sqlite":
        ph = ", ".join(["?"] * len(cols))
        sql = f'INSERT OR REPLACE INTO "{table}" ({col_sql}) VALUES ({ph})'
        dest.conn.executemany(sql, [tuple(r) for r in rows])
        dest.conn.commit()
    else:
        ph = ", ".join(["%s"] * len(cols))
        sql = f'INSERT INTO "{table}" ({col_sql}) VALUES ({ph}) ON CONFLICT DO NOTHING'
        with dest.conn.cursor() as cur:
            cur.executemany(sql, [tuple(r) for r in rows])
        dest.conn.commit()
    return len(rows)


def cmd_to_sqlite(server: str, db_name: str, out: Path) -> None:
    import sqlite3

    from sqlalchemy import create_engine, inspect, text

    # 1) Crear esquema Helios en SQLite con los modelos
    os.environ["HELIOS_DATABASE_URL"] = f"sqlite:///{out.as_posix()}"
    # re-import fresco
    import importlib

    import app.config as cfg

    importlib.reload(cfg)
    import app.database as dbmod

    importlib.reload(dbmod)
    from app import models  # noqa: F401
    from app.database import Base, engine

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    # recreate engine after reload
    from sqlalchemy.orm import sessionmaker

    eng = create_engine(f"sqlite:///{out.as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    print("schema SQLite OK", out)

    # 2) Copiar datos desde MSSQL (nombres de tabla físicos)
    src = _pyodbc_connect(server, db_name)
    scur = src.cursor()
    tables = _table_names(scur)
    print("source tables", len(tables))

    raw = sqlite3.connect(str(out))
    dest = _Dest("sqlite", raw)

    # Desactivar FK temporalmente
    raw.execute("PRAGMA foreign_keys=OFF")
    total = 0
    for t in tables:
        # ¿existe en sqlite?
        exists = raw.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)
        ).fetchone()
        if not exists:
            print("  skip (no en modelos)", t)
            continue
        scur.execute(f"SELECT * FROM dbo.[{t}]")
        cols = [d[0] for d in scur.description]
        # mapear columnas SQL Server → sqlite (pueden diferir en casing)
        sqlite_cols = [r[1] for r in raw.execute(f'PRAGMA table_info("{t}")').fetchall()]
        # intersectar por nombre case-insensitive
        lower_map = {c.lower(): c for c in sqlite_cols}
        use_cols = []
        idx = []
        for i, c in enumerate(cols):
            if c.lower() in lower_map:
                use_cols.append(lower_map[c.lower()])
                idx.append(i)
        if not use_cols:
            print("  skip cols", t)
            continue
        rows = []
        for r in scur.fetchall():
            rows.append(tuple(r[i] for i in idx))
        # clear + insert
        raw.execute(f'DELETE FROM "{t}"')
        n = _insert_rows(dest, t, use_cols, rows)
        total += n
        print(f"  + {t}: {n}")
    raw.execute("PRAGMA foreign_keys=ON")
    raw.close()
    src.close()
    print("SQLite listo:", out, "filas~", total)


def cmd_to_postgres(sqlite_path: Path, database_url: str) -> None:
    """Copia SQLite → Postgres (Railway) usando SQLAlchemy reflection simple."""
    from sqlalchemy import create_engine, MetaData, Table, text
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    if database_url.startswith("postgres://"):
        database_url = "postgresql://" + database_url[len("postgres://") :]

    src = create_engine(f"sqlite:///{sqlite_path.as_posix()}")
    dst = create_engine(database_url)

    # crear tablas con modelos Helios
    os.environ["HELIOS_DATABASE_URL"] = database_url
    import importlib
    import app.config as cfg

    importlib.reload(cfg)
    from app import models  # noqa: F401
    from app.database import Base

    Base.metadata.create_all(dst)

    md = MetaData()
    md.reflect(bind=src)
    with src.connect() as sconn, dst.begin() as dconn:
        for name, table in md.tables.items():
            rows = [dict(r) for r in sconn.execute(text(f'SELECT * FROM "{name}"')).mappings()]
            if not rows:
                print(" ", name, 0)
                continue
            dtable = Table(name, MetaData(), autoload_with=dst)
            # upsert best-effort
            dconn.execute(dtable.delete())
            dconn.execute(dtable.insert(), rows)
            print(" ", name, len(rows))
    print("Postgres OK")


def cmd_copy_uploads(src: Path, dest: Path) -> None:
    if not src.is_dir():
        print("uploads origen no encontrado", src)
        return
    dest.mkdir(parents=True, exist_ok=True)
    for p in src.rglob("*"):
        if p.is_file():
            rel = p.relative_to(src)
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
            print(" +", rel)
    print("uploads →", dest)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--bak", type=Path, default=DEFAULT_BAK)
    p.add_argument("--server", default=os.getenv("HELIOS_SQL_SERVER", r".\SQLEXPRESS"))
    p.add_argument("--db", default="Helios")
    p.add_argument("--restore", action="store_true")
    p.add_argument("--to-sqlite", action="store_true")
    p.add_argument("--to-postgres", action="store_true")
    p.add_argument("--sqlite", type=Path, default=SQLITE_OUT)
    p.add_argument("--copy-uploads", action="store_true")
    p.add_argument("--uploads-src", type=Path, default=DEFAULT_UPLOADS_SRC)
    args = p.parse_args()

    if args.copy_uploads:
        cmd_copy_uploads(args.uploads_src, HELIOS / "uploads")
    if args.restore:
        cmd_restore(args.bak, args.server, args.db)
    if args.to_sqlite:
        cmd_to_sqlite(args.server, args.db, args.sqlite)
    if args.to_postgres:
        url = os.getenv("HELIOS_DATABASE_URL") or os.getenv("DATABASE_URL")
        if not url:
            raise SystemExit("Defina DATABASE_URL o HELIOS_DATABASE_URL (Postgres Railway)")
        cmd_to_postgres(args.sqlite, url)
    if not any([args.restore, args.to_sqlite, args.to_postgres, args.copy_uploads]):
        p.print_help()
        print(
            "\nEl .bak NO se puede cargar directo en Railway. "
            "Hace falta SQL Server 2025 local/Docker para restaurar y luego --to-sqlite/--to-postgres."
        )


if __name__ == "__main__":
    main()
