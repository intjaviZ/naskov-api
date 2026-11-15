from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator
from app.models.declaracion_model import CultivoEnum, PrioridadPrincipalEnum, TipoTierraEnum

NumeroCiclo = Annotated[int, Field(strict=True, ge=1, le=3)]
RiegosPorSemana = Annotated[int, Field(strict=True, ge=0, le=7)]

class _DeclaracionBase(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

class CicloRotacionDTO(_DeclaracionBase):
    ciclo: NumeroCiclo = Field(
        ..., description="Número de ciclo: 1 es el más antiguo y 3 el más reciente."
    )
    cultivo: CultivoEnum = Field(
        ..., description="Cultivo sembrado, o 'no_se' / 'no_hubo' si no hay dato o no hubo siembra."
    )

class SueloDeclaracionDTO(_DeclaracionBase):
    tipo_tierra: TipoTierraEnum = Field(..., description="Tipo de tierra según el agricultor.")
    agrego_productos: bool = Field(
        default=False,
        strict=True,
        description="Si agregó productos al suelo. No entra al puntaje; se guarda como contexto.",
    )


class DeclaracionPayloadDTO(_DeclaracionBase):
    rotacion_existente: list[CicloRotacionDTO] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Los 3 ciclos exactos (1, 2 y 3), sin repetir. Se devuelven ordenados por ciclo.",
    )
    suelo: SueloDeclaracionDTO
    riego_veces_semana: RiegosPorSemana = Field(
        ..., description="Veces por semana que puede regar (0 = solo temporal)."
    )
    considerar_riesgo: bool = Field(
        default=True, strict=True, description="Si quiere que se considere el riesgo del clima."
    )
    prioridad_principal: PrioridadPrincipalEnum = Field(
        default=PrioridadPrincipalEnum.igual, description="Qué le preocupa más al agricultor."
    )

    @field_validator("rotacion_existente")
    @classmethod
    def validar_ciclos(cls, ciclos: list[CicloRotacionDTO]) -> list[CicloRotacionDTO]:
        if {c.ciclo for c in ciclos} != {1, 2, 3}:
            raise ValueError("La rotación debe incluir exactamente los ciclos 1, 2 y 3, sin repetir.")
        return sorted(ciclos, key=lambda c: c.ciclo)

    @field_validator("prioridad_principal")
    @classmethod
    def validar_prioridad_y_riesgo(
        cls, prioridad: PrioridadPrincipalEnum, info: ValidationInfo
    ) -> PrioridadPrincipalEnum:
        if prioridad == PrioridadPrincipalEnum.riesgo and info.data.get("considerar_riesgo", True) is False:
            raise ValueError("La prioridad 'riesgo' solo es válida si 'considerar_riesgo' es verdadero.")
        return prioridad

class DeclaracionPatchRequestDTO(_DeclaracionBase):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "declaracion": {
                        "rotacion_existente": [
                            {"ciclo": 1, "cultivo": "no_se"},
                            {"ciclo": 2, "cultivo": "maiz"},
                            {"ciclo": 3, "cultivo": "maiz"},
                        ],
                        "suelo": {"tipo_tierra": "negra", "agrego_productos": False},
                        "riego_veces_semana": 0,
                        "considerar_riesgo": True,
                        "prioridad_principal": "igual",
                    }
                }
            ]
        }
    )

    declaracion: DeclaracionPayloadDTO