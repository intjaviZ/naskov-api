from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.parcela_controller import ParcelaController
from app.core.database import get_db_session
from app.core.dependencies import obtener_id_cuenta_actual
from app.core.exceptions import ErroresContrato
from app.dtos.declaracion_create_dto import DeclaracionCreateDTO
from app.dtos.declaracion_response_dto import DeclaracionResponseDTO
from app.dtos.parcela_create_dto import ParcelaCreateDTO
from app.dtos.parcela_response_dto import (
    ParcelaCreadaResponseDTO,
    ParcelaDetalleResponseDTO,
    ParcelaListaResponseDTO,
)
from app.dtos.perfil_response_dto import PerfilAgroclimaticoResponseDTO
from app.repository.parcela_repository import ParcelaRepository
from app.services.clima_provider import ProveedorClimaImerg
from app.services.parcela_service import ParcelaService, descifrar_geometria
from app.services.perfil_service import (
    DatosInsuficientesError,
    IndicadoresInvalidosError,
    ParcelaNoEncontradaError,
    PerfilService,
)

router = APIRouter(prefix="/v1/parcelas", tags=["Parcelas"])

_ERR_SOLICITUD = {"description": "solicitud_invalida: cuerpo mal formado o valor fuera de rango."}
_ERR_SESION = {"description": "no_autenticado: falta el token de sesión o no es válido."}
_ERR_NO_ENCONTRADA = {"description": "no_encontrado: la parcela no existe o es de otra cuenta."}


def get_parcela_controller(db: AsyncSession = Depends(get_db_session)) -> ParcelaController:
    repo = ParcelaRepository(db)
    perfil_service = PerfilService(
        parcelas=repo,
        clima=ProveedorClimaImerg(),
        descifrar_geometria=descifrar_geometria,
        version_reglas="1.2.0",
    )
    return ParcelaController(ParcelaService(repo), perfil_service)


@router.post(
    "",
    response_model=ParcelaCreadaResponseDTO,
    status_code=status.HTTP_201_CREATED,
    operation_id="crearParcela",
    summary="Registrar una parcela",
    description=(
        "Registra una parcela marcada en el mapa del frontend: polígono GeoJSON o punto con radio. "
        "Debe estar en Chiapas y medir entre 1 y 10 ha. La geometría se guarda cifrada y nunca se devuelve."
    ),
    responses={
        400: _ERR_SOLICITUD,
        401: _ERR_SESION,
        422: {"description": "region_no_preparada o parcela_fuera_de_rango."},
    },
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
    summary="Listar mis parcelas",
    description="Lista paginada por cursor de las parcelas de la cuenta, de la más reciente a la más antigua.",
    responses={400: _ERR_SOLICITUD, 401: _ERR_SESION},
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
    summary="Ver una parcela y su declaración",
    description="Devuelve área, estado y la declaración vigente (null si todavía no la hizo).",
    responses={400: _ERR_SOLICITUD, 401: _ERR_SESION, 404: _ERR_NO_ENCONTRADA},
)
async def obtener_parcela_endpoint(
    id_parcela: UUID,
    id_cuenta: str = Depends(obtener_id_cuenta_actual),
    controller: ParcelaController = Depends(get_parcela_controller),
) -> ParcelaDetalleResponseDTO:
    return await controller.obtener_parcela(id_parcela, id_cuenta)


@router.patch(
    "/{id_parcela}",
    response_model=DeclaracionResponseDTO,
    status_code=status.HTTP_200_OK,
    operation_id="guardarDeclaracion",
    summary="Guardar la declaración del agricultor",
    description=(
        "Guarda o reemplaza la declaración vigente: rotación de 3 ciclos, tipo de tierra, riego (0 a 7), "
        "productos agregados, riesgo y prioridad. Cada guardado sube la versión."
    ),
    responses={400: _ERR_SOLICITUD, 401: _ERR_SESION, 404: _ERR_NO_ENCONTRADA},
)
async def guardar_declaracion_endpoint(
    id_parcela: UUID,
    payload: DeclaracionCreateDTO,
    id_cuenta: str = Depends(obtener_id_cuenta_actual),
    controller: ParcelaController = Depends(get_parcela_controller),
) -> DeclaracionResponseDTO:
    return await controller.guardar_declaracion(id_parcela, id_cuenta, payload)


@router.delete(
    "/{id_parcela}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="eliminarParcela",
    summary="Borrar una parcela",
    description="Borra la parcela y su declaración asociada.",
    responses={400: _ERR_SOLICITUD, 401: _ERR_SESION, 404: _ERR_NO_ENCONTRADA},
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
    summary="Perfil agroclimático de la parcela",
    description=(
        "Indicadores históricos de lluvia calculados con NASA GPM IMERG para la zona de la parcela. "
        "Usa ?indicadores= para pedir solo algunos (lluvia_mensual, secuencia_seca_max_dias, rre, "
        "inicio_lluvias, heladas). rre y heladas pueden venir null si la fuente no los trae."
    ),
    responses={
        400: _ERR_SOLICITUD,
        401: _ERR_SESION,
        404: _ERR_NO_ENCONTRADA,
        422: {"description": "datos_insuficientes: no hay serie histórica suficiente."},
        503: {"description": "fuente_degradada: la fuente satelital no respondió."},
    },
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
        raise ErroresContrato.no_encontrado("Parcela") from None
    except IndicadoresInvalidosError as exc:
        raise ErroresContrato.solicitud_invalida(str(exc), "indicadores") from None
    except DatosInsuficientesError as exc:
        raise ErroresContrato.datos_insuficientes(str(exc)) from None