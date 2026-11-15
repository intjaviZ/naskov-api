from typing import List
from fastapi import APIRouter, Depends, status

from app.controllers.catalogo_controller import CatalogoController
from app.core.dependencies import get_catalogo_controller
from app.dtos.catalogo_cultivos_dto import (
    CultivoCatalogoDTO,
    EscenarioCatalogoDTO,
    CriterioCatalogoDTO,
    RegionCatalogoDTO,
    GlosarioItemDTO,
    ParametrosReferenciaDTO,
    SaludDTO,
    VersionDTO,
)

router = APIRouter(prefix="/v1", tags=["Catálogos y Referencia"])


@router.get(
    "/catalogos/cultivos",
    response_model=List[CultivoCatalogoDTO],
    status_code=status.HTTP_200_OK,
    operation_id="listarCultivos",
    summary="Lista de cultivos con ficha técnica",
)
def listar_cultivos(
    controller: CatalogoController = Depends(get_catalogo_controller),
) -> List[CultivoCatalogoDTO]:
    return controller.listar_cultivos()


@router.get(
    "/catalogos/escenarios",
    response_model=List[EscenarioCatalogoDTO],
    status_code=status.HTTP_200_OK,
    operation_id="listarEscenarios",
    summary="Catálogo de escenarios del piloto",
)
def listar_escenarios(
    controller: CatalogoController = Depends(get_catalogo_controller),
) -> List[EscenarioCatalogoDTO]:
    return controller.listar_escenarios()


@router.get(
    "/catalogos/criterios",
    response_model=List[CriterioCatalogoDTO],
    status_code=status.HTTP_200_OK,
    operation_id="listarCriterios",
    summary="Criterios de evaluación agronómica",
)
def listar_criterios(
    controller: CatalogoController = Depends(get_catalogo_controller),
) -> List[CriterioCatalogoDTO]:
    return controller.listar_criterios()


@router.get(
    "/catalogos/glosario",
    response_model=List[GlosarioItemDTO],
    status_code=status.HTTP_200_OK,
    operation_id="listarGlosario",
    summary="Glosario técnico en lenguaje claro",
)
def listar_glosario(
    controller: CatalogoController = Depends(get_catalogo_controller),
) -> List[GlosarioItemDTO]:
    return controller.listar_glosario()


@router.get(
    "/catalogos/regiones",
    response_model=List[RegionCatalogoDTO],
    status_code=status.HTTP_200_OK,
    operation_id="listarRegionesCatalogo",
    summary="Regiones preparadas con series satelitales",
)
@router.get(
    "/regiones",
    response_model=List[RegionCatalogoDTO],
    status_code=status.HTTP_200_OK,
    operation_id="listarRegiones",
    summary="Regiones preparadas (ruta directa)",
)
def listar_regiones(
    controller: CatalogoController = Depends(get_catalogo_controller),
) -> List[RegionCatalogoDTO]:
    return controller.listar_regiones()


@router.get(
    "/parametros",
    response_model=ParametrosReferenciaDTO,
    status_code=status.HTTP_200_OK,
    operation_id="obtenerParametros",
    summary="Parámetros técnicos de referencia vigentes",
)
def obtener_parametros(
    controller: CatalogoController = Depends(get_catalogo_controller),
) -> ParametrosReferenciaDTO:
    return controller.obtener_parametros()


@router.get(
    "/salud",
    response_model=SaludDTO,
    status_code=status.HTTP_200_OK,
    operation_id="obtenerSalud",
    summary="Estado del servicio y fuentes satelitales (RNF12)",
)
def obtener_salud(
    controller: CatalogoController = Depends(get_catalogo_controller),
) -> SaludDTO:
    return controller.obtener_salud()


@router.get(
    "/version",
    response_model=VersionDTO,
    status_code=status.HTTP_200_OK,
    operation_id="obtenerVersion",
    summary="Versión de API, pipeline y reglas (RNF05)",
)
def obtener_version(
    controller: CatalogoController = Depends(get_catalogo_controller),
) -> VersionDTO:
    return controller.obtener_version()
