"""
api/domain/modelos_cultivo.py
Fichas y parámetros agronómicos de los 6 cultivos prioritarios en Chiapas (M1).
Basado en Fichas de cultivo NasKob — v0.3 y Especificación de Cálculos Ciclo 4.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class CultivoAgronomico:
    id_cultivo: str
    nombre_comun: str
    nombre_cientifico: str
    familia_botanica: str  # poaceas, fabaceas, cucurbitaceas, solanaceas
    requiere_riego: bool
    riegos_semana_referencia: int
    temp_optima_c: Tuple[float, float]
    temp_rango_util_c: Tuple[float, float]
    ciclo_dias: int
    etapas_dias: Dict[str, int]  # ini, desarrollo, medio, final
    kc: Dict[str, float]  # ini, des, medio, final
    p_fao56: float
    factor_sequia: float  # Multiplica D_tol de la tierra
    ky: Optional[float]
    etapa_critica_nombre: Optional[str]
    ventana_critica_dias: Optional[Tuple[int, int]]  # (inicio, fin) en DDS
    umbral_calor_c: float
    sensibilidad_helada: str  # alta, media, baja
    suelo_nitrogeno: Optional[str]  # extrae (0), aporta (1), None (excluido)
    plagas_suelo: List[str] = field(default_factory=list)
    avisos_tierra: Dict[str, str] = field(default_factory=dict)
    zonas_comunes: List[str] = field(default_factory=list)


# -----------------------------------------------------------------------------
# CATÁLOGO OFICIAL DE 6 CULTIVOS (MATRIZ CHIAPAS M1)
# -----------------------------------------------------------------------------
CULTIVOS_M1: Dict[str, CultivoAgronomico] = {
    "maiz": CultivoAgronomico(
        id_cultivo="maiz",
        nombre_comun="Maíz",
        nombre_cientifico="Zea mays",
        familia_botanica="poaceas",
        requiere_riego=False,
        riegos_semana_referencia=0,
        temp_optima_c=(24.0, 30.0),
        temp_rango_util_c=(18.0, 33.0),
        ciclo_dias=125,
        etapas_dias={"ini": 20, "desarrollo": 35, "medio": 40, "final": 30},
        kc={"ini": 0.40, "des": 0.80, "medio": 1.15, "final": 0.60},
        p_fao56=0.55,
        factor_sequia=1.00,
        ky=1.25,
        etapa_critica_nombre="floración y llenado",
        ventana_critica_dias=(55, 85),
        umbral_calor_c=35.0,
        sensibilidad_helada="alta",
        suelo_nitrogeno="extrae",
        plagas_suelo=["gusano_cogollero", "gallina_ciega", "trozador"],
        avisos_tierra={"arenosa": "pérdida rápida de humedad y de acidez"},
        zonas_comunes=["frailesca", "depresion_central", "altos", "sierra", "norte", "soconusco", "chiapas"],
    ),
    "frijol": CultivoAgronomico(
        id_cultivo="frijol",
        nombre_comun="Frijol",
        nombre_cientifico="Phaseolus vulgaris",
        familia_botanica="fabaceas",
        requiere_riego=False,
        riegos_semana_referencia=0,
        temp_optima_c=(18.0, 24.0),
        temp_rango_util_c=(15.0, 27.0),
        ciclo_dias=110,
        etapas_dias={"ini": 20, "desarrollo": 30, "medio": 40, "final": 20},
        kc={"ini": 0.40, "des": 0.75, "medio": 1.10, "final": 0.50},
        p_fao56=0.45,
        factor_sequia=0.78,  # Factor según especificación 5.2 (o 0.82)
        ky=1.15,
        etapa_critica_nombre="floración y llenado de vaina",
        ventana_critica_dias=(35, 60),
        umbral_calor_c=31.0,
        sensibilidad_helada="alta",
        suelo_nitrogeno="aporta",
        plagas_suelo=[],
        avisos_tierra={"arcillosa": "requiere buen drenaje; revisar encharcamiento"},
        zonas_comunes=["depresion_central", "frailesca", "altos", "norte", "sierra", "chiapas"],
    ),
    "cacahuate": CultivoAgronomico(
        id_cultivo="cacahuate",
        nombre_comun="Cacahuate",
        nombre_cientifico="Arachis hypogaea",
        familia_botanica="fabaceas",
        requiere_riego=False,
        riegos_semana_referencia=0,
        temp_optima_c=(25.0, 30.0),
        temp_rango_util_c=(22.0, 33.0),
        ciclo_dias=130,
        etapas_dias={"ini": 25, "desarrollo": 35, "medio": 45, "final": 25},
        kc={"ini": 0.40, "des": 0.75, "medio": 1.15, "final": 0.60},
        p_fao56=0.50,
        factor_sequia=1.10,  # Factor según nota 5.2.2 (o 0.91)
        ky=0.70,
        etapa_critica_nombre="floración y formación de vaina (clavado)",
        ventana_critica_dias=(40, 85),
        umbral_calor_c=35.0,
        sensibilidad_helada="media",
        suelo_nitrogeno=None,  # Excluido del promedio q_N
        plagas_suelo=[],
        avisos_tierra={
            "arcillosa": "se dificulta el clavado y se pierden vainas al arrancar",
            "arenosa": "ventaja natural de drenaje y facilidad de cosecha",
        },
        zonas_comunes=["depresion_central", "cintalapa", "jiquipilas", "villaflores", "venustiano_carranza", "istmo_costa", "norte", "chiapas"],
    ),
    "calabaza": CultivoAgronomico(
        id_cultivo="calabaza",
        nombre_comun="Calabaza",
        nombre_cientifico="Cucurbita pepo / C. moschata",
        familia_botanica="cucurbitaceas",
        requiere_riego=False,
        riegos_semana_referencia=0,
        temp_optima_c=(20.0, 28.0),
        temp_rango_util_c=(18.0, 32.0),
        ciclo_dias=100,
        etapas_dias={"ini": 20, "desarrollo": 30, "medio": 30, "final": 20},
        kc={"ini": 0.50, "des": 0.80, "medio": 1.00, "final": 0.75},
        p_fao56=0.50,
        factor_sequia=1.00,
        ky=None,
        etapa_critica_nombre=None,
        ventana_critica_dias=None,
        umbral_calor_c=34.5,
        sensibilidad_helada="media",
        suelo_nitrogeno=None,
        plagas_suelo=[],
        avisos_tierra={},
        zonas_comunes=["frailesca", "selva", "altos", "norte", "costa", "chiapas"],
    ),
    "sandia": CultivoAgronomico(
        id_cultivo="sandia",
        nombre_comun="Sandía",
        nombre_cientifico="Citrullus lanatus",
        familia_botanica="cucurbitaceas",
        requiere_riego=True,
        riegos_semana_referencia=3,
        temp_optima_c=(23.0, 28.0),
        temp_rango_util_c=(18.0, 35.0),
        ciclo_dias=80,
        etapas_dias={"ini": 10, "desarrollo": 20, "medio": 20, "final": 30},
        kc={"ini": 0.40, "des": 0.75, "medio": 1.00, "final": 0.75},
        p_fao56=0.40,
        factor_sequia=0.78,  # o 0.73
        ky=1.10,
        etapa_critica_nombre="cuajado y engorde del fruto",
        ventana_critica_dias=(40, 70),
        umbral_calor_c=35.0,
        sensibilidad_helada="alta",
        suelo_nitrogeno="extrae",
        plagas_suelo=["fusarium_y_pudriciones_radiculares"],
        avisos_tierra={"arcillosa": "riesgo de Fusarium y pudriciones radiculares; sensible al exceso de humedad"},
        zonas_comunes=["istmo_costa", "tonala", "pijijiapan", "mapastepec", "soconusco", "frailesca", "villaflores", "valles_centrales", "chiapas"],
    ),
    "habanero": CultivoAgronomico(
        id_cultivo="habanero",
        nombre_comun="Chile habanero",
        nombre_cientifico="Capsicum chinense",
        familia_botanica="solanaceas",
        requiere_riego=True,
        riegos_semana_referencia=3,
        temp_optima_c=(24.0, 30.0),
        temp_rango_util_c=(20.0, 32.0),
        ciclo_dias=120,
        etapas_dias={"ini": 25, "desarrollo": 35, "medio": 40, "final": 20},
        kc={"ini": 0.40, "des": 0.75, "medio": 1.05, "final": 0.85},
        p_fao56=0.30,
        factor_sequia=0.55,
        ky=1.10,
        etapa_critica_nombre=None,
        ventana_critica_dias=None,
        umbral_calor_c=34.0,
        sensibilidad_helada="media",
        suelo_nitrogeno=None,
        plagas_suelo=["phytophthora_capsici"],
        avisos_tierra={
            "arcillosa": "riesgo de Phytophthora capsici por encharcamiento",
            "arenosa": "pérdida rápida de humedad y de acidez",
        },
        zonas_comunes=["selva", "palenque", "ocosingo", "norte", "reforma", "pichucalco", "soconusco", "depresion_central", "chiapas"],
    ),
}


def calcular_kc_dia(cultivo: CultivoAgronomico, dia: int) -> float:
    """
    Interpola el coeficiente de cultivo Kc(d) para el día d del ciclo según
    la curva de 5 nodos especificada en la Matriz M1:
    - Día 0 a Lini: Kc constante = Kc_ini
    - Día Lini a Lini + Ldev/2: transición lineal Kc_ini -> Kc_des
    - Día Lini + Ldev/2 a Lini + Ldev: transición lineal Kc_des -> Kc_med
    - Día Lini + Ldev a Lini + Ldev + Lmid: Kc constante = Kc_med
    - Día Lini + Ldev + Lmid a Ltotal: transición lineal Kc_med -> Kc_fin
    """
    e = cultivo.etapas_dias
    kc = cultivo.kc
    l_ini = e.get("ini", 20)
    l_dev = e.get("desarrollo", 30)
    l_mid = e.get("medio", 40)
    l_fin = e.get("final", 20)
    l_tot = l_ini + l_dev + l_mid + l_fin

    dia_clamped = max(0, min(dia, l_tot))

    n1 = l_ini
    n2 = l_ini + (l_dev / 2.0)
    n3 = l_ini + l_dev
    n4 = l_ini + l_dev + l_mid
    n5 = l_tot

    kc_ini = kc.get("ini", 0.4)
    kc_des = kc.get("des", 0.75)
    kc_med = kc.get("medio", 1.1)
    kc_fin = kc.get("final", 0.6)

    if dia_clamped <= n1:
        return kc_ini
    elif dia_clamped <= n2:
        # Interpolación n1 -> n2 (Kc_ini a Kc_des)
        frac = (dia_clamped - n1) / max(1e-5, (n2 - n1))
        return kc_ini + frac * (kc_des - kc_ini)
    elif dia_clamped <= n3:
        # Interpolación n2 -> n3 (Kc_des a Kc_med)
        frac = (dia_clamped - n2) / max(1e-5, (n3 - n2))
        return kc_des + frac * (kc_med - kc_des)
    elif dia_clamped <= n4:
        return kc_med
    else:
        # Interpolación n4 -> n5 (Kc_med a Kc_fin)
        frac = (dia_clamped - n4) / max(1e-5, (n5 - n4))
        return kc_med + frac * (kc_fin - kc_med)
