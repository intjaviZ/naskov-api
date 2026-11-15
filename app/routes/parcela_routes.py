from uuid import UUID
from typing import Any, Dict
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
from app.dtos.perfil_response_dto import (
    PerfilAgroclimaticoResponseDTO,
    InicioLluviasDTO,
    HeladasDTO,
)
from app.repository.parcela_repository import ParcelaRepository
from app.services.clima_provider import ProveedorClimaFrailesca
from app.services.parcela_service import ParcelaService, descifrar_geometria
from app.services.perfil_service import (
    DatosInsuficientesError,
    IndicadoresInvalidosError,
    ParcelaNoEncontradaError,
    PerfilService,
)

router = APIRouter(prefix="/v1/parcelas", tags=["Parcelas y perfil"])


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
    name="crearParcela",
    summary="Registra una parcela con polígono (GeoJSON) o punto con radio.",
)
async def crear_parcela(
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
    name="listarParcelas",
    summary="Lista versiones paginadas de parcelas.",
)
async def listar_parcelas(
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
    name="obtenerParcela",
    summary="Devuelve área, estado y región; nunca la geometría.",
)
async def obtener_parcela(
    id_parcela: UUID,
    id_cuenta: str = Depends(obtener_id_cuenta_actual),
    controller: ParcelaController = Depends(get_parcela_controller),
) -> ParcelaDetalleResponseDTO:
    return await controller.obtener_parcela(id_parcela, id_cuenta)


@router.delete(
    "/{id_parcela}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="borrarParcela",
    name="borrarParcela",
    summary="Borra la parcela y sus datos asociados (derecho de borrado).",
)
async def borrar_parcela(
    id_parcela: UUID,
    id_cuenta: str = Depends(obtener_id_cuenta_actual),
    controller: ParcelaController = Depends(get_parcela_controller),
) -> Response:
    await controller.eliminar_parcela(id_parcela, id_cuenta)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Declaraciones (Contrato 3.2) ---


@router.post(
    "/{id_parcela}/declaraciones",
    response_model=DeclaracionActualizadaResponseDTO,
    status_code=status.HTTP_201_CREATED,
    operation_id="crearDeclaracion",
    name="crearDeclaracion",
    summary="Crea una versión nueva con rotación de 3 ciclos, suelo (incluida textura), limitaciones, ganado y pesos.",
)
@router.patch(
    "/{id_parcela}",
    response_model=DeclaracionActualizadaResponseDTO,
    status_code=status.HTTP_200_OK,
    operation_id="guardarDeclaracionLegacy",
    include_in_schema=False,
)
@router.patch(
    "/{id_parcela}/declaracion",
    response_model=DeclaracionActualizadaResponseDTO,
    status_code=status.HTTP_200_OK,
    operation_id="guardarDeclaracionAlias",
    include_in_schema=False,
)
async def crear_declaracion(
    id_parcela: UUID,
    payload: DeclaracionPatchRequestDTO,
    id_cuenta: str = Depends(obtener_id_cuenta_actual),
    controller: ParcelaController = Depends(get_parcela_controller),
) -> DeclaracionActualizadaResponseDTO:
    return await controller.guardar_declaracion(id_parcela, id_cuenta, payload)


# --- Perfil agroclimático (Contrato 3.3) ---


@router.get(
    "/{id_parcela}/perfil",
    response_model=PerfilAgroclimaticoResponseDTO,
    status_code=status.HTTP_200_OK,
    operation_id="obtenerPerfil",
    name="obtenerPerfil",
    summary="Indicadores con valor, p10, p90, tendencia, fuente, resolución, f_val, confianza y nota de escala.",
)
async def obtener_perfil(
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


@router.get(
    "/{id_parcela}/inicio-lluvias",
    response_model=InicioLluviasDTO,
    status_code=status.HTTP_200_OK,
    operation_id="obtenerInicioLluvias",
    name="obtenerInicioLluvias",
    summary="Fecha mediana y rango p10–p90 de inicio de lluvias, rotulado «contexto de la zona», con resolución de la fuente.",
)
async def obtener_inicio_lluvias(
    id_parcela: UUID,
    id_cuenta: str = Depends(obtener_id_cuenta_actual),
    controller: ParcelaController = Depends(get_parcela_controller),
) -> InicioLluviasDTO:
    try:
        perfil = await controller.obtener_perfil(id_parcela, id_cuenta, "inicio_lluvias")
        if not perfil.inicio_lluvias:
            raise ErroresContrato.datos_insuficientes("No se pudo calcular la fecha de inicio de lluvias.")
        return perfil.inicio_lluvias
    except ParcelaNoEncontradaError:
        raise ErroresContrato.no_encontrado("Parcela")
    except DatosInsuficientesError as exc:
        raise ErroresContrato.datos_insuficientes(str(exc))


@router.get(
    "/{id_parcela}/heladas",
    response_model=HeladasDTO,
    status_code=status.HTTP_200_OK,
    operation_id="obtenerHeladas",
    name="obtenerHeladas",
    summary="Indicador de heladas; devuelve aplica: false con motivo cuando no se activa la regla.",
)
async def obtener_heladas(
    id_parcela: UUID,
    id_cuenta: str = Depends(obtener_id_cuenta_actual),
    controller: ParcelaController = Depends(get_parcela_controller),
) -> HeladasDTO:
    try:
        perfil = await controller.obtener_perfil(id_parcela, id_cuenta, "heladas")
        if not perfil.heladas:
            return HeladasDTO(aplica=False, motivo="Región cálida subhúmeda sin registro de heladas")
        return perfil.heladas
    except ParcelaNoEncontradaError:
        raise ErroresContrato.no_encontrado("Parcela")
    except DatosInsuficientesError as exc:
        raise ErroresContrato.datos_insuficientes(str(exc))


@router.get(
    "/{id_parcela}/capas",
    status_code=status.HTTP_200_OK,
    operation_id="obtenerCapas",
    name="obtenerCapas",
    summary="Capas del mapa. Parámetros capa (pendiente, rre, cobertura, lluvia, humedad) y anio.",
)
async def obtener_capas(
    id_parcela: UUID,
    capa: str = Query(default="rre", description="Nombre de la capa geográfica"),
    anio: int | None = Query(default=2024, description="Año de la capa"),
    id_cuenta: str = Depends(obtener_id_cuenta_actual),
    controller: ParcelaController = Depends(get_parcela_controller),
) -> Dict[str, Any]:
    parcela = await controller.obtener_parcela(id_parcela, id_cuenta)
    return {
        "id_parcela": str(id_parcela),
        "region": parcela.region,
        "capa": capa,
        "anio": anio,
        "tipo": "raster_celda_gruesa",
        "resolucion_km": 11,
        "fuente": "NASA POWER / GPM IMERG",
    }
