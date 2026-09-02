"""Búsqueda escalable de clientes para autocomplete (ORM portátil)."""

from __future__ import annotations

import re

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Cliente


def _normalizar_q(q: str) -> str:
    return re.sub(r"\s+", " ", (q or "").strip())


def _solo_digitos(q: str) -> str:
    return re.sub(r"\D", "", q or "")


def listar_clientes_recientes(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
) -> dict:
    """Listado reciente para el módulo Clientes 360 (sin forzar búsqueda)."""
    page = max(1, page)
    page_size = min(max(1, page_size), 50)
    offset = (page - 1) * page_size
    total = db.query(Cliente).count()
    rows = (
        db.query(Cliente)
        .order_by(Cliente.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [cliente_resumen(c) for c in rows],
        "mode": "recientes",
    }


def buscar_clientes(
    db: Session,
    q: str,
    *,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    Búsqueda paginada (SQLite / Postgres / MSSQL) por:
      - identificación exacta o prefijo (con/sin guiones)
      - nombre, correo, teléfono
    """
    page = max(1, page)
    page_size = min(max(1, page_size), 50)
    offset = (page - 1) * page_size
    qn = _normalizar_q(q)
    digitos = _solo_digitos(qn)

    if len(qn) < 2 and len(digitos) < 3:
        return {"total": 0, "page": page, "page_size": page_size, "items": []}

    filtros = []
    if len(qn) >= 2:
        like = f"%{qn}%"
        pref = f"{qn}%"
        filtros.extend(
            [
                Cliente.identificacion == qn,
                Cliente.identificacion.ilike(pref),
                Cliente.identificacion.ilike(like),
                Cliente.nombre_completo.ilike(like),
                Cliente.correo.ilike(pref),
            ]
        )
    if len(digitos) >= 3:
        filtros.append(Cliente.identificacion.ilike(f"%{digitos}%"))
        filtros.append(Cliente.telefono.ilike(f"%{digitos}%"))

    query = db.query(Cliente).filter(or_(*filtros))
    total = query.count()
    rows = (
        query.order_by(Cliente.nombre_completo)
        .offset(offset)
        .limit(page_size)
        .all()
    )

    # Ranking simple en memoria: exacto > prefijo cédula > resto
    def score(c: Cliente) -> tuple:
        ident = c.identificacion or ""
        ident_d = _solo_digitos(ident)
        if ident == qn or ident_d == digitos:
            return (0, c.nombre_completo)
        if ident.startswith(qn) or (digitos and ident_d.startswith(digitos)):
            return (1, c.nombre_completo)
        return (2, c.nombre_completo)

    rows = sorted(rows, key=score)
    items = [cliente_resumen(c) for c in rows]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


def cliente_resumen(cliente: Cliente) -> dict:
    return {
        "id": cliente.id,
        "nombre_completo": cliente.nombre_completo,
        "tipo_identificacion": cliente.tipo_identificacion,
        "identificacion": cliente.identificacion,
        "telefono": cliente.telefono,
        "correo": cliente.correo,
        "label": f"{cliente.nombre_completo} · {cliente.identificacion}",
    }
