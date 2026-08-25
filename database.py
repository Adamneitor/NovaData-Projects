"""
Persistencia Nova Projects — SQLite (local) / Postgres (Railway).
Usa DATABASE_URL si existe; si no, sqlite:///instance/nova_projects.db
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash

db = SQLAlchemy()


def database_url() -> str:
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if url:
        # Railway a veces entrega postgres:// (SQLAlchemy 2 exige postgresql://)
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        return url
    base = Path(__file__).resolve().parent
    instance = base / "instance"
    instance.mkdir(exist_ok=True)
    return f"sqlite:///{instance / 'nova_projects.db'}"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    role = db.Column(db.String(40), nullable=False, default="user")
    photo = db.Column(db.String(255), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, nullable=True)

    def to_session_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "photo": self.photo,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }


def init_app(app):
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
    db.init_app(app)


def create_and_seed(app) -> None:
    """Crea tablas e inserta admin si no existe."""
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(
                username="admin",
                password_hash=generate_password_hash("admin"),
                name="Administrator",
                email="admin@novadatasolutions.local",
                role="admin",
                active=True,
            )
            db.session.add(admin)
            db.session.commit()
            print("Seed: usuario admin / admin creado.")
        else:
            print("Seed: admin ya existe.")
        # Diagnóstico
        engine = db.engine
        print(f"BD: {engine.url.render_as_string(hide_password=True)}")
        print(f"Tablas: {inspect(engine).get_table_names()}")
        try:
            n = db.session.execute(text("SELECT COUNT(*) FROM users")).scalar()
            print(f"Usuarios: {n}")
        except Exception as exc:  # noqa: BLE001
            print(f"Aviso conteo users: {exc}")
