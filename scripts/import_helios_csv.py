"""
Importa el dump CSV de Helios (export del .bak) a SQLite/Postgres vía modelos ORM.

Uso:
  python scripts/import_helios_csv.py
  python scripts/import_helios_csv.py --dir "C:\\Users\\...\\Downloads\\export"
  python scripts/import_helios_csv.py --wipe   # borra tablas BPM+casos+catálogos y recarga

Tras importar, ponga HELIOS_SEED_DEMO=0 para que el bridge no pise con el seed demo.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELIOS = ROOT / "blueprints" / "Helios"
DEFAULT_EXPORT = Path(r"c:\Users\adsanchez\Downloads\export")

if str(HELIOS) not in sys.path:
    sys.path.insert(0, str(HELIOS))

# Orden de carga respetando FKs (nombres = archivo CSV sin .csv = __tablename__)
LOAD_ORDER = [
    "Perfiles_Usuarios",
    "Tipos_Flujos",
    "Tipos_Datos_Complementarios",
    "Documentos",
    "Usuarios",
    "Politicas_Password",
    "Usuarios_Password_Historial",
    "Auditoria_Password",
    "Grupos_Usuarios",
    "Grupos_X_Usuario",
    "Datos_Complementarios",
    "Api_Calls",
    "Api_Parametros",
    "Api_Outputs",
    "Flujos",
    "Etapas",
    "Estados",
    "Estado_Api_Inputs",
    "Estado_Api_Outputs",
    "Transiciones",
    "Api_Reglas",
    "Api_Regla_Condiciones",
    "Dato_Reglas",
    "Dato_Regla_Condiciones",
    "Etapas_X_Grupo",
    "Etapas_X_Documento",
    "Etapas_X_Dato",
    "Clientes",
    "Casos",
    "Casos_Historial",
    "Casos_Documentos",
    "Casos_Datos_Complementarios",
    "Casos_Api_Log",
]

# Borrado en orden inverso (hijos primero)
WIPE_ORDER = list(reversed(LOAD_ORDER))

BOOL_TRUE = {"true", "1", "yes", "y", "si", "sí"}
BOOL_FALSE = {"false", "0", "no", "n", ""}


def _parse_value(raw: str | None):
    if raw is None:
        return None
    s = raw.strip()
    if s == "" or s.upper() == "NULL":
        return None
    low = s.lower()
    if low in BOOL_TRUE:
        return True
    if low in BOOL_FALSE and s != "0":  # "0" puede ser int
        if low in {"false", "no", "n"}:
            return False
    # fechas ISO-ish
    if len(s) >= 19 and s[4] == "-" and (" " in s or "T" in s):
        try:
            return datetime.fromisoformat(s.replace(" ", "T", 1).rstrip("Z"))
        except ValueError:
            pass
    # enteros
    if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
        try:
            return int(s)
        except ValueError:
            pass
    # floats (pero no cédulas con guiones)
    if "." in s and s.replace(".", "", 1).replace("-", "", 1).isdigit():
        try:
            return float(s)
        except ValueError:
            pass
    return s


def _read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        cols = list(reader.fieldnames or [])
        rows = []
        for row in reader:
            rows.append({k: _parse_value(v) for k, v in row.items() if k is not None})
        return cols, rows


def _table_by_name(Base) -> dict[str, object]:
    return {t.name: t for t in Base.metadata.sorted_tables}


def main() -> int:
    ap = argparse.ArgumentParser(description="Importa CSV Helios al motor configurado")
    ap.add_argument("--dir", type=Path, default=DEFAULT_EXPORT, help="Carpeta con los .csv")
    ap.add_argument("--wipe", action="store_true", help="Vaciar tablas antes de cargar")
    ap.add_argument(
        "--copy-to-project",
        action="store_true",
        help="Copia el export a blueprints/Helios/data/export",
    )
    args = ap.parse_args()
    export_dir: Path = args.dir
    if not export_dir.is_dir():
        raise SystemExit(f"No existe carpeta export: {export_dir}")

    os.environ.setdefault("HELIOS_SEED_DEMO", "0")

    from app import models  # noqa: F401
    from app.database import Base, SessionLocal, engine
    from sqlalchemy import text

    Base.metadata.create_all(engine)
    tables = _table_by_name(Base)

    if args.copy_to_project:
        dest = HELIOS / "data" / "export"
        dest.mkdir(parents=True, exist_ok=True)
        import shutil

        for f in export_dir.glob("*.csv"):
            shutil.copy2(f, dest / f.name)
        print(f"Copiado a {dest}")

    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            conn.execute(text("PRAGMA foreign_keys=OFF"))
        if args.wipe:
            for name in WIPE_ORDER:
                t = tables.get(name)
                if t is not None:
                    conn.execute(t.delete())
                    print(f"wipe {name}")
        if engine.dialect.name == "sqlite":
            conn.execute(text("PRAGMA foreign_keys=ON"))

    totals: dict[str, int] = {}
    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            conn.execute(text("PRAGMA foreign_keys=OFF"))
        for name in LOAD_ORDER:
            csv_path = export_dir / f"{name}.csv"
            if not csv_path.is_file():
                print(f"skip {name} (sin archivo)")
                continue
            t = tables.get(name)
            if t is None:
                print(f"skip {name} (sin modelo)")
                continue
            cols, rows = _read_csv(csv_path)
            if not rows:
                print(f"empty {name}")
                totals[name] = 0
                continue
            # Solo columnas que existen en la tabla
            table_cols = {c.name for c in t.columns}
            use_cols = [c for c in cols if c in table_cols]
            if not use_cols:
                print(f"skip {name} (columnas no coinciden: {cols})")
                continue
            payload = [{c: row.get(c) for c in use_cols} for row in rows]
            # SQLite: insertar respetando PKs explícitas
            conn.execute(t.insert(), payload)
            totals[name] = len(payload)
            print(f"ok {name}: {len(payload)}")
        if engine.dialect.name == "sqlite":
            conn.execute(text("PRAGMA foreign_keys=ON"))

    # Sanity
    with SessionLocal() as db:
        from app.models import ApiCall, Caso, Cliente, Flujo, Usuario

        print("---")
        print("Usuarios", db.query(Usuario).count())
        print("Clientes", db.query(Cliente).count())
        print("Flujos", db.query(Flujo).count())
        print("APIs", db.query(ApiCall).count())
        print("Casos", db.query(Caso).count())
        for f in db.query(Flujo).all():
            print(f"  flujo #{f.id}: {f.nombre}")
        for a in db.query(ApiCall).all():
            print(f"  api #{a.id}: {a.nombre} {a.metodo} {a.url}")

    print("\nListo. Defina HELIOS_SEED_DEMO=0 en el entorno antes de reiniciar la app.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
