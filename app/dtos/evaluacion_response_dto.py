from datetime import datetime
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from app.dtos.escenario_tarjeta_dto import EscenarioDetalleDTO


class EvaluacionResponseDTO(BaseModel):
    id_evaluacion: str
    id_parcela: Optional[str] = None
    id_declaracion: Optional[str] = None
    generado_utc: datetime
    vigencia_hasta: datetime
    pesos_usados: Dict[str, float]
    respuestas_snapshot: Optional[Dict[str, Any]] = None
    escenarios: List[EscenarioDetalleDTO]
    descartes_rc5: Optional[List[Dict[str, Any]]] = None


class SensibilidadRequestDTO(BaseModel):
    variante: Literal["mas_seco", "mas_calido", "secuencia_seca_adicional"] = Field(
        default="mas_seco",
        description="Escenario de estrés histórico para reevaluación",
    )


class SensibilidadResponseDTO(BaseModel):
    id_evaluacion: str
    variante: str
    aviso_legal: str = Field(
        default="Reevaluación sobre el historial satelital, no pronóstico climático",
        description="Aviso de no-predicción (R4 y RF13)",
    )
    ajuste_puntajes: Dict[str, float]
    confianza: str = "media"


class TextosIAResponseDTO(BaseModel):
    id_evaluacion: str
    version_ia: str = "gemini-2.5-flash-lite"
    textos_por_escenario: Dict[str, Any]
    aviso_apoyo: str = "Esta herramienta apoya tu decisión; no sustituye el criterio técnico en campo."


class ExportacionRequestDTO(BaseModel):
    formato: Literal["json", "csv", "pdf"] = Field(default="json", description="Formato de exportación")


class ExportacionResponseDTO(BaseModel):
    id_evaluacion: str
    formato: str
    resumen: Dict[str, Any]
    generado_utc: datetime

