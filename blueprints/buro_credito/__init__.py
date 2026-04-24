"""
Buró de Crédito — Blueprint de demostración para Nova Projects.

Consulta un cliente por cédula y muestra un reporte de crédito generado
a partir de datos de ejemplo (no hay conexión a bases de datos reales).
"""
from .routes import buro_bp

__all__ = ["buro_bp"]
