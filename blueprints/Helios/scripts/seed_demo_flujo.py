"""
CLI: siembra demo Helios (APIs + flujo + casos).

  python scripts/seed_demo_flujo.py
  python scripts/seed_demo_flujo.py --base-url https://novadata-projects-production.up.railway.app
  python scripts/seed_demo_flujo.py --force
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import SessionLocal  # noqa: E402
from app.services.seed_demo_presentacion import run_seed_demo  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo Helios (flujo + APIs + casos)")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("DEMO_API_BASE_URL"),
        help="URL base de NOVA (/demo-api/*)",
    )
    parser.add_argument("--force", action="store_true", help="Recrea el flujo aunque tenga casos")
    parser.add_argument("--sin-casos", action="store_true", help="No crear casos dummy")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = run_seed_demo(
            db,
            base_url=args.base_url,
            force=args.force,
            with_casos=not args.sin_casos,
        )
        db.commit()
        print("Listo.", result)
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
