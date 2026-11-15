"""
api/domain/motor_calculo.py
Cálculo de los 4 Criterios de Evaluación Agroclimática (c_agua, c_riesgo, c_suelo, c_apt).
Cumple estrictamente con la Sección 5 de la Especificación de Cálculos NasKob.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.domain.modelos_cultivo import CULTIVOS_M1, CultivoAgronomico, calcular_kc_dia

# Días de tolerancia a sequía según tipo de tierra (D_tol) - Sección 5.2
D_TOLERANCIA_TIERRA = {
    "arenosa": 20,
    "negra": 25,
    "arcillosa": 30,
}

# Pesos de suelo según Riesgo Relativo de Erosión (RRE) - Sección 5.3
PESOS_SUELO_RRE = {
    "bajo": {"w_N": 0.500, "w_div": 0.500},
    "medio": {"w_N": 0.625, "w_div": 0.375},
    "alto": {"w_N": 0.700, "w_div": 0.300},
}


# =============================================================================
# 5.1 CRITERIO 1: BALANCE DE AGUA (c_agua)
# =============================================================================
def calcular_c_agua(
    cultivo: CultivoAgronomico,
    perfil: Dict[str, Any],
    riego_veces_semana: int = 0,
) -> Tuple[float, Optional[float]]:
    """
    Calcula el balance hídrico histórico (2001-2025).
    - Para cultivos con riego garantizado (requiere_riego=True y riego_veces_semana >= 1),
      el déficit pluvial no penaliza y se reporta volumen informativo Q_riego (c_agua = 1.0).
    - Para cultivos de temporal, evalúa precipitación efectiva (f_e = 0.75) vs ET_c
      ponderando la etapa crítica con peso w_c = 2.
    Retorna: (c_agua, q_riego_mm)
    """
    cuenta_con_riego = riego_veces_semana > 0

    if cultivo.requiere_riego and cuenta_con_riego:
        # Riego disponible: demanda satisfecha por riego
        q_riego = float(cultivo.ciclo_dias * 5.0)  # ~500-600 mm referencial
        return 1.0, q_riego

    lluvia_anual = perfil.get("lluvia_anual_historica_mm", {})
    lluvia_mensual = perfil.get("lluvia_mensual_climatologia_mm", {})
    anios = list(range(2001, 2026))

    # ET0 promedio diario durante ciclo de temporal en Chiapas (~4.2 mm/día)
    et0_diario_base = float(perfil.get("et0_diaria_mm", 4.2))

    deficits_anuales = []
    l_tot = cultivo.ciclo_dias

    for anio in anios:
        factor_lluvia = float(lluvia_anual.get(str(anio), 1200.0)) / 1200.0

        # Lluvia diaria promedio en los meses de temporal (mayo a octubre ~180 días)
        # 85% de la lluvia anual cae en temporal
        p_diaria_prom = (float(lluvia_anual.get(str(anio), 1200.0)) * 0.85) / 180.0

        # Lluvia efectiva diaria (Pe = 0.75 * P)
        pe_diaria = 0.75 * p_diaria_prom

        sum_pe_crit = 0.0
        sum_etc_crit = 0.0
        sum_pe_resto = 0.0
        sum_etc_resto = 0.0

        v_crit = cultivo.ventana_critica_dias  # (inicio, fin)

        for dia in range(1, l_tot + 1):
            kc_dia = calcular_kc_dia(cultivo, dia)
            etc_dia = kc_dia * et0_diario_base

            # Simulación de variabilidad intra-estival en canícula (días 50 a 90)
            pe_dia_ajustada = pe_diaria
            if 50 <= dia <= 90 and factor_lluvia < 1.0:
                pe_dia_ajustada *= 0.65  # Reducción por canícula en años secos

            if v_crit and v_crit[0] <= dia <= v_crit[1]:
                sum_pe_crit += pe_dia_ajustada
                sum_etc_crit += etc_dia
            else:
                sum_pe_resto += pe_dia_ajustada
                sum_etc_resto += etc_dia

        if v_crit and sum_etc_crit > 0:
            dr_crit = max(0.0, 1.0 - (sum_pe_crit / max(1e-5, sum_etc_crit)))
            dr_resto = max(0.0, 1.0 - (sum_pe_resto / max(1e-5, sum_etc_resto)))
            # Déficit ponderado en etapa crítica con peso w_c = 2 (Sección 5.1)
            dr_pond = (2.0 * dr_crit + dr_resto) / 3.0
        else:
            sum_pe_total = sum_pe_crit + sum_pe_resto
            sum_etc_total = sum_etc_crit + sum_etc_resto
            dr_pond = max(0.0, 1.0 - (sum_pe_total / max(1e-5, sum_etc_total)))

        deficits_anuales.append(dr_pond)

    dr_medio = float(np.mean(deficits_anuales)) if deficits_anuales else 0.20
    c_agua = max(0.0, min(1.0, 1.0 - dr_medio))

    # Si un cultivo exige riego y el agricultor declaró 0 riegos, severa penalización
    if cultivo.requiere_riego and not cuenta_con_riego:
        c_agua = round(min(c_agua, 0.20), 4)
        return c_agua, None

    return round(c_agua, 4), None


# =============================================================================
# 5.2 CRITERIO 2: RESILIENCIA A EXTREMOS CLIMÁTICOS (c_riesgo)
# =============================================================================
def calcular_c_riesgo(
    cultivo: CultivoAgronomico,
    perfil: Dict[str, Any],
    tipo_tierra: str = "negra",
    riego_veces_semana: int = 0,
) -> float:
    """
    Evalúa la resiliencia climática del cultivo en los 25 años históricos:
    1. Sequía en ventana crítica (temporal).
    2. Sequía acumulada vs tolerancia de suelo (D_tol_efectivo).
    3. Golpe de calor: anomalía térmica en años extremos vs umbral térmico del cultivo.
    4. Helada: T_min <= 2°C en zonas vulnerables.
    """
    cuenta_con_riego = riego_veces_semana > 0
    d_tol_base = D_TOLERANCIA_TIERRA.get(tipo_tierra.lower(), 25)
    d_tol_efectivo = d_tol_base * cultivo.factor_sequia

    secuencia_seca = perfil.get("secuencia_seca_max_dias", {})
    anios = list(range(2001, 2026))

    # Temperatura máxima media de la temporada de lluvias en Chiapas (29.5 °C en temporal)
    # Se evita el default incorrecto de 33.5 °C que quemaba al frijol (umbral 31 °C)
    t_max_zona = float(perfil.get("temperatura_max_c", perfil.get("temp_media_ciclo_c", 29.5)))
    heladas_info = perfil.get("heladas", {})
    t_min_absoluta = float(heladas_info.get("t_min_absoluta_c", 8.0))
    zona_con_heladas = heladas_info.get("riesgo_heladas") in ["medio", "alto"] or t_min_absoluta <= 2.0

    anios_con_evento_critico = 0

    for anio in anios:
        evento_activo = False
        dias_secos_anio = float(secuencia_seca.get(str(anio), 20.0))

        # 1 y 2. Secuencias secas (se omiten si cuenta con riego)
        if not (cultivo.requiere_riego and cuenta_con_riego):
            if cultivo.ventana_critica_dias and dias_secos_anio >= 22:
                evento_activo = True
            if dias_secos_anio >= d_tol_efectivo:
                evento_activo = True

        # 3. Golpe de calor: la anomalía térmica ocurre en años El Niño o canículas severas (>25 d secos)
        anomalia_calor = 1.8 if (anio in [2009, 2015, 2019, 2023] or dias_secos_anio >= 25) else 0.0
        t_max_anio = t_max_zona + anomalia_calor
        if t_max_anio >= cultivo.umbral_calor_c:
            evento_activo = True

        # 4. Heladas
        if zona_con_heladas and cultivo.sensibilidad_helada == "alta":
            if anio in [2005, 2010, 2017] and t_min_absoluta <= 3.0:
                evento_activo = True

        if evento_activo:
            anios_con_evento_critico += 1

    fraccion_dano = anios_con_evento_critico / max(1, len(anios))
    c_riesgo = max(0.0, min(1.0, 1.0 - fraccion_dano))
    return round(c_riesgo, 4)

# =============================================================================
# 5.3 CRITERIO 3: SUELO Y ROTACIÓN (c_suelo)
# =============================================================================
def calcular_c_suelo(
    historial_3_ciclos: List[str],
    candidato_ciclo_4: str,
    rre: str = "medio",
) -> Tuple[float, float, float]:
    """
    Evalúa la rotación completa de 4 ciclos (3 históricos declarados + Ciclo 4 candidato):
    1. Balance de Nitrógeno (q_N):
       - maiz = 0 (extrae)
       - sandia = 0 (extrae)
       - frijol = 1 (aporta)
       - cacahuate, calabaza, habanero, no_hubo = excluidos del promedio.
       - no_se = maíz (0).
    2. Diversidad Botánica (q_div):
       - Conteo de familias distintas (Poáceas, Fabáceas, Cucurbitáceas, Solanáceas) / 4.
    Retorna: (c_suelo, q_N, q_div)
    """
    rotacion_4 = list(historial_3_ciclos) + [candidato_ciclo_4]

    # 1. Balance de Nitrógeno (q_N)
    valores_n = []
    for c in rotacion_4:
        c_clean = c.lower().strip()
        if c_clean == "no_se":
            c_clean = "maiz"

        if c_clean in ["maiz"]:
            valores_n.append(0.0)
        elif c_clean in ["sandia"]:
            valores_n.append(0.0)
        elif c_clean in ["frijol"]:
            valores_n.append(1.0)
        # cacahuate, calabaza, habanero y no_hubo se excluyen

    if len(valores_n) > 0:
        q_n = float(np.mean(valores_n))
    else:
        q_n = 0.50  # Neutral por defecto si ninguno tiene dato con respaldo

    # 2. Diversidad Botánica (q_div)
    familias = set()
    for c in rotacion_4:
        c_clean = c.lower().strip()
        if c_clean == "no_se":
            c_clean = "maiz"

        if c_clean in CULTIVOS_M1:
            familias.add(CULTIVOS_M1[c_clean].familia_botanica)

    q_div = min(1.0, len(familias) / 4.0)

    # 3. Ponderación final según RRE
    pesos_rre = PESOS_SUELO_RRE.get(rre.lower(), PESOS_SUELO_RRE["medio"])
    w_n = pesos_rre["w_N"]
    w_div = pesos_rre["w_div"]

    c_suelo = (w_n * q_n) + (w_div * q_div)
    return round(c_suelo, 4), round(q_n, 4), round(q_div, 4)


# =============================================================================
# 5.4 CRITERIO 4: APTITUD AGROCLIMÁTICA Y ZONA (c_apt)
# =============================================================================
def calcular_c_apt(
    cultivo: CultivoAgronomico,
    perfil: Dict[str, Any],
    region: str = "frailesca",
) -> Tuple[float, float, float]:
    """
    Evalúa la aptitud agroclimática térmica y de zona común en Chiapas:
    1. Corrección de temperatura por altitud (SRTM + POWER):
       T_corregida = T_POWER - 0.0065 * (z_SRTM - z_POWER).
    2. Aptitud térmica diaria (c_temp): función trapecio comparada con rangos de M1.
    3. Factor de zona común (f_zona): 1.0 si coincide con zona tradicional en Chiapas, 0.5 si no.
    Retorna: (c_apt, c_temp, f_zona)
    """
    altitud_srtm = float(perfil.get("altitud_m", 580.0))
    altitud_power = float(perfil.get("altitud_power_m", altitud_srtm))
    t_power_media = float(perfil.get("temperatura_media_c", 25.5))

    # 1. Corrección adiabática
    t_corregida = t_power_media - 0.0065 * (altitud_srtm - altitud_power)

    # 2. Aptitud térmica (Trapecio)
    opt_min, opt_max = cultivo.temp_optima_c
    util_min, util_max = cultivo.temp_rango_util_c

    if opt_min <= t_corregida <= opt_max:
        c_temp = 1.0
    elif util_min <= t_corregida < opt_min:
        # Interpolación lineal 0.5 -> 1.0
        c_temp = 0.5 + 0.5 * ((t_corregida - util_min) / max(1e-5, (opt_min - util_min)))
    elif opt_max < t_corregida <= util_max:
        # Interpolación lineal 1.0 -> 0.5
        c_temp = 1.0 - 0.5 * ((t_corregida - opt_max) / max(1e-5, (util_max - opt_max)))
    elif t_corregida < util_min:
        # Decae a 0 con margen de 3 °C
        c_temp = max(0.0, 0.5 * (1.0 - (util_min - t_corregida) / 3.0))
    else:
        # Decae a 0 con margen de 3 °C
        c_temp = max(0.0, 0.5 * (1.0 - (t_corregida - util_max) / 3.0))

    # 3. Factor de Zona Común (f_zona)
    reg_norm = region.lower().strip().replace(" ", "_")
    f_zona = 0.5
    for z in cultivo.zonas_comunes:
        if z in reg_norm or reg_norm in z or z in ["chiapas", "todas"]:
            f_zona = 1.0
            break

    c_apt = c_temp * f_zona
    return round(c_apt, 4), round(c_temp, 4), round(f_zona, 4)
