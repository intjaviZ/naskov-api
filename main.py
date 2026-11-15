from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from app.core.exceptions import (
    NasKobException,
    naskob_exception_handler,
    validation_exception_handler,
)
from app.routes.cuenta_routes import router as cuenta_router
from app.routes.sesion_routes import router as sesion_router
from app.routes.parcela_routes import router as parcela_router
from app.routes.evaluacion_routes import router as evaluacion_router
from app.services.clima_provider import ProveedorClimaImerg

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await ProveedorClimaImerg.cerrar()

app = FastAPI(
    title="NasKob API",
    version="1.2.0",
    description="Apoyo a la decisión de rotación de cultivos - NASA Space Apps 2026",
    lifespan=lifespan,
)

# Manejadores globales RFC 9457 (application/problem+json)
app.add_exception_handler(NasKobException, naskob_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Registro de rutas del Contrato v1.2 y Contrato 3.4
app.include_router(cuenta_router)
app.include_router(sesion_router)
app.include_router(parcela_router)
app.include_router(evaluacion_router)


@app.get("/health", tags=["Salud"])
async def health_check():
    return {"status": "ok", "app": "NasKob API", "version": "1.2.0"}
