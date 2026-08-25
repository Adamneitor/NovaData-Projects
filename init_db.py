"""Inicializa BD Nova Projects (local o Railway).

Uso:
  python init_db.py

En Railway (release / one-off):
  python init_db.py
"""
from app import app
from database import create_and_seed

if __name__ == "__main__":
    create_and_seed(app)
    print("Listo.")
