import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class CatalogoRepository:
    """
    Repositorio de acceso a catálogos oficiales y parámetros de referencia.
    Lee archivos estáticos versionados en datos/catalogos/ y suministra
    parámetros técnicos del motor agronómico.
    """ 

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        if base_dir is None:
            self._base_dir = Path(__file__).resolve().parent.parent.parent
        else:
            self._base_dir = base_dir
        self._catalogos_dir = self._base_dir / "datos" / "catalogos"
        self._cache: Dict[str, Any] = {}

    def _leer_json(self, nombre_archivo: str) -> Any:
        if nombre_archivo in self._cache:
            return self._cache[nombre_archivo]

        ruta = self._catalogos_dir / nombre_archivo
        if not ruta.exists():
            return []

        contenido = json.loads(ruta.read_text(encoding="utf-8"))
        self._cache[nombre_archivo] = contenido
        return contenido

    def listar_cultivos(self) -> List[Dict[str, Any]]:
        return self._leer_json("cultivos.json")

    def listar_escenarios(self) -> List[Dict[str, Any]]:
        return self._leer_json("escenarios.json")

    def listar_criterios(self) -> List[Dict[str, Any]]:
        return self._leer_json("criterios.json")

    def listar_regiones(self) -> List[Dict[str, Any]]:
        return self._leer_json("regiones.json")

    def listar_glosario(self) -> List[Dict[str, Any]]:
        return self._leer_json("glosario.json")

    def obtener_parametros(self) -> Dict[str, Any]:
        return {
            "version_parametros": "param-v1.1-frailesca",
            "es_vigente": True,
            "tolerancia_sequia_tierra": {
                "arcillosa": {"dias": 30, "rango": [20, 35]},
                "negra": {"dias": 25, "rango": [20, 30]},
                "arenosa": {"dias": 20, "rango": [15, 25]},
            },
            "pesos_por_prioridad": {
                "igual": {"agua": 0.25, "riesgo": 0.25, "suelo": 0.25, "aptitud": 0.25},
                "agua": {"agua": 0.40, "riesgo": 0.20, "suelo": 0.20, "aptitud": 0.20},
                "riesgo": {"agua": 0.20, "riesgo": 0.40, "suelo": 0.20, "aptitud": 0.20},
                "suelo": {"agua": 0.20, "riesgo": 0.20, "suelo": 0.40, "aptitud": 0.20},
            },
            "pesos_suelo_rre": {
                "bajo": {"w_N": 0.50, "w_div": 0.50},
                "medio": {"w_N": 0.625, "w_div": 0.375},
                "alto": {"w_N": 0.70, "w_div": 0.30},
            },
            "umbrales_climaticos": {
                "temperatura_base_c": 10.0,
                "umbral_calor_general_c": 35.0,
                "dias_canicula_media": 14,
            },
        }
