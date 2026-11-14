from typing import List, Dict, Any
from pydantic import BaseModel


class CifraTrazabilidadDTO(BaseModel):
    id_cifra: str
    id_evaluacion: str
    etiqueta: str
    valor_mostrado: str
    formula: str
    fuente_datos: str
    pasos_calculo: List[str]
    variables_utilizadas: Dict[str, Any]
