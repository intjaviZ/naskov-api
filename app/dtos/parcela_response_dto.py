from typing import Annotated
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.dtos.declaracion_response_dto import DeclaracionResponseDTO
from app.models.parcela_model import EstadoParcelaEnum

AreaHa = Annotated[float, Field(ge=0.0, allow_inf_nan=False, description="Área en hectáreas.")]


class _RespuestaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ParcelaCreadaResponseDTO(_RespuestaBase):
    id_parcela: UUID = Field(..., description="Identificador opaco de la parcela.")
    area_ha: AreaHa


class ParcelaItemDTO(_RespuestaBase):
    id_parcela: UUID = Field(..., description="Identificador opaco de la parcela.")
    area_ha: AreaHa
    estado: EstadoParcelaEnum = Field(..., description="'registrada' o 'con_declaracion'.")


class ParcelaListaResponseDTO(_RespuestaBase):
    parcelas: list[ParcelaItemDTO] = Field(..., description="Parcelas de la cuenta; puede ir vacía.")
    siguiente_cursor: str | None = Field(
        default=None, description="Cursor de la siguiente página; null si no hay más."
    )


class ParcelaDetalleResponseDTO(_RespuestaBase):
    id_parcela: UUID = Field(..., description="Identificador opaco de la parcela.")
    area_ha: AreaHa
    estado: EstadoParcelaEnum = Field(..., description="'registrada' o 'con_declaracion'.")
    declaracion: DeclaracionResponseDTO | None = Field(
        default=None, description="Declaración vigente; null si todavía no la ha hecho."
    )