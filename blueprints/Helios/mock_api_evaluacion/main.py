"""
API mock de evaluación crediticia — independiente de Helios.

Uso:
  uvicorn main:app --host 127.0.0.1 --port 3000 --reload

Token: Bearer test-token-123
"""

from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TOKEN_ESPERADO = "test-token-123"
TASA_USD = 57.5  # referencia aproximada DOP→USD (solo para coherencia)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("mock_evaluacion")

app = FastAPI(
    title="API Mock Evaluación Crediticia",
    description="Servicio de prueba con Bearer Token y respuestas aleatorias.",
    version="1.0.0",
)

security = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class EvaluacionRequest(BaseModel):
    salario: float = Field(..., gt=0, description="Ingreso mensual")
    es_asalariado: bool | int = Field(..., description="1/0 o true/false")
    tiempo_laborando: int | float = Field(..., ge=0, description="Meses laborando")
    cedula: str = Field(..., min_length=5, max_length=20, description="Documento de identidad")

    @property
    def asalariado(self) -> bool:
        if isinstance(self.es_asalariado, bool):
            return self.es_asalariado
        return int(self.es_asalariado) != 0



class EvaluacionResponse(BaseModel):
    Monto_DOP: float
    Monto_USD: float
    Dictamen: Literal["APROBADO", "RECHAZADO"]
    Razon: str


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def require_bearer(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta header Authorization: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if credentials.credentials != TOKEN_ESPERADO:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


# ---------------------------------------------------------------------------
# Generación aleatoria
# ---------------------------------------------------------------------------

RAZONES_APROBADO = [
    "Perfil estable con ingresos consistentes",
    "Historial laboral sólido y capacidad de pago adecuada",
    "Ingresos suficientes para el producto solicitado",
    "Evaluación positiva por antigüedad laboral",
    "Score interno favorable según política vigente",
    "Relación deuda/ingreso dentro de parámetros aceptables",
]

RAZONES_RECHAZADO = [
    "Ingresos insuficientes para el monto evaluado",
    "Antigüedad laboral por debajo del mínimo requerido",
    "Perfil de riesgo elevado según política interna",
    "Inconsistencias detectadas en la información laboral",
    "Capacidad de pago insuficiente tras simulación",
    "No cumple criterios mínimos de elegibilidad",
]


def generar_respuesta(req: EvaluacionRequest) -> EvaluacionResponse:
    """Respuesta distinta en cada llamada; sesgo leve según inputs (sigue siendo aleatorio)."""
    # Semilla por request_id implícito: usamos random del proceso (no fijo)
    rng = random.Random(uuid.uuid4().hex)

    # Sesgo suave: mejor chance de aprobar si asalariado + más tiempo + mejor salario
    score = 0.35
    if req.asalariado:
        score += 0.15
    if float(req.tiempo_laborando) >= 12:
        score += 0.15
    if float(req.tiempo_laborando) >= 36:
        score += 0.10
    if req.salario >= 30000:
        score += 0.10
    if req.salario >= 60000:
        score += 0.10
    score = min(0.85, max(0.20, score))

    dictamen: Literal["APROBADO", "RECHAZADO"] = (
        "APROBADO" if rng.random() < score else "RECHAZADO"
    )

    if dictamen == "APROBADO":
        # Monto correlacionado levemente con salario, pero con rango amplio aleatorio
        base = max(10_000.0, min(500_000.0, req.salario * rng.uniform(1.5, 6.0)))
        monto_dop = round(rng.uniform(max(10_000, base * 0.6), min(500_000, base * 1.4)), 2)
        razon = rng.choice(RAZONES_APROBADO)
    else:
        monto_dop = round(rng.uniform(10_000, 80_000), 2)
        razon = rng.choice(RAZONES_RECHAZADO)

    # Alternar: conversión aproximada O random cercano
    if rng.random() < 0.5:
        monto_usd = round(monto_dop / TASA_USD, 2)
    else:
        monto_usd = round(rng.uniform(150, 9000), 2)

    return EvaluacionResponse(
        Monto_DOP=monto_dop,
        Monto_USD=monto_usd,
        Dictamen=dictamen,
        Razon=razon,
    )


# ---------------------------------------------------------------------------
# Middleware de log
# ---------------------------------------------------------------------------


@app.middleware("http")
async def log_requests(request: Request, call_next):
    req_id = uuid.uuid4().hex[:8]
    started = datetime.now()
    log.info("[%s] → %s %s", req_id, request.method, request.url.path)
    response = await call_next(request)
    ms = (datetime.now() - started).total_seconds() * 1000
    log.info("[%s] ← %s (%.0f ms)", req_id, response.status_code, ms)
    return response


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "mock-evaluacion",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


@app.post("/api/evaluacion", response_model=EvaluacionResponse)
def evaluacion(
    body: EvaluacionRequest,
    _token: Annotated[str, Depends(require_bearer)],
):
    """Evalúa un perfil y devuelve dictamen + montos aleatorios."""
    log.info(
        "Evaluación | cedula=%s salario=%.2f asalariado=%s (%s) tiempo=%s",
        body.cedula,
        body.salario,
        body.asalariado,
        body.es_asalariado,
        body.tiempo_laborando,
    )
    resp = generar_respuesta(body)
    log.info(
        "Resultado | Dictamen=%s Monto_DOP=%.2f Monto_USD=%.2f",
        resp.Dictamen,
        resp.Monto_DOP,
        resp.Monto_USD,
    )
    return resp


@app.get("/")
def root():
    return {
        "mensaje": "API Mock Evaluación — use POST /api/evaluacion con Bearer test-token-123",
        "docs": "/docs",
        "health": "/health",
    }
