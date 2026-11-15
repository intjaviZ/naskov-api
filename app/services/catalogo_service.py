from typing import List
from app.repository.catalogo_repository import CatalogoRepository
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


class CatalogoService:
    def __init__(self, repo: CatalogoRepository) -> None:
        self.repo = repo

    def obtener_cultivos(self) -> List[CultivoCatalogoDTO]:
        datos = self.repo.listar_cultivos()
        return [CultivoCatalogoDTO(**c) for c in datos]

    def obtener_escenarios(self) -> List[EscenarioCatalogoDTO]:
        datos = self.repo.listar_escenarios()
        return [EscenarioCatalogoDTO(**e) for e in datos]

    def obtener_criterios(self) -> List[CriterioCatalogoDTO]:
        datos = self.repo.listar_criterios()
        return [CriterioCatalogoDTO(**cr) for cr in datos]

    def obtener_regiones(self) -> List[RegionCatalogoDTO]:
        datos = self.repo.listar_regiones()
        return [RegionCatalogoDTO(**r) for r in datos]

    def obtener_glosario(self) -> List[GlosarioItemDTO]:
        datos = self.repo.listar_glosario()
        return [GlosarioItemDTO(**g) for g in datos]

    def obtener_parametros(self) -> ParametrosReferenciaDTO:
        datos = self.repo.obtener_parametros()
        return ParametrosReferenciaDTO(**datos)

    def obtener_salud(self) -> SaludDTO:
        return SaludDTO(
            estado="operativo",
            servicio="naskob-api",
            version="1.2.0",
            motor="determinista-multicriterio",
            fuentes={
                "gpm_imerg": "disponible",
                "nasa_power": "disponible",
                "gemini_flash_lite": "operativo",
            },
        )

    def obtener_version(self) -> VersionDTO:
        return VersionDTO(
            api="1.2.0",
            pipeline="2026.11-rc1",
            reglas="v1.1-frailesca-rc5",
            hash_commit="33bc630",
        )

    def obtener_ejecucion(self, id_ejecucion: str) -> EjecucionDTO:
        return EjecucionDTO(
            id_ejecucion=id_ejecucion,
            version_codigo="1.2.0",
            hash_commit="33bc630",
            pipeline="2026.11-rc1",
            version_reglas="v1.1-frailesca-rc5",
        )

