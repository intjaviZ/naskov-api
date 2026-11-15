"""
api/domain/ponderaciones.py
Matriz oficial de pesos y ponderaciones multicriterio para el Ciclo 4.
Cumple con la Sección 6 de la Especificación de Cálculos NasKob.
"""

from typing import Dict, Optional


MATRIZ_PESOS_OFICIAL: Dict[tuple[bool, str], Dict[str, float]] = {
    # (considerar_riesgo, prioridad_principal) -> pesos {w_agua, w_riesgo, w_suelo, w_apt}
    (True, "agua"): {"c_agua": 0.40, "c_riesgo": 0.20, "c_suelo": 0.20, "c_apt": 0.20},
    (True, "riesgo"): {"c_agua": 0.20, "c_riesgo": 0.40, "c_suelo": 0.20, "c_apt": 0.20},
    (True, "suelo"): {"c_agua": 0.20, "c_riesgo": 0.20, "c_suelo": 0.40, "c_apt": 0.20},
    (True, "igual"): {"c_agua": 0.25, "c_riesgo": 0.25, "c_suelo": 0.25, "c_apt": 0.25},
    (False, "agua"): {"c_agua": 0.50, "c_riesgo": 0.00, "c_suelo": 0.25, "c_apt": 0.25},
    (False, "suelo"): {"c_agua": 0.25, "c_riesgo": 0.00, "c_suelo": 0.50, "c_apt": 0.25},
    (False, "igual"): {"c_agua": 0.333, "c_riesgo": 0.00, "c_suelo": 0.333, "c_apt": 0.334},
}


def resolver_pesos_oficiales(
    considerar_riesgo: bool = True,
    prioridad_principal: str = "igual",
    pesos_personalizados: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    Determina los 4 pesos oficiales (w_agua, w_riesgo, w_suelo, w_apt)
    según la respuesta declarada por el agricultor (Sección 6).
    Si se envían pesos personalizados válidos, los normaliza.
    """
    if pesos_personalizados and len(pesos_personalizados) > 0:
        # Extraer los 4 criterios
        w_agua = float(pesos_personalizados.get("c_agua", pesos_personalizados.get("agua", 0.25)))
        w_riesgo = float(pesos_personalizados.get("c_riesgo", pesos_personalizados.get("riesgo", 0.25)))
        w_suelo = float(pesos_personalizados.get("c_suelo", pesos_personalizados.get("suelo", 0.25)))
        w_apt = float(pesos_personalizados.get("c_apt", pesos_personalizados.get("aptitud", 0.25)))

        if not considerar_riesgo:
            w_riesgo = 0.0

        total = w_agua + w_riesgo + w_suelo + w_apt
        if total > 0:
            return {
                "c_agua": round(w_agua / total, 4),
                "c_riesgo": round(w_riesgo / total, 4),
                "c_suelo": round(w_suelo / total, 4),
                "c_apt": round(w_apt / total, 4),
            }

    # Validación de regla de consistencia
    prioridad = prioridad_principal.lower().strip()
    if not considerar_riesgo and prioridad == "riesgo":
        raise ValueError(
            "Combinación inválida: no es posible elegir 'riesgo' como prioridad principal "
            "si 'considerar_riesgo' está desactivado (false)."
        )

    clave = (considerar_riesgo, prioridad)
    if clave in MATRIZ_PESOS_OFICIAL:
        return dict(MATRIZ_PESOS_OFICIAL[clave])

    # Fallback neutro
    if considerar_riesgo:
        return {"c_agua": 0.25, "c_riesgo": 0.25, "c_suelo": 0.25, "c_apt": 0.25}
    else:
        return {"c_agua": 0.333, "c_riesgo": 0.00, "c_suelo": 0.333, "c_apt": 0.334}


def calcular_puntaje_global(
    criterios: Dict[str, float],
    pesos: Dict[str, float],
) -> float:
    """
    Calcula el puntaje global ponderado S(s) en el rango [0, 1]:
    S(s) = w_agua * c_agua + w_riesgo * c_riesgo + w_suelo * c_suelo + w_apt * c_apt
    """
    w_agua = pesos.get("c_agua", 0.25)
    w_riesgo = pesos.get("c_riesgo", 0.25)
    w_suelo = pesos.get("c_suelo", 0.25)
    w_apt = pesos.get("c_apt", 0.25)

    c_agua = criterios.get("c_agua", 0.5)
    c_riesgo = criterios.get("c_riesgo", 0.5)
    c_suelo = criterios.get("c_suelo", 0.5)
    c_apt = criterios.get("c_apt", 0.5)

    s = (w_agua * c_agua) + (w_riesgo * c_riesgo) + (w_suelo * c_suelo) + (w_apt * c_apt)
    return round(max(0.0, min(1.0, s)), 4)
