from typing import List
from app.services.catalogo_service import CatalogoService
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


class CatalogoController:
    def __init__(self, service: CatalogoService) -> None:
        self.service = service

    def listar_cultivos(self) -> List[CultivoCatalogoDTO]:
        return self.service.obtener_cultivos()

    def listar_escenarios(self) -> List[EscenarioCatalogoDTO]:
        return self.service.obtener_escenarios()

    def listar_criterios(self) -> List[CriterioCatalogoDTO]:
        return self.service.obtener_criterios()

    def listar_regiones(self) -> List[RegionCatalogoDTO]:
        return self.service.obtener_regiones()

    def listar_glosario(self) -> List[GlosarioItemDTO]:
        return self.service.obtener_glosario()

    def obtener_parametros(self) -> ParametrosReferenciaDTO:
        return self.service.obtener_parametros()

    def obtener_salud(self) -> SaludDTO:
        return self.service.obtener_salud()

    def obtener_version(self) -> VersionDTO:
        return self.service.obtener_version()

    def obtener_ejecucion(self, id_ejecucion: str) -> EjecucionDTO:
        return self.service.obtener_ejecucion(id_ejecucion)

