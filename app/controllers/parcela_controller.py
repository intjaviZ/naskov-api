from uuid import UUID
from app.dtos.declaracion_create_dto import DeclaracionPatchRequestDTO
from app.dtos.declaracion_response_dto import DeclaracionActualizadaResponseDTO
from app.dtos.parcela_create_dto import ParcelaCreateDTO
from app.dtos.parcela_response_dto import (
    ParcelaCreadaResponseDTO,
    ParcelaDetalleResponseDTO,
    ParcelaListaResponseDTO,
)
from app.dtos.perfil_response_dto import PerfilAgroclimaticoResponseDTO
from app.services.parcela_service import ParcelaService
from app.services.perfil_service import PerfilService


class ParcelaController:
    def __init__(self, parcela_service: ParcelaService, perfil_service: PerfilService) -> None:
        self._parcela_service = parcela_service
        self._perfil_service = perfil_service

    async def crear_parcela(
        self, payload: ParcelaCreateDTO, id_cuenta: str
    ) -> ParcelaCreadaResponseDTO:
        return await self._parcela_service.registrar_parcela(payload, id_cuenta)

    async def listar_parcelas(
        self, id_cuenta: str, limite: int, cursor: str | None
    ) -> ParcelaListaResponseDTO:
        return await self._parcela_service.listar_parcelas(id_cuenta, limite, cursor)

    async def obtener_parcela(
        self, id_parcela: UUID, id_cuenta: str
    ) -> ParcelaDetalleResponseDTO:
        return await self._parcela_service.obtener_parcela(id_parcela, id_cuenta)

    async def guardar_declaracion(
        self, id_parcela: UUID, id_cuenta: str, payload: DeclaracionPatchRequestDTO
    ) -> DeclaracionActualizadaResponseDTO:
        return await self._parcela_service.guardar_declaracion(id_parcela, id_cuenta, payload)

    async def eliminar_parcela(self, id_parcela: UUID, id_cuenta: str) -> None:
        await self._parcela_service.eliminar_parcela(id_parcela, id_cuenta)

    async def obtener_perfil(
        self, id_parcela: UUID, id_cuenta: str, indicadores: str | None
    ) -> PerfilAgroclimaticoResponseDTO:
        lista_indicadores = [i.strip() for i in indicadores.split(",")] if indicadores else None
        return await self._perfil_service.obtener_perfil(id_parcela, id_cuenta, lista_indicadores)