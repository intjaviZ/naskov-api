from typing import Literal, List
from pydantic import BaseModel, Field


class CicloRotacionDTO(BaseModel):
    ciclo: int = Field(..., ge=1, le=3)
    cultivo: str = Field(
        ...,
        description="maiz, frijol, cacahuate, calabaza, sandia, habanero, no_se, no_hubo",
    )


class DeclaracionCreateDTO(BaseModel):
    rotacion_existente: List[CicloRotacionDTO] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Historial exacto de 3 ciclos previos",
        examples=[[
            {"ciclo": 1, "cultivo": "maiz"},
            {"ciclo": 2, "cultivo": "maiz"},
            {"ciclo": 3, "cultivo": "frijol"},
        ]],
    )
    tipo_tierra: Literal["negra", "arcillosa", "arenosa"] = Field(
        default="negra",
        description="Tipo de suelo: negra (25 d), arcillosa (30 d), arenosa (20 d)",
    )
    riego_veces_semana: int = Field(
        default=0,
        ge=0,
        le=7,
        description="Frecuencia de riegos semanales (0 = temporal)",
    )
    agrego_productos: bool = Field(
        default=False,
        description="¿Agregó fertilizantes o agroquímicos al suelo?",
    )
    considerar_riesgo: bool = Field(
        default=True,
        description="¿Incluir criterio de resiliencia a extremos?",
    )
    prioridad_principal: Literal["agua", "riesgo", "suelo", "igual"] = Field(
        default="igual",
        description="Prioridad declarada por el agricultor",
    )
    region: str = Field(
        default="frailesca",
        description="Región o municipio de Chiapas para perfil agroclimático NASA",
    )
