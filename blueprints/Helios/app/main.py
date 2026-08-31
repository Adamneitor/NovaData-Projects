import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import SECRET_KEY
from app.embed import EmbedMiddleware
from app.routers import admin, apis, auth, casos, catalogos, flujos, platform

app = FastAPI(title="NOVA · Helios BPM")
# Cookie distinta de Flask (`session`) para no pisar el login del portal NOVA
_https = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))
app.add_middleware(EmbedMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="helios_session",
    max_age=8 * 3600,
    same_site="lax",
    https_only=_https,
)
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

app.include_router(platform.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(catalogos.router)
app.include_router(apis.router)
app.include_router(flujos.router)
app.include_router(casos.router)
