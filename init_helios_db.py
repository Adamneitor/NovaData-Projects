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
        if __import__("os").getenv("HELIOS_SEED_DEMO", "1") != "0":
            try:
                from app.models import Flujo
                from app.services.seed_demo_presentacion import run_seed_demo

                if db.query(Flujo).count() > 0:
                    print("Seed demo omitido: ya hay flujos en BD")
                else:
                    run_seed_demo(db, force=False, with_casos=True)
                    db.commit()
                    print("Seed demo presentación OK")
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                print(f"Seed demo (opcional): {exc}")
    print("Seed Helios OK")


if __name__ == "__main__":
    main()
