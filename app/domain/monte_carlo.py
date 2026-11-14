"""
api/domain/monte_carlo.py
Simulación Monte Carlo de robustez y análisis de sensibilidad de pesos (Sección 7).
"""

from typing import Dict, List, Literal, Optional, Tuple
import numpy as np


def ejecutar_monte_carlo(
    criterios_por_escenario: Dict[str, Dict[str, float]],
    pesos_base: Dict[str, float],
    n_replicas: int = 1000,
    seed: int = 42,
) -> Dict[str, Dict[str, Any]]:
    """
    Ejecuta 1,000 réplicas perturbando los pesos +/- 20% con distribución uniforme:
    w'_k = w_k * Uniforme(0.8, 1.2), renormalizados a 1.0.

    Calcula:
    - puntaje_mediana: mediana de los puntajes en las réplicas
    - puntaje_p10: percentil 10
    - puntaje_p90: percentil 90
    - fraccion_primer_lugar (R_s): porcentaje de réplicas donde el escenario fue el #1
    - robustez: "consistente" (>= 0.70), "sensible" (0.40 <= R_s < 0.70), o "baja_consistencia" (< 0.40)
    """
    rng = np.random.default_rng(seed)
    nombres_criterios = ["c_agua", "c_riesgo", "c_suelo", "c_apt"]
    w_vec = np.array([pesos_base.get(c, 0.25) for c in nombres_criterios], dtype=float)

    # Códigos de escenarios (ej. ["A", "B", "C", "D"])
    codigos = list(criterios_por_escenario.keys())
    if not codigos:
        return {}

    # Matriz de criterios: filas = escenarios, columnas = 4 criterios
    matriz_criterios = []
    for cod in codigos:
        c_dict = criterios_por_escenario[cod]
        matriz_criterios.append([c_dict.get(c, 0.5) for c in nombres_criterios])
    matriz_criterios = np.array(matriz_criterios)  # Shape: (E, 4)

    # Generar perturbaciones: (1000, 4)
    perturbaciones = rng.uniform(0.8, 1.2, size=(n_replicas, 4))
    pesos_replicas = w_vec * perturbaciones  # (1000, 4)
    # Renormalizar cada fila para que sume 1.0
    sumas = pesos_replicas.sum(axis=1, keepdims=True)
    pesos_replicas = pesos_replicas / np.maximum(sumas, 1e-8)

    # Calcular puntajes en todas las réplicas: (E, 4) x (4, 1000) -> (E, 1000)
    puntajes_todas = np.dot(matriz_criterios, pesos_replicas.T)  # Shape: (E, 1000)

    # Identificar qué escenario fue #1 en cada réplica
    ganadores_por_replica = np.argmax(puntajes_todas, axis=0)  # Shape: (1000,)

    resultados_mc: Dict[str, Dict[str, Any]] = {}

    for idx, cod in enumerate(codigos):
        scores_esc = puntajes_todas[idx, :]
        p10 = float(np.percentile(scores_esc, 10))
        p50 = float(np.median(scores_esc))
        p90 = float(np.percentile(scores_esc, 90))

        # Fracción de réplicas como ganador
        victorias = int(np.sum(ganadores_por_replica == idx))
        r_s = victorias / float(n_replicas)

        # Clasificación de robustez según Sección 7
        if r_s >= 0.70:
            etiqueta_robustez = "consistente"
            texto_etiqueta = "Consistente con tus prioridades"
        elif r_s >= 0.40:
            etiqueta_robustez = "sensible"
            texto_etiqueta = "Sensible a cambios"
        else:
            etiqueta_robustez = "baja_consistencia"
            texto_etiqueta = "Variabilidad alta"

        resultados_mc[cod] = {
            "p10": round(p10, 4),
            "mediana": round(p50, 4),
            "p90": round(p90, 4),
            "r_s": round(r_s, 4),
            "robustez": etiqueta_robustez,
            "etiqueta_humana": texto_etiqueta,
        }

    return resultados_mc
