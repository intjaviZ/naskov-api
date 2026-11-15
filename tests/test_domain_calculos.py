import pytest
from app.domain.modelos_cultivo import CULTIVOS_M1, CultivoAgronomico
from app.domain.ponderaciones import (
    resolver_pesos_oficiales,
    calcular_puntaje_global,
    MATRIZ_PESOS_OFICIAL,
)
from app.domain.motor_calculo import (
    calcular_c_agua,
    calcular_c_riesgo,
    calcular_c_suelo,
    calcular_c_apt,
)
from app.domain.monte_carlo import ejecutar_monte_carlo
from app.domain.tarjetas import (
    generar_tarjetas_deterministas,
    ensamblar_tarjeta_5_partes,
)


def test_cultivos_catalogo_m1():
    """Verifica que el catálogo contenga exactamente los 6 cultivos oficiales de Chiapas."""
    cultivos_esperados = {"maiz", "frijol", "cacahuate", "calabaza", "sandia", "habanero"}
    assert set(CULTIVOS_M1.keys()) == cultivos_esperados

    # Maíz, frijol, cacahuate y calabaza son de temporal
    assert not CULTIVOS_M1["maiz"].requiere_riego
    assert not CULTIVOS_M1["frijol"].requiere_riego
    assert not CULTIVOS_M1["cacahuate"].requiere_riego
    assert not CULTIVOS_M1["calabaza"].requiere_riego

    # Sandía y habanero requieren riego externo (RC5)
    assert CULTIVOS_M1["sandia"].requiere_riego
    assert CULTIVOS_M1["habanero"].requiere_riego


def test_matriz_ponderaciones_suman_uno():
    """Verifica que todas las configuraciones válidas de la matriz oficial sumen exactamente 1.0."""
    combinaciones_validas = [
        (True, "agua"),
        (True, "riesgo"),
        (True, "suelo"),
        (True, "igual"),
        (False, "agua"),
        (False, "suelo"),
        (False, "igual"),
    ]
    for considerar_riesgo, prioridad in combinaciones_validas:
        pesos = resolver_pesos_oficiales(
            considerar_riesgo=considerar_riesgo,
            prioridad_principal=prioridad,
        )
        assert pytest.approx(sum(pesos.values()), 1e-3) == 1.0
        assert all(w >= 0 for w in pesos.values())

    # Caso contradictorio: no considerar riesgo pero elegir prioridad riesgo -> debe lanzar ValueError
    with pytest.raises(ValueError):
        resolver_pesos_oficiales(considerar_riesgo=False, prioridad_principal="riesgo")


def test_calculo_criterios_individuales():
    """Verifica que cada uno de los 4 criterios se calcule en el rango [0.0, 1.0]."""
    perfil_mock = {
        "precipitacion_anual_mediana_mm": 1250.0,
        "precipitacion_ciclo_p50_mm": 850.0,
        "precipitacion_ciclo_p10_mm": 620.0,
        "p_racha_seca_critica": 0.28,
        "p_exceso_hidrico": 0.15,
        "temp_media_ciclo_c": 26.5,
        "gdd_acumulados_base10": 1950.0,
        "rre": "medio",
    }

    maiz = CULTIVOS_M1["maiz"]

    # 1. Criterio Agua
    c_agua, q_riego = calcular_c_agua(maiz, perfil_mock, riego_veces_semana=0)
    assert 0.0 <= c_agua <= 1.0
    assert q_riego is None or q_riego == 0.0

    # 2. Criterio Riesgo
    c_riesgo = calcular_c_riesgo(maiz, perfil_mock, tipo_tierra="negra", riego_veces_semana=0)
    assert 0.0 <= c_riesgo <= 1.0

    # 3. Criterio Suelo (rotación maiz -> maiz -> frijol -> maiz)
    c_suelo, q_n, q_div = calcular_c_suelo(["maiz", "maiz", "frijol"], "maiz", rre="medio")
    assert 0.0 <= c_suelo <= 1.0
    assert q_n > 0.0  # El ciclo 3 tuvo frijol (leguminosa aportó nitrógeno)

    # 4. Criterio Aptitud
    c_apt, c_temp, f_zona = calcular_c_apt(maiz, perfil_mock, region="frailesca")
    assert 0.0 <= c_apt <= 1.0


def test_rotacion_diversidad_suelo():
    """Verifica que una rotación con aporte de leguminosa y diversidad botánica puntúe mayor en c_suelo que un monocultivo."""
    # Rotación diversa con aporte de nitrógeno (Maíz -> Frijol -> Calabaza) + Frijol
    c_suelo_diverso, q_n_div, q_bot_div = calcular_c_suelo(["maiz", "frijol", "calabaza"], "frijol", rre="medio")

    # Monocultivo continuo de maíz (Maíz -> Maíz -> Maíz) + Maíz
    c_suelo_monocultivo, q_n_mono, q_bot_mono = calcular_c_suelo(["maiz", "maiz", "maiz"], "maiz", rre="medio")

    assert c_suelo_diverso > c_suelo_monocultivo
    assert q_n_div > q_n_mono
    assert q_bot_div > q_bot_mono


def test_simulacion_monte_carlo():
    """Verifica la estabilidad y propiedades de la simulación Monte Carlo de 1,000 réplicas."""
    criterios = {
        "A": {"c_agua": 0.85, "c_riesgo": 0.70, "c_suelo": 0.60, "c_apt": 0.90},
        "B": {"c_agua": 0.75, "c_riesgo": 0.80, "c_suelo": 0.95, "c_apt": 0.88},
    }
    pesos = {"c_agua": 0.3, "c_riesgo": 0.25, "c_suelo": 0.25, "c_apt": 0.20}

    resultados = ejecutar_monte_carlo(criterios, pesos, n_replicas=1000, seed=42)

    for cod in ["A", "B"]:
        res = resultados[cod]
        assert "mediana" in res
        assert "p10" in res
        assert "p90" in res
        # Los percentiles deben guardar orden P10 <= Mediana <= P90
        assert res["p10"] <= res["mediana"] <= res["p90"]
        assert 0.0 <= res["p10"] <= 1.0
        assert 0.0 <= res["p90"] <= 1.0


def test_ensamblar_tarjeta_5_partes():
    """Verifica la estructura y campos de la tarjeta en 5 partes."""
    t5 = ensamblar_tarjeta_5_partes(
        cultivo_nombre="Frijol Negro",
        es_linea_base=False,
        puntaje=0.88,
        criterios={"c_agua": 0.85, "c_riesgo": 0.78, "c_suelo": 0.95, "c_apt": 0.90},
        tipo_tierra="negra",
        agrego_productos=False,
        riego_veces_semana=0,
        advertencias_tierra={"negra": "Suelo con buena retención"},
        gemini_insight_agronomico="Aporte biológico comprobado",
        gemini_insight_resiliencia="Buena resistencia a canícula",
    )
    assert len(t5.por_que_se_sugirio) > 0
    assert len(t5.evidencia_agroclimatica) > 0
    assert len(t5.beneficios_posibles) > 0
    assert len(t5.carencias_informacion) > 0
    assert len(t5.riesgos_revision_local) > 0
    assert "Aporte biológico comprobado" in t5.beneficios_posibles
    assert "Buena resistencia a canícula" in t5.riesgos_revision_local
