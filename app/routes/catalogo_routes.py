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
    EjecucionDTO,
)

router = APIRouter(prefix="/v1", tags=["Catálogos y Referencia"])


@router.get(
    "/catalogos/cultivos",
    response_model=List[CultivoCatalogoDTO],
    status_code=status.HTTP_200_OK,
    operation_id="listarCultivos",
    name="listarCultivos",
    summary="Lista de cultivos con ficha: atributos cualitativos, familia, riego externo requerido, plagas de suelo conocidas, citas y fecha de consulta.",
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
    name="listarEscenarios",
    summary="Catálogo del piloto (B a E) con intención y límite declarado.",
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
    name="listarCriterios",
    summary="Criterios activos, descripción y condición de activación (forraje solo con ganado).",
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
    name="listarGlosario",
    summary="Términos con explicación de 25 palabras o menos e identificador de ilustración.",
)
def listar_glosario(
    controller: CatalogoController = Depends(get_catalogo_controller),
) -> List[GlosarioItemDTO]:
    return controller.listar_glosario()


@router.get(
    "/regiones",
    response_model=List[RegionCatalogoDTO],
    status_code=status.HTTP_200_OK,
    operation_id="listarRegiones",
    name="listarRegiones",
    summary="Regiones preparadas, con zona de proyección y temporada.",
)
@router.get(
    "/catalogos/regiones",
    response_model=List[RegionCatalogoDTO],
    status_code=status.HTTP_200_OK,
    operation_id="listarRegionesCatalogo",
    include_in_schema=False,
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
    name="obtenerParametros",
    summary="Parámetros de referencia vigentes con versión y rango de sensibilidad.",
)
def obtener_parametros(
    controller: CatalogoController = Depends(get_catalogo_controller),
) -> ParametrosReferenciaDTO:
    return controller.obtener_parametros()


@router.get(
    "/ejecuciones/{id_ejecucion}",
    response_model=EjecucionDTO,
    status_code=status.HTTP_200_OK,
    operation_id="obtenerEjecucion",
    name="obtenerEjecucion",
    summary="Versión de código, configuración, dependencias y fuentes con hash de la ejecución.",
)
def obtener_ejecucion(
    id_ejecucion: str,
    controller: CatalogoController = Depends(get_catalogo_controller),
) -> EjecucionDTO:
    return controller.obtener_ejecucion(id_ejecucion)


@router.get(
    "/salud",
    response_model=SaludDTO,
    status_code=status.HTTP_200_OK,
    operation_id="obtenerSalud",
    name="obtenerSalud",
    summary="Estado del servicio y de las fuentes (para la estrategia de degradación).",
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
    name="obtenerVersion",
    summary="Versión de la API, del pipeline y de las reglas.",
)
def obtener_version(
    controller: CatalogoController = Depends(get_catalogo_controller),
) -> VersionDTO:
    return controller.obtener_version()
