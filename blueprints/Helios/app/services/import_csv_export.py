"""Importa blueprints/Helios/data/export/*.csv si la BD BPM está vacía.

Usado por init_helios_db / helios_bridge para que Railway y local
vean el dump del .bak sin depender de HELIOS_DATABASE_URL accidental.
"""
from __future__ import annotations

import csv
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

HELIOS_ROOT = Path(__file__).resolve().parents[2]  # blueprints/Helios
DEFAULT_EXPORT = HELIOS_ROOT / "data" / "export"

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

BOOL_TRUE = {"true", "1", "yes", "y", "si", "sí"}
BOOL_FALSE = {"false", "no", "n"}


def should_import_csv() -> bool:
    """Importar CSV empaquetado salvo opt-out explícito HELIOS_IMPORT_CSV=0."""
    flag = os.getenv("HELIOS_IMPORT_CSV", "").strip().lower()
    if flag in {"0", "false", "no"}:
        return False
    if flag in {"1", "true", "yes"}:
        return True
    return (DEFAULT_EXPORT / "Flujos.csv").is_file()


def _parse_value(raw: str | None):
    if raw is None:
        return None
    s = raw.strip()
    if s == "" or s.upper() == "NULL":
        return None
    low = s.lower()
    if low in BOOL_TRUE:
        return True
    if low in BOOL_FALSE:
        return False
    if len(s) >= 19 and s[4] == "-" and (" " in s or "T" in s):
        try:
            return datetime.fromisoformat(s.replace(" ", "T", 1).rstrip("Z"))
        except ValueError:
            pass
    if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
        try:
            return int(s)
        except ValueError:
            pass
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
        rows = [{k: _parse_value(v) for k, v in row.items() if k is not None} for row in reader]
        return cols, rows


def try_import_bundled_csv(*, force: bool = False) -> dict[str, int]:
    """Carga CSV empaquetado si no hay flujos (BPM vacío) o force=True."""
    from app.database import Base, engine

    export_dir = Path(os.getenv("HELIOS_CSV_DIR", str(DEFAULT_EXPORT)))
    if not (export_dir / "Flujos.csv").is_file():
        print(f"[helios_csv] sin export en {export_dir}")
        return {}

    Base.metadata.create_all(engine)
    tables = {t.name: t for t in Base.metadata.sorted_tables}

    with engine.connect() as conn:
        n_flujos = conn.execute(text("SELECT COUNT(*) FROM Flujos")).scalar() or 0
    if n_flujos > 0 and not force:
        print(f"[helios_csv] omitido: ya hay {n_flujos} flujo(s)")
        return {}

    totals: dict[str, int] = {}
    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            conn.execute(text("PRAGMA foreign_keys=OFF"))
        if force and n_flujos > 0:
            for name in reversed(LOAD_ORDER):
                t = tables.get(name)
                if t is not None:
                    conn.execute(t.delete())
        for name in LOAD_ORDER:
            csv_path = export_dir / f"{name}.csv"
            t = tables.get(name)
            if not csv_path.is_file() or t is None:
                continue
            cols, rows = _read_csv(csv_path)
            if not rows:
                totals[name] = 0
                continue
            table_cols = {c.name for c in t.columns}
            use_cols = [c for c in cols if c in table_cols]
            if not use_cols:
                continue
            payload = [{c: row.get(c) for c in use_cols} for row in rows]
            conn.execute(t.insert(), payload)
            totals[name] = len(payload)
            print(f"[helios_csv] {name}: {len(payload)}")
        if engine.dialect.name == "sqlite":
            conn.execute(text("PRAGMA foreign_keys=ON"))

    print(
        f"[helios_csv] import OK · Flujos={totals.get('Flujos', 0)} "
        f"Casos={totals.get('Casos', 0)} Clientes={totals.get('Clientes', 0)}"
    )
    return totals
