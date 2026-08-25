"""Inicializa BD Helios (Postgres en Railway / SQLite / SQL Server)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELIOS = ROOT / "blueprints" / "Helios"
sys.path.insert(0, str(HELIOS))

from app import models  # noqa: E402, F401
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.migrate import migrate  # noqa: E402
from app.seed import seed  # noqa: E402


def main() -> None:
    print(f"Helios engine: {engine.url}")
    Base.metadata.create_all(engine)
    print("Tablas Helios creadas/verificadas.")
    try:
        migrate()
    except Exception as exc:  # noqa: BLE001
        print(f"migrate (opcional): {exc}")
    with SessionLocal() as db:
        seed(db)
    print("Seed Helios OK · usuario admin / admin")


if __name__ == "__main__":
    main()
