from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
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
