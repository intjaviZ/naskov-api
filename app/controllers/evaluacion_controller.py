from typing import Optional, Dict, Any
from app.services.evaluacion_service import EvaluacionService
from app.dtos.evaluacion_create_dto import EvaluacionCreateDTO
from app.dtos.evaluacion_response_dto import (
    EvaluacionResponseDTO,
    SensibilidadResponseDTO,
    TextosIAResponseDTO,
    ExportacionResponseDTO,
)
from app.dtos.escenario_tarjeta_dto import EscenarioDetalleDTO
from app.dtos.cifra_explicacion_dto import CifraTrazabilidadDTO


class EvaluacionController:
    def __init__(self, service: EvaluacionService):
        self.service = service

    async def evaluar_parcela(
        self,
        id_parcela: str,
        payload: EvaluacionCreateDTO,
        id_cuenta: Optional[str] = None,
    ) -> EvaluacionResponseDTO:
        return await self.service.evaluar_para_parcela(id_parcela, payload, id_cuenta)

    async def simular(self, payload: EvaluacionCreateDTO) -> EvaluacionResponseDTO:
        return await self.service.simular_evaluacion(payload)

    async def obtener_evaluacion(self, id_evaluacion: str) -> EvaluacionResponseDTO:
        return await self.service.obtener_evaluacion_por_id(id_evaluacion)

    async def obtener_escenario(
        self, id_evaluacion: str, id_escenario: str
    ) -> EscenarioDetalleDTO:
        return await self.service.obtener_escenario_por_id(id_evaluacion, id_escenario)

    async def obtener_cifra(self, id_evaluacion: str, id_cifra: str) -> CifraTrazabilidadDTO:
        return await self.service.obtener_cifra_trazabilidad(id_evaluacion, id_cifra)

    async def evaluar_sensibilidad(
        self, id_evaluacion: str, variante: str
    ) -> SensibilidadResponseDTO:
        res = await self.service.evaluar_sensibilidad(id_evaluacion, variante)
        return SensibilidadResponseDTO(**res)

    async def obtener_textos(self, id_evaluacion: str) -> TextosIAResponseDTO:
        res = await self.service.obtener_textos_ia(id_evaluacion)
        return TextosIAResponseDTO(**res)

    async def exportar(
        self, id_evaluacion: str, formato: str = "json"
    ) -> ExportacionResponseDTO:
        res = await self.service.exportar_resumen(id_evaluacion, formato)
        return ExportacionResponseDTO(**res)

