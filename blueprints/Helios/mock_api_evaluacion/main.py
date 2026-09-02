"""
API mock de evaluación crediticia + buró — independiente de Helios.

Uso:
  uvicorn main:app --host 127.0.0.1 --port 3000 --reload

Token: Bearer test-token-123

Endpoints:
  POST /api/evaluacion     → Dictamen APROBADA | REFERIDA | DECLINADA
  POST /api/buro/reporte   → Score, mora, EIC, DictamenBuro
"""

from __future__ import annotations

import hashlib
import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

TOKEN_ESPERADO = "test-token-123"
TASA_USD = 57.5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("mock_evaluacion")

app = FastAPI(
    title="API Mock Helios Demo",
    description="Motor de crédito (APROBADA/REFERIDA/DECLINADA) + Buró de crédito.",
    version="2.0.0",
)

security = HTTPBearer(auto_error=False)

DictamenMotor = Literal["APROBADA", "REFERIDA", "DECLINADA"]


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
    Dictamen: DictamenMotor
    Razon: str


class BuroRequest(BaseModel):
    cedula: str = Field(..., min_length=5, max_length=20)


RAZONES_APROBADA = [
    "Perfil estable con ingresos consistentes",
    "Historial laboral sólido y capacidad de pago adecuada",
    "Ingresos suficientes para el producto solicitado",
    "Evaluación positiva por antigüedad laboral",
    "Score interno favorable según política vigente",
    "Relación deuda/ingreso dentro de parámetros aceptables",
]
RAZONES_REFERIDA = [
    "Requiere revisión de comité por monto solicitado",
    "Score en banda intermedia: validar documentación adicional",
    "Inconsistencia leve en datos laborales: referir a analista",
    "Capacidad de pago borderline: decisión manual recomendada",
    "Cliente con historial mixto: evaluación humana requerida",
]
RAZONES_DECLINADA = [
    "Ingresos insuficientes para el monto evaluado",
    "Antigüedad laboral por debajo del mínimo requerido",
    "Perfil de riesgo elevado según política interna",
    "Capacidad de pago insuficiente tras simulación",
    "No cumple criterios mínimos de elegibilidad",
]

BURO_PROFILES: dict[str, dict[str, Any]] = {
    "00112345678": {
        "Nombre": "Ana María Pérez Rosario",
        "Score": 782,
        "ChanceFavor": 72,
        "ChanceContra": 28,
        "EicMin": 320000.0,
        "EicMax": 780000.0,
        "CuentasAbiertas": 2,
        "CuentasCerradas": 1,
        "MoraMaxDias": 0,
        "DictamenBuro": "OK",
        "Resumen": "Buen historial. Sin atraso vigente. Elegible para originación.",
    },
    "00298765432": {
        "Nombre": "Carlos Enrique Méndez Ruiz",
        "Score": 610,
        "ChanceFavor": 48,
        "ChanceContra": 52,
        "EicMin": 80000.0,
        "EicMax": 220000.0,
        "CuentasAbiertas": 3,
        "CuentasCerradas": 1,
        "MoraMaxDias": 45,
        "DictamenBuro": "ALERTA",
        "Resumen": "Mora histórica reciente. Referir a evaluación manual.",
    },
    "00345678901": {
        "Nombre": "Laura Beatriz Fernández Díaz",
        "Score": 420,
        "ChanceFavor": 22,
        "ChanceContra": 78,
        "EicMin": 0.0,
        "EicMax": 50000.0,
        "CuentasAbiertas": 4,
        "CuentasCerradas": 2,
        "MoraMaxDias": 120,
        "DictamenBuro": "RIESGO",
        "Resumen": "Alto riesgo. Múltiples atrasos. No recomendado sin garantías.",
    },
}


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


def _cedula_limpia(raw: str) -> str:
    return "".join(ch for ch in raw if ch.isdigit())


def generar_respuesta(req: EvaluacionRequest) -> EvaluacionResponse:
    rng = random.Random(uuid.uuid4().hex)

    score = 0.30
    if req.asalariado:
        score += 0.15
    if float(req.tiempo_laborando) >= 12:
        score += 0.12
    if float(req.tiempo_laborando) >= 36:
        score += 0.10
    if req.salario >= 30000:
        score += 0.10
    if req.salario >= 60000:
        score += 0.10
    score = min(0.90, max(0.12, score))

    roll = rng.random()
    if roll < score * 0.55:
        dictamen: DictamenMotor = "APROBADA"
        base = max(15_000.0, min(500_000.0, req.salario * rng.uniform(2.0, 6.5)))
        monto_dop = round(rng.uniform(base * 0.7, min(500_000, base * 1.3)), 2)
        razon = rng.choice(RAZONES_APROBADA)
    elif roll < score * 0.55 + 0.28:
        dictamen = "REFERIDA"
        base = max(10_000.0, min(250_000.0, req.salario * rng.uniform(1.2, 3.5)))
        monto_dop = round(base, 2)
        razon = rng.choice(RAZONES_REFERIDA)
    else:
        dictamen = "DECLINADA"
        monto_dop = round(rng.uniform(10_000, 60_000), 2)
        razon = rng.choice(RAZONES_DECLINADA)

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


def generar_buro(cedula: str) -> dict[str, Any]:
    key = _cedula_limpia(cedula)
    if key in BURO_PROFILES:
        perfil = dict(BURO_PROFILES[key])
    else:
        seed = int(hashlib.sha256(key.encode()).hexdigest()[:12], 16)
        rng = random.Random(seed)
        score = rng.randint(380, 820)
        if score >= 700:
            dictamen, favor = "OK", rng.randint(65, 88)
        elif score >= 550:
            dictamen, favor = "ALERTA", rng.randint(40, 60)
        else:
            dictamen, favor = "RIESGO", rng.randint(15, 35)
        perfil = {
            "Nombre": "Cliente Demo",
            "Score": score,
            "ChanceFavor": favor,
            "ChanceContra": 100 - favor,
            "EicMin": float(rng.randint(0, 150_000)),
            "EicMax": float(rng.randint(150_000, 800_000)),
            "CuentasAbiertas": rng.randint(0, 5),
            "CuentasCerradas": rng.randint(0, 3),
            "MoraMaxDias": 0 if dictamen == "OK" else rng.randint(15, 180),
            "DictamenBuro": dictamen,
            "Resumen": "Reporte sintético generado para demo Helios.",
        }
    venc = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
    return {
        **perfil,
        "Cedula": key,
        "FechaConsulta": datetime.utcnow().strftime("%Y-%m-%d"),
        "FechaVencimiento": venc,
        "Proveedor": "Demo Buró NOVA",
    }


@app.middleware("http")
async def log_requests(request: Request, call_next):
    req_id = uuid.uuid4().hex[:8]
    started = datetime.now()
    log.info("[%s] → %s %s", req_id, request.method, request.url.path)
    response = await call_next(request)
    ms = (datetime.now() - started).total_seconds() * 1000
    log.info("[%s] ← %s (%.0f ms)", req_id, response.status_code, ms)
    return response


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "mock-helios-demo",
        "endpoints": ["/api/evaluacion", "/api/buro/reporte"],
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


@app.post("/api/evaluacion", response_model=EvaluacionResponse)
def evaluacion(
    body: EvaluacionRequest,
    _token: Annotated[str, Depends(require_bearer)],
):
    log.info(
        "Evaluación | cedula=%s salario=%.2f asalariado=%s tiempo=%s",
        body.cedula,
        body.salario,
        body.asalariado,
        body.tiempo_laborando,
    )
    resp = generar_respuesta(body)
    log.info("Resultado | Dictamen=%s Monto_DOP=%.2f", resp.Dictamen, resp.Monto_DOP)
    return resp


@app.post("/api/buro/reporte")
def buro_reporte(
    body: BuroRequest,
    _token: Annotated[str, Depends(require_bearer)],
):
    report = generar_buro(body.cedula)
    log.info(
        "Buró | cedula=%s Score=%s Dictamen=%s",
        report.get("Cedula"),
        report.get("Score"),
        report.get("DictamenBuro"),
    )
    return report


@app.get("/")
def root():
    return {
        "mensaje": "API Mock Helios Demo — Bearer test-token-123",
        "docs": "/docs",
        "health": "/health",
        "motor": "POST /api/evaluacion → APROBADA | REFERIDA | DECLINADA",
        "buro": "POST /api/buro/reporte → Score, Mora, EIC, DictamenBuro",
    }
