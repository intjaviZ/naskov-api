from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class Tarjeta5PartesDTO(BaseModel):
    por_que_se_sugirio: str
    evidencia_agroclimatica: Union[str, List[str]]
    beneficios_posibles: Union[str, List[str]]
    carencias_informacion: Union[str, List[str]]
    riesgos_revision_local: Union[str, List[str]]


class TarjetaInformativaDTO(BaseModel):
    id_tarjeta: str
    titulo: str
    subtitulo: Optional[str] = None
    tipo: str
    contenido: str
    origen: str
    icono: str
    destacado: bool = False
    tags: List[str] = Field(default_factory=list)


class EscenarioDetalleDTO(BaseModel):
    codigo_escenario: str
    orden_visual: int
    nombre: str
    cultivo: Optional[str] = None
    es_linea_base: bool
    secuencia_cultivos: List[str]
    es_supuesto: bool = False
    ciclos_supuestos: List[int] = Field(default_factory=list)
    confianza: str = "alta"
    puntaje_mediana: Optional[float] = None
    puntaje_p10: Optional[float] = None
    puntaje_p90: Optional[float] = None
    robustez: Optional[str] = None
    etiqueta_robustez: Optional[str] = None
    criterios_detalle: Dict[str, float]
    delta_vs_a: Optional[Dict[str, float]] = None
    tarjeta_5_partes: Tarjeta5PartesDTO
    tarjetas_informativas: Optional[List[TarjetaInformativaDTO]] = None
