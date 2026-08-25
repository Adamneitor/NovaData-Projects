"""Reinicio del ambiente de prueba: borra BPM y conserva usuarios/grupos/clientes."""

import shutil

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import UPLOADS_DIR
from app.database import engine
from app.seed import seed

TABLAS_BPM = [
    "Casos_Api_Log",
    "Casos_Datos_Complementarios",
    "Casos_Documentos",
    "Casos_Historial",
    "Casos",
    "Api_Reglas",
    "Transiciones",
    "Etapas_X_Documento",
    "Etapas_X_Dato",
    "Etapas_X_Grupo",
    "Estados",
    "Etapas",
    "Flujos",
    "Api_Parametros",
    "Api_Outputs",
    "Api_Calls",
    "Datos_Complementarios",
    "Documentos",
    "Tipos_Flujos",
    "Tipos_Datos_Complementarios",
]


def reiniciar_ambiente_prueba(db: Session) -> None:
    with engine.begin() as cn:
        cn.execute(text("EXEC sp_msforeachtable 'ALTER TABLE ? NOCHECK CONSTRAINT ALL'"))
        try:
            for t in TABLAS_BPM:
                cn.execute(text(f"DELETE FROM [{t}]"))
                try:
                    cn.execute(text(f"DBCC CHECKIDENT ('{t}', RESEED, 0)"))
                except Exception:
                    pass
        finally:
            cn.execute(text("EXEC sp_msforeachtable 'ALTER TABLE ? WITH CHECK CHECK CONSTRAINT ALL'"))

    if UPLOADS_DIR.exists():
        for hijo in list(UPLOADS_DIR.iterdir()):
            try:
                if hijo.is_dir():
                    shutil.rmtree(hijo, ignore_errors=True)
                else:
                    hijo.unlink(missing_ok=True)
            except PermissionError:
                pass

    # Restaura tipos de flujo y tipo de dato (usuarios/perfiles ya existen)
    seed(db)
