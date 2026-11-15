from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.parcela_controller import ParcelaController
from app.core.database import get_db_session
from app.core.dependencies import obtener_id_cuenta_actual
from app.core.exceptions import ErroresContrato
from app.dtos.declaracion_create_dto import DeclaracionPatchRequestDTO
from app.dtos.declaracion_response_dto import DeclaracionActualizadaResponseDTO
from app.dtos.parcela_create_dto import ParcelaCreateDTO
from app.dtos.parcela_response_dto import (
    ParcelaCreadaResponseDTO,
    ParcelaDetalleResponseDTO,
    ParcelaListaResponseDTO,
)
from app.dtos.perfil_response_dto import PerfilAgroclimaticoResponseDTO
from app.repository.parcela_repository import ParcelaRepository
from app.services.clima_provider import ProveedorClimaFrailesca
from app.services.parcela_service import ParcelaService, descifrar_geometria
from app.services.perfil_service import (
    DatosInsuficientesError,
    IndicadoresInvalidosError,
    ParcelaNoEncontradaError,
    PerfilService,
)

router = APIRouter(prefix="/v1/parcelas", tags=["Parcelas"])

def get_parcela_controller(db: AsyncSession = Depends(get_db_session)) -> ParcelaController:
    repo = ParcelaRepository(db)
    parcela_service = ParcelaService(repo)
    clima_provider = ProveedorClimaFrailesca()
    perfil_service = PerfilService(
        parcelas=repo,
        clima=clima_provider,
        descifrar_geometria=descifrar_geometria,
        version_reglas="1.2.0",
    )
    return ParcelaController(parcela_service, perfil_service)

@router.post(
    "",
    response_model=ParcelaCreadaResponseDTO,
    status_code=status.HTTP_201_CREATED,
    operation_id="crearParcela",
)
async def crear_parcela_endpoint(
    payload: ParcelaCreateDTO,
    id_cuenta: str = Depends(obtener_id_cuenta_actual),
    controller: ParcelaController = Depends(get_parcela_controller),
) -> ParcelaCreadaResponseDTO:
    return await controller.crear_parcela(payload, id_cuenta)

@router.get(
    "",
    response_model=ParcelaListaResponseDTO,
    status_code=status.HTTP_200_OK,
    operation_id="listarParcelas",
)
async def listar_parcelas_endpoint(
    limite: int = Query(default=10, ge=1, le=100, description="Número de parcelas por página"),
    cursor: str | None = Query(default=None, description="Cursor opaco para la siguiente página"),
    id_cuenta: str = Depends(obtener_id_cuenta_actual),
    controller: ParcelaController = Depends(get_parcela_controller),
) -> ParcelaListaResponseDTO:
    return await controller.listar_parcelas(id_cuenta, limite, cursor)


@router.get(
    "/{id_parcela}",
    response_model=ParcelaDetalleResponseDTO,
    status_code=status.HTTP_200_OK,
    operation_id="obtenerParcela",
)
async def obtener_parcela_endpoint(
    id_parcela: UUID,
    id_cuenta: str = Depends(obtener_id_cuenta_actual),
    controller: ParcelaController = Depends(get_parcela_controller),
) -> ParcelaDetalleResponseDTO:
    return await controller.obtener_parcela(id_parcela, id_cuenta)


@router.patch(
    "/{id_parcela}",
    response_model=DeclaracionActualizadaResponseDTO,
    status_code=status.HTTP_200_OK,
    operation_id="guardarDeclaracion",
)
@router.patch(
    "/{id_parcela}/declaracion",
    response_model=DeclaracionActualizadaResponseDTO,
    status_code=status.HTTP_200_OK,
    operation_id="guardarDeclaracionAlias",
    include_in_schema=False,
)
async def guardar_declaracion_endpoint(
    id_parcela: UUID,
    payload: DeclaracionPatchRequestDTO,
    id_cuenta: str = Depends(obtener_id_cuenta_actual),
    controller: ParcelaController = Depends(get_parcela_controller),
) -> DeclaracionActualizadaResponseDTO:
    return await controller.guardar_declaracion(id_parcela, id_cuenta, payload)


@router.delete(
    "/{id_parcela}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="eliminarParcela",
)
async def eliminar_parcela_endpoint(
    id_parcela: UUID,
    id_cuenta: str = Depends(obtener_id_cuenta_actual),
    controller: ParcelaController = Depends(get_parcela_controller),
) -> Response:
    await controller.eliminar_parcela(id_parcela, id_cuenta)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get(
    "/{id_parcela}/perfil",
    response_model=PerfilAgroclimaticoResponseDTO,
    status_code=status.HTTP_200_OK,
    operation_id="obtenerPerfilAgroclimatico",
)
async def obtener_perfil_endpoint(
    id_parcela: UUID,
    indicadores: str | None = Query(
        default=None,
        description="Subconjunto de indicadores separados por coma (ej. 'lluvia_mensual,heladas')",
    ),
    id_cuenta: str = Depends(obtener_id_cuenta_actual),
    controller: ParcelaController = Depends(get_parcela_controller),
) -> PerfilAgroclimaticoResponseDTO:
    try:
        return await controller.obtener_perfil(id_parcela, id_cuenta, indicadores)
    except ParcelaNoEncontradaError:
        raise ErroresContrato.no_encontrado("Parcela")
    except IndicadoresInvalidosError as exc:
        raise ErroresContrato.solicitud_invalida(str(exc), "indicadores")
    except DatosInsuficientesError as exc:
        raise ErroresContrato.datos_insuficientes(str(exc))