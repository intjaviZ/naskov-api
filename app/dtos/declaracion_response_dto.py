from datetime import datetime
from typing import List
from uuid import UUID
from pydantic import BaseModel
from app.dtos.declaracion_create_dto import CicloRotacionDTO


class DeclaracionResponseDTO(BaseModel):
    id_declaracion: str
    id_parcela: str
    version: int
    rotacion_existente: List[CicloRotacionDTO]
    tipo_tierra: str
    riego_veces_semana: int
    agrego_productos: bool
    creada_utc: datetime


class DeclaracionActualizadaResponseDTO(BaseModel):
    id_parcela: UUID
    declaracion_actualizada_utc: datetime
