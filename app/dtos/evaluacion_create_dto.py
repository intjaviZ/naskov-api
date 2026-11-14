from typing import Optional, Dict
from pydantic import BaseModel, Field
from app.dtos.declaracion_create_dto import DeclaracionCreateDTO


class EvaluacionCreateDTO(BaseModel):
    id_declaracion: Optional[str] = Field(
        default=None,
        description="ID de la declaración previa (opcional si se envía declaracion_directa)",
    )
    version_declaracion: int = Field(default=1, ge=1)
    modo_evaluacion: str = Field(
        default="equilibrado",
        description="conservador | equilibrado | arriesgado",
    )
    pesos: Optional[Dict[str, float]] = Field(
        default=None,
        description="Pesos manuales opcionales para los 4 criterios (c_agua, c_riesgo, c_suelo, c_apt)",
    )
    declaracion_directa: Optional[DeclaracionCreateDTO] = Field(
        default=None,
        description="Declaración directa para simulación rápida o evaluación sin persistencia previa",
    )
