from uuid import UUID
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

class DeclaracionActualizadaResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_parcela: UUID = Field(..., description="Identificador opaco de la parcela.")
    declaracion_actualizada_utc: AwareDatetime = Field(
        ..., description="Fecha y hora UTC (ISO 8601) en que se guardó la declaración."
    )