from app.services.sesion_service import SesionService
from app.dtos.sesion_create_dto import SesionCreateDTO
from app.dtos.sesion_response_dto import SesionResponseDTO


class SesionController:
    def __init__(self, service: SesionService):
        self.service = service

    async def iniciar_sesion(self, payload: SesionCreateDTO) -> SesionResponseDTO:
        return await self.service.iniciar_sesion(payload)

    async def cerrar_sesion_actual(self, jti: str, id_cuenta: str = "") -> None:
        await self.service.cerrar_sesion(jti, id_cuenta)