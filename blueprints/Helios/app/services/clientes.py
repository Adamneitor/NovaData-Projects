"""Búsqueda escalable de clientes para autocomplete (banca / 100k–1M+)."""

from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Cliente


def _normalizar_q(q: str) -> str:
    return re.sub(r"\s+", " ", (q or "").strip())


def _escape_like(valor: str) -> str:
    return valor.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def buscar_clientes(
    db: Session,
    q: str,
    *,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    Búsqueda paginada con ranking bancario:
      1) Identificación exacta
      2) Prefijo de identificación (usa índice unique)
      3) Prefijo de nombre (índice nonclustered)
      4) Prefijo correo / contiene teléfono normalizado

    Usa OFFSET/FETCH. page_size máximo 50 para autocomplete.
    """
    page = max(1, page)
    page_size = min(max(1, page_size), 50)
    offset = (page - 1) * page_size
    qn = _normalizar_q(q)

    if len(qn) < 2:
        return {"total": 0, "page": page, "page_size": page_size, "items": []}

    like_prefix = _escape_like(qn) + "%"
    like_contains = "%" + _escape_like(qn) + "%"
    # Teléfono: solo dígitos para matchear 809-555 vs 809555
    digitos = re.sub(r"\D", "", qn)
    like_tel = "%" + digitos + "%" if len(digitos) >= 3 else None

    # Ranking + filtro. NO usar LIKE '%x%' en Identificacion/Nombre cuando hay prefijo —
    # el OR con teléfono/correo es secundario y limitado.
    sql = text(
        """
        WITH base AS (
            SELECT
                c.Cod_CL AS id,
                c.Nombre_Completo AS nombre_completo,
                c.Tipo_Id AS tipo_identificacion,
                c.Identificacion AS identificacion,
                c.Telefono AS telefono,
                c.Correo AS correo,
                CASE
                    WHEN c.Identificacion = :q_exact THEN 0
                    WHEN c.Identificacion LIKE :like_prefix ESCAPE '\\' THEN 1
                    WHEN REPLACE(REPLACE(c.Identificacion, '-', ''), ' ', '')
                         LIKE REPLACE(REPLACE(:q_exact, '-', ''), ' ', '') + '%' THEN 2
                    WHEN c.Nombre_Completo COLLATE Latin1_General_CI_AI LIKE :like_prefix ESCAPE '\\' THEN 3
                    WHEN c.Correo COLLATE Latin1_General_CI_AI LIKE :like_prefix ESCAPE '\\' THEN 4
                    WHEN :like_tel IS NOT NULL
                         AND REPLACE(REPLACE(REPLACE(ISNULL(c.Telefono,''), '-', ''), ' ', ''), '(', '')
                             LIKE :like_tel THEN 5
                    WHEN c.Nombre_Completo COLLATE Latin1_General_CI_AI LIKE :like_contains ESCAPE '\\' THEN 6
                    ELSE 9
                END AS rank_score
            FROM Clientes c
            WHERE
                c.Identificacion LIKE :like_prefix ESCAPE '\\'
                OR REPLACE(REPLACE(c.Identificacion, '-', ''), ' ', '')
                   LIKE REPLACE(REPLACE(:q_exact, '-', ''), ' ', '') + '%'
                OR c.Nombre_Completo COLLATE Latin1_General_CI_AI LIKE :like_prefix ESCAPE '\\'
                OR c.Correo COLLATE Latin1_General_CI_AI LIKE :like_prefix ESCAPE '\\'
                OR (
                    :like_tel IS NOT NULL
                    AND REPLACE(REPLACE(REPLACE(ISNULL(c.Telefono,''), '-', ''), ' ', ''), '(', '')
                        LIKE :like_tel
                )
                OR (
                    LEN(:q_exact) >= 4
                    AND c.Nombre_Completo COLLATE Latin1_General_CI_AI LIKE :like_contains ESCAPE '\\'
                )
        )
        SELECT *, COUNT(*) OVER() AS total
        FROM base
        WHERE rank_score < 9
        ORDER BY rank_score, nombre_completo
        OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
        """
    )

    rows = db.execute(
        sql,
        {
            "q_exact": qn,
            "like_prefix": like_prefix,
            "like_contains": like_contains,
            "like_tel": like_tel,
            "offset": offset,
            "limit": page_size,
        },
    ).mappings().all()

    total = int(rows[0]["total"]) if rows else 0
    items = [
        {
            "id": r["id"],
            "nombre_completo": r["nombre_completo"],
            "tipo_identificacion": r["tipo_identificacion"],
            "identificacion": r["identificacion"],
            "telefono": r["telefono"],
            "correo": r["correo"],
            "label": f"{r['nombre_completo']} · {r['identificacion']}",
        }
        for r in rows
    ]
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
