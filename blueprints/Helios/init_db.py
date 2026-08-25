"""Crea las tablas en la base de datos Helios y carga los datos semilla."""

from app import models  # noqa: F401  (registra los modelos)
from app.database import Base, SessionLocal, engine
from app.migrate import migrate
from app.seed import seed


def main() -> None:
    Base.metadata.create_all(engine)
    print("Tablas creadas/verificadas.")
    migrate()
    with SessionLocal() as db:
        seed(db)
    print("Datos semilla cargados. Usuario inicial: admin / admin")


if __name__ == "__main__":
    main()
