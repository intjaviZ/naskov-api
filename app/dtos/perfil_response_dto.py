from typing import Literal
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

class LluviaMensualDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mes: int = Field(..., ge=1, le=12, description="Número de mes (1-12)")
    mediana_mm: float = Field(..., ge=0.0, description="Mediana de precipitación en mm")
    p10_mm: float = Field(..., ge=0.0, description="Percentil 10 de precipitación en mm")
    p90_mm: float = Field(..., ge=0.0, description="Percentil 90 de precipitación en mm")

class SecuenciaSecaDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    p10: float = Field(..., ge=0.0, description="Días secos consecutivos (p10)")
    p90: float = Field(..., ge=0.0, description="Días secos consecutivos (p90)")

class InicioLluviasDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mediana_fecha: str = Field(..., pattern=r"^\d{2}-\d{2}$", description="Fecha mediana formato MM-DD (ej. '05-18')")
    p10_fecha: str = Field(..., pattern=r"^\d{2}-\d{2}$", description="Fecha temprana formato MM-DD")
    p90_fecha: str = Field(..., pattern=r"^\d{2}-\d{2}$", description="Fecha tardía formato MM-DD")
    rotulo: str = Field(default="contexto de la zona", description="Rótulo de escala")
    no_es_pronostico: bool = Field(default=True, description="Aclara que es histórico y no un pronóstico")

class HeladasDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    aplica: bool = Field(..., description="Si aplica el riesgo de heladas en la zona")
    motivo: str | None = Field(default=None, description="Motivo agronómico cuando no aplica")

    @model_validator(mode="after")
    def validar_motivo(self) -> "HeladasDTO":
        if not self.aplica and not self.motivo:
            raise ValueError("Debes especificar el motivo cuando el riesgo de heladas no aplica")
        return self

class PerfilAgroclimaticoResponseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lluvia_mensual: list[LluviaMensualDTO] | None = Field(default=None, description="Distribución mensual de lluvia")
    secuencia_seca_max_dias: SecuenciaSecaDTO | None = Field(default=None, description="Secuencia seca máxima en días")
    rre: Literal["bajo", "medio", "alto"] | None = Field(default=None, description="Riesgo Relativo de Erosión")
    inicio_lluvias: InicioLluviasDTO | None = Field(default=None, description="Inicio histórico de temporada de lluvias")
    heladas: HeladasDTO | None = Field(default=None, description="Riesgo de heladas en la zona")

    # Metadatos obligatorios de procedencia y trazabilidad
    fuente: str = Field(..., description="Fuente satelital (ej. 'GPM IMERG')")
    resolucion_km: int = Field(..., gt=0, description="Resolución espacial nativa en km")
    anios: int = Field(..., ge=1, description="Años de historial analizados")
    f_val: float = Field(..., ge=0.0, le=1.0, description="Fracción de observaciones válidas en la serie")
    confianza: Literal["alta", "media", "baja", "insuficiente"] = Field(..., description="Nivel de confianza calculado")
    
    version_pipeline: str = Field(..., description="Versión del pipeline de datos")
    id_ejecucion: str = Field(..., description="ID único reproducible de la ejecución")
    version_reglas: str = Field(..., description="Versión del motor de reglas")
    generado_utc: AwareDatetime = Field(..., description="Fecha de cálculo UTC con zona horaria")
    vigencia_hasta: AwareDatetime = Field(..., description="Vigencia de la información UTC con zona horaria")