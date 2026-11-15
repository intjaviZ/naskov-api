from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CultivoCatalogoDTO(BaseModel):
    id_cultivo: str
    nombre: str
    familia_botanica: str
    requiere_riego: bool
    riegos_semana_min: int
    sensibilidad_sequia: str
    kc_etapas: Dict[str, float]
    etapa_critica: Dict[str, Any]
    umbral_calor_c: float
    atributos_suelo: Dict[str, str]
    plagas_suelo: List[str]
    cita_bibliografica: str
    fecha_consulta: str
    revision_tecnica: bool


class EscenarioCatalogoDTO(BaseModel):
    codigo: str
    nombre: str
    descripcion: str
    es_linea_base: bool
    orden_visual: int


class CriterioCatalogoDTO(BaseModel):
    id_criterio: str
    nombre: str
    descripcion: str
    activo_por_defecto: bool
    es_opcional: bool


class RegionCatalogoDTO(BaseModel):
    id_region: str
    nombre: str
    estado: str
    pais: str
    municipios: List[str]
    centroide: Dict[str, float]
    zona_utm: str
    elevacion_msnm_rango: List[int]
    precipitacion_anual_media_mm: int
    temperatura_media_c: float
    tipo_tierra_predominante: str


class GlosarioItemDTO(BaseModel):
    termino: str
    definicion: str
    palabras: int
    categoria: str


class ParametrosReferenciaDTO(BaseModel):
    version_parametros: str = Field(default="param-v1.1-frailesca")
    es_vigente: bool = Field(default=True)
    tolerancia_sequia_tierra: Dict[str, Any]
    pesos_por_prioridad: Dict[str, Any]
    pesos_suelo_rre: Dict[str, Any]
    umbrales_climaticos: Dict[str, Any]


class SaludDTO(BaseModel):
    estado: str = Field(default="operativo", description="Estado del servicio (operativo, degradado)")
    servicio: str = Field(default="naskob-api")
    version: str = Field(default="1.2.0")
    motor: str = Field(default="determinista-multicriterio")
    fuentes: Dict[str, str] = Field(
        default_factory=lambda: {
            "gpm_imerg": "disponible",
            "nasa_power": "disponible",
            "gemini_flash_lite": "operativo",
        }
    )


class VersionDTO(BaseModel):
    api: str = Field(default="1.2.0")
    pipeline: str = Field(default="2026.11-rc1")
    reglas: str = Field(default="v1.1-frailesca-rc5")
    hash_commit: str = Field(default="a998005")
