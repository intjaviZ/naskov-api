from app.services.cuenta_service import CuentaService
from app.dtos.cuenta_create_dto import CuentaCreateDTO
from app.dtos.cuenta_response_dto import CuentaResponseDTO


class CuentaController:
    def __init__(self, service: CuentaService):
        self.service = service

    async def crear_cuenta(self, payload: CuentaCreateDTO) -> CuentaResponseDTO:
        return await self.service.registrar_cuenta(payload)

    async def eliminar_cuenta(self, id_cuenta: str) -> None:
        await self.service.borrar_cuenta_actual(id_cuenta)