import uuid
from datetime import datetime, timezone
from app.core.exceptions import ErroresContrato
from app.core.security import hashear_contrasena
from app.repository.cuenta_repository import CuentaRepository
from app.models.cuenta_model import CuentaORM
from app.dtos.cuenta_create_dto import CuentaCreateDTO
from app.dtos.cuenta_response_dto import CuentaResponseDTO


class CuentaService:
    def __init__(self, repo: CuentaRepository):
        self.repo = repo

    async def registrar_cuenta(self, dto: CuentaCreateDTO) -> CuentaResponseDTO:
        correo_norm = dto.correo.lower().strip()
        existente = await self.repo.obtener_por_correo(correo_norm)
        if existente:
            raise ErroresContrato.correo_ya_registrado()

        nueva_cuenta = CuentaORM(
            id_cuenta=str(uuid.uuid4()),
            correo=correo_norm,
            contrasena_hash=hashear_contrasena(dto.contrasena),
            creada_utc=datetime.now(timezone.utc),
        )
        creada = await self.repo.crear(nueva_cuenta)
        return CuentaResponseDTO(id_cuenta=creada.id_cuenta)

    async def borrar_cuenta_actual(self, id_cuenta: str) -> None:
        await self.repo.eliminar_en_cascada(id_cuenta)