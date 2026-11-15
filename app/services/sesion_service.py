from app.core.exceptions import ErroresContrato
from app.core.security import verificar_contrasena, crear_token_jwt
from app.repository.cuenta_repository import CuentaRepository
from app.repository.sesion_repository import SesionRepository
from app.dtos.sesion_create_dto import SesionCreateDTO
from app.dtos.sesion_response_dto import SesionResponseDTO


class SesionService:
    def __init__(self, cuenta_repo: CuentaRepository, sesion_repo: SesionRepository):
        self.cuenta_repo = cuenta_repo
        self.sesion_repo = sesion_repo

    async def iniciar_sesion(self, dto: SesionCreateDTO) -> SesionResponseDTO:
        correo_norm = dto.correo.lower().strip()
        cuenta = await self.cuenta_repo.obtener_por_correo(correo_norm)
        if not cuenta or not verificar_contrasena(dto.contrasena, cuenta.contrasena_hash):
            raise ErroresContrato.credenciales_invalidas()

        token, _, expira = crear_token_jwt(cuenta.id_cuenta)
        return SesionResponseDTO(token=token, tipo="Bearer", expira_utc=expira)

    async def cerrar_sesion(self, jti: str, id_cuenta: str) -> None:
        await self.sesion_repo.revocar_token(jti, id_cuenta)