from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import bearer_scheme, validar_api_key, decodificar_token_jwt
from app.core.exceptions import ErroresContrato
from app.core.config import settings

# Repositories
from app.repository.cuenta_repository import CuentaRepository
from app.repository.sesion_repository import SesionRepository
from app.repository.evaluacion_repository import EvaluacionRepository
from app.repository.catalogo_repository import CatalogoRepository

# Services
from app.services.cuenta_service import CuentaService
from app.services.sesion_service import SesionService
from app.services.gemini_service import GeminiService
from app.services.evaluacion_service import EvaluacionService
from app.services.catalogo_service import CatalogoService

# Controllers
from app.controllers.cuenta_controller import CuentaController
from app.controllers.sesion_controller import SesionController
from app.controllers.evaluacion_controller import EvaluacionController
from app.controllers.catalogo_controller import CatalogoController


# --- REPOSITORIES CONECTADOS A BASE DE DATOS ---
def get_cuenta_repository(db: AsyncSession = Depends(get_db_session)) -> CuentaRepository:
    return CuentaRepository(db=db)


def get_sesion_repository(db: AsyncSession = Depends(get_db_session)) -> SesionRepository:
    return SesionRepository(db=db)


def get_evaluacion_repository(db: AsyncSession = Depends(get_db_session)) -> EvaluacionRepository:
    return EvaluacionRepository(db=db)


# --- SERVICES ---
def get_gemini_service() -> GeminiService:
    return GeminiService(api_key=settings.GEMINI_API_KEY)


def get_cuenta_service(repo: CuentaRepository = Depends(get_cuenta_repository)) -> CuentaService:
    return CuentaService(repo=repo)


def get_sesion_service(
    cuenta_repo: CuentaRepository = Depends(get_cuenta_repository),
    sesion_repo: SesionRepository = Depends(get_sesion_repository),
) -> SesionService:
    return SesionService(cuenta_repo=cuenta_repo, sesion_repo=sesion_repo)


def get_evaluacion_service(
    repo: EvaluacionRepository = Depends(get_evaluacion_repository),
    gemini_service: GeminiService = Depends(get_gemini_service),
) -> EvaluacionService:
    return EvaluacionService(repo=repo, gemini_service=gemini_service)


# --- CONTROLLERS ---
def get_cuenta_controller(service: CuentaService = Depends(get_cuenta_service)) -> CuentaController:
    return CuentaController(service=service)


def get_sesion_controller(service: SesionService = Depends(get_sesion_service)) -> SesionController:
    return SesionController(service=service)


def get_evaluacion_controller(
    service: EvaluacionService = Depends(get_evaluacion_service),
) -> EvaluacionController:
    return EvaluacionController(service=service)


def get_catalogo_repository() -> CatalogoRepository:
    return CatalogoRepository()


def get_catalogo_service(
    repo: CatalogoRepository = Depends(get_catalogo_repository),
) -> CatalogoService:
    return CatalogoService(repo=repo)


def get_catalogo_controller(
    service: CatalogoService = Depends(get_catalogo_service),
) -> CatalogoController:
    return CatalogoController(service=service)


# --- GUARDIAS DE AUTENTICACIÓN ---
async def obtener_contexto_token(
    _api_key: str = Depends(validar_api_key),
    credenciales: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    cuenta_repo: CuentaRepository = Depends(get_cuenta_repository),
    sesion_repo: SesionRepository = Depends(get_sesion_repository),
) -> dict:
    if not credenciales or credenciales.scheme.lower() != "bearer":
        raise ErroresContrato.no_autenticado()

    payload = decodificar_token_jwt(credenciales.credentials)
    id_cuenta = payload.get("sub")
    jti = payload.get("jti")

    if not id_cuenta or not jti:
        raise ErroresContrato.no_autenticado()

    if await sesion_repo.esta_revocado(jti):
        raise ErroresContrato.no_autenticado("La sesión fue cerrada.")

    cuenta = await cuenta_repo.obtener_por_id(id_cuenta)
    if not cuenta:
        raise ErroresContrato.no_autenticado("La cuenta asociada al token ya no existe.")

    return {"id_cuenta": id_cuenta, "jti": jti}


async def obtener_id_cuenta_actual(
    ctx: dict = Depends(obtener_contexto_token),
) -> str:
    return ctx["id_cuenta"]
