"""Inserta 2,000 clientes dummy realistas en Helios (idempotente por rango de identificaciones)."""

from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from app.database import SessionLocal, engine

NOMBRES = [
    "Juan", "José", "Carlos", "Luis", "Miguel", "Pedro", "Rafael", "Andrés", "Francisco", "Manuel",
    "María", "Ana", "Carmen", "Laura", "Patricia", "Sofía", "Valeria", "Elena", "Diana", "Rosa",
    "Daniel", "David", "Jorge", "Alejandro", "Ricardo", "Fernando", "Héctor", "Óscar", "Iván", "Pablo",
    "Gabriela", "Isabella", "Camila", "Lucía", "Andrea", "Natalia", "Paola", "Karina", "Yolanda", "Claudia",
]
APELLIDOS = [
    "García", "Rodríguez", "Martínez", "Pérez", "González", "Sánchez", "Ramírez", "Torres", "Flores", "Rivera",
    "Gómez", "Díaz", "Cruz", "Morales", "Reyes", "Ortiz", "Gutiérrez", "Ruiz", "Hernández", "Jiménez",
    "Vargas", "Castillo", "Mendoza", "Romero", "Alvarez", "Medina", "Guerrero", "Rojas", "Cabrera", "Peña",
]
DOMINIOS = ["correo.com.do", "email.do", "vimenca-demo.local", "cliente.test"]


def cedula(n: int) -> str:
    # Formato dominicano sintético único: 001-NNNNNNN-C
    cuerpo = 1000000 + n
    check = (cuerpo % 9) + 1
    return f"001-{cuerpo:07d}-{check}"


def telefono(n: int) -> str:
    pref = random.choice(["809", "829", "849"])
    return f"{pref}-{500 + (n % 400):03d}-{1000 + (n % 9000):04d}"


def main(total: int = 2000) -> None:
    random.seed(42)
    with engine.begin() as cn:
        # Índices / migraciones ligeras ya deberían existir vía init_db
        existentes = cn.execute(
            text("SELECT COUNT(*) FROM Clientes WHERE Identificacion LIKE '001-1%'")
        ).scalar()
        if existentes and existentes >= total:
            print(f"Ya hay {existentes} clientes dummy (001-1...). Nada que hacer.")
            return

    filas = []
    for i in range(1, total + 1):
        nom = random.choice(NOMBRES)
        ap1 = random.choice(APELLIDOS)
        ap2 = random.choice(APELLIDOS)
        nombre = f"{nom} {ap1} {ap2}"
        iden = cedula(i)
        mail = f"{nom.lower()}.{ap1.lower()}.{i}@{random.choice(DOMINIOS)}"
        mail = (
            mail.replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
        )
        tipo = "Cedula" if i % 17 else "RNC" if i % 23 == 0 else "Cedula"
        if tipo == "RNC":
            iden = f"1{300000000 + i}"
            nombre = f"{ap1} & {ap2} SRL"
        filas.append(
            {
                "nombre": nombre,
                "tipo": tipo,
                "iden": iden,
                "tel": telefono(i),
                "correo": mail,
            }
        )

    with SessionLocal() as db:
        insertados = 0
        for f in filas:
            existe = db.execute(
                text("SELECT 1 FROM Clientes WHERE Identificacion = :iden"),
                {"iden": f["iden"]},
            ).scalar()
            if existe:
                continue
            db.execute(
                text(
                    """
                    INSERT INTO Clientes (Nombre_Completo, Tipo_Id, Identificacion, Telefono, Correo)
                    VALUES (:nombre, :tipo, :iden, :tel, :correo)
                    """
                ),
                f,
            )
            insertados += 1
            if insertados % 200 == 0:
                db.commit()
                print(f"  … {insertados} insertados")
        db.commit()
        total_db = db.execute(text("SELECT COUNT(*) FROM Clientes")).scalar()
        print(f"Listo. Insertados en esta corrida: {insertados}. Total Clientes: {total_db}")


if __name__ == "__main__":
    main()
