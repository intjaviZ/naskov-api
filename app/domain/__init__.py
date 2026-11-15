"""Módulo de Dominio: Reglas agronómicas, ponderaciones, 4 criterios y Monte Carlo."""

from app.domain.modelos_cultivo import CULTIVOS_M1, CultivoAgronomico, calcular_kc_dia
from app.domain.ponderaciones import resolver_pesos_oficiales, calcular_puntaje_global
from app.domain.motor_calculo import (
    calcular_c_agua,
    calcular_c_riesgo,
    calcular_c_suelo,
    calcular_c_apt,
)
from app.domain.monte_carlo import ejecutar_monte_carlo
from app.domain.tarjetas import (
    TarjetaInformativa,
    Tarjeta5Partes,
    generar_tarjetas_deterministas,
    ensamblar_tarjeta_5_partes,
)
from app.domain.series_nasa import cargar_serie_nasa
