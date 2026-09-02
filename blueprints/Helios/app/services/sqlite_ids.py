"""Asignación de PKs BigInteger en SQLite (no autoincrementan bien con BIGINT)."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import engine


def next_bigint_id(db: Session, model) -> int | None:
    """Devuelve el próximo id o None si el motor sí autoincrementa (Postgres/MSSQL)."""
    if engine.dialect.name != "sqlite":
        return None
    return int(db.query(func.max(model.id)).scalar() or 0) + 1


def apply_bigint_id(db: Session, model, kwargs: dict) -> dict:
    """Si hace falta, inyecta id en kwargs antes de construir el modelo."""
    nid = next_bigint_id(db, model)
    if nid is not None:
        kwargs = {**kwargs, "id": nid}
    return kwargs
