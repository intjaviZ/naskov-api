import pytest
from httpx import AsyncClient
from app.core.config import settings


@pytest.mark.asyncio
async def test_flujo_completo_contrato_3_4(async_client: AsyncClient):
    client = async_client
    headers = {"X-Api-Key": settings.PWA_API_KEY}

    # 1. Test Health check
    res_health = await client.get("/health")
    assert res_health.status_code == 200, res_health.text
    print("✓ Health check OK")

    # 2. Test POST /v1/evaluaciones/simular
    payload_sim = {
        "version_declaracion": 1,
        "modo_evaluacion": "equilibrado",
        "declaracion_directa": {
            "rotacion_existente": [
                {"ciclo": 1, "cultivo": "maiz"},
                {"ciclo": 2, "cultivo": "frijol"},
                {"ciclo": 3, "cultivo": "calabaza"},
            ],
            "tipo_tierra": "negra",
            "riego_veces_semana": 0,
            "agrego_productos": False,
            "considerar_riesgo": True,
            "prioridad_principal": "igual",
            "region": "frailesca",
        },
    }

    res_sim = await client.post("/v1/evaluaciones/simular", json=payload_sim, headers=headers)
    assert res_sim.status_code == 200, res_sim.text
    data_sim = res_sim.json()
    assert "escenarios" in data_sim
    assert len(data_sim["escenarios"]) > 0

    # Verificar descarte RC5: sin riego, sandia y habanero deben descartarse
    assert "descartes_rc5" in data_sim
    descartes = [d["cultivo"] for d in data_sim["descartes_rc5"]]
    assert "sandia" in descartes
    assert "habanero" in descartes
    print(f"✓ Simulación directa OK. Descartados RC5: {descartes}")

    # Verificar generación de insights de Gemini en el escenario recomendado (el ganador)
    esc_ganador = next(e for e in data_sim["escenarios"] if not e["es_linea_base"])
    tarjetas_ganador = esc_ganador["tarjetas_informativas"]
    tarjetas_gemini = [t for t in tarjetas_ganador if t["origen"] == "gemini_flash_lite"]
    assert len(tarjetas_gemini) == 2, f"Se esperaban 2 tarjetas Gemini, encontradas: {len(tarjetas_gemini)}"
    print("✓ Gemini Flash Lite generó 2 insights con éxito:")
    for tg in tarjetas_gemini:
        print(f"   [{tg['id_tarjeta']}]: {tg['contenido']}")

    # 3. Test POST /v1/parcelas/{id}/evaluaciones (Persistencia)
    id_parcela = "a8098c1a-f86e-11da-bd1a-00112444be1e"
    res_post = await client.post(
        f"/v1/parcelas/{id_parcela}/evaluaciones",
        json=payload_sim,
        headers=headers,
    )
    assert res_post.status_code == 201, res_post.text
    data_post = res_post.json()
    id_eval = data_post["id_evaluacion"]
    assert id_eval is not None
    print(f"✓ Evaluación creada y persistida con éxito: {id_eval}")

    # 4. Test GET /v1/evaluaciones/{id_evaluacion}
    res_get = await client.get(f"/v1/evaluaciones/{id_eval}", headers=headers)
    assert res_get.status_code == 200, res_get.text
    data_get = res_get.json()
    assert data_get["id_evaluacion"] == id_eval
    assert len(data_get["escenarios"]) == len(data_post["escenarios"])
    print("✓ Consulta GET /v1/evaluaciones/{id} recuperó todos los datos y escenarios")

    # 5. Test GET /v1/evaluaciones/{id_evaluacion}/cifras/{id_cifra}
    res_cifra = await client.get(
        f"/v1/evaluaciones/{id_eval}/cifras/cifra_lluvia_mediana",
        headers=headers,
    )
    assert res_cifra.status_code == 200, res_cifra.text
    data_cifra = res_cifra.json()
    assert data_cifra["id_cifra"] == "cifra_lluvia_mediana"
    assert len(data_cifra["pasos_calculo"]) > 0
    print(f"✓ Trazabilidad RF11 OK: {data_cifra['etiqueta']} = {data_cifra['valor_mostrado']}")


@pytest.mark.asyncio
async def test_evaluacion_sin_declaracion_directa(async_client: AsyncClient):
    """
    Verifica que al evaluar una parcela sin pasar `declaracion_directa` (usando la declaración
    almacenada en BD o la rotación por defecto), no se produzca AttributeError por falta de
    `considerar_riesgo` o `prioridad_principal`.
    """
    client = async_client
    headers = {"X-Api-Key": settings.PWA_API_KEY}
    id_parcela = "b9098c1a-f86e-11da-bd1a-00112444be2f"

    payload = {
        "version_declaracion": 1,
        "modo_evaluacion": "equilibrado",
    }
    res = await client.post(f"/v1/parcelas/{id_parcela}/evaluaciones", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["id_evaluacion"] is not None
    assert len(data["escenarios"]) > 0
    assert "pesos_usados" in data


@pytest.mark.asyncio
async def test_ciclo_base_escenario_a_rotacion(async_client: AsyncClient):
    """
    Verifica que el Escenario A tome como cultivo base el Ciclo 1 (hace 3 ciclos) y NO el último,
    incluso cuando la lista en la petición se envíe en orden no secuencial.
    """
    client = async_client
    headers = {"X-Api-Key": settings.PWA_API_KEY}

    payload = {
        "version_declaracion": 1,
        "modo_evaluacion": "equilibrado",
        "declaracion_directa": {
            "rotacion_existente": [
                {"ciclo": 3, "cultivo": "maiz"},     # Más reciente (hace 1 temporada)
                {"ciclo": 1, "cultivo": "frijol"},   # Inicio de rotación (hace 3 temporadas)
                {"ciclo": 2, "cultivo": "calabaza"}, # Intermedio
            ],
            "tipo_tierra": "negra",
            "riego_veces_semana": 0,
            "agrego_productos": False,
            "considerar_riesgo": True,
            "prioridad_principal": "igual",
            "region": "frailesca",
        },
    }

    res = await client.post("/v1/evaluaciones/simular", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    # Escenario A debe tener como cultivo el del ciclo 1 ("frijol")
    escenario_a = next(e for e in data["escenarios"] if e["es_linea_base"])
    assert escenario_a["cultivo"] == "frijol", f"Se esperaba frijol en Escenario A, obtenido: {escenario_a['cultivo']}"
    assert escenario_a["secuencia_cultivos"] == ["frijol", "calabaza", "maiz", "frijol"]


def test_escenario_orm_sin_columnas_prohibidas():
    """
    Verifica que EscenarioORM cumpla R4, RN-TAR-07 y RN-IA-06:
    NO debe tener columnas con kg/ha ni probabilidades, y SÍ debe tener métricas normalizadas.
    """
    from app.models.escenario_model import EscenarioORM
    columnas = EscenarioORM.__table__.columns.keys()

    # Columnas prohibidas
    assert "rendimiento_esperado_kg_ha" not in columnas
    assert "ic_inferior_kg_ha" not in columnas
    assert "ic_superior_kg_ha" not in columnas
    assert "probabilidad_exito_pct" not in columnas

    # Columnas correctas
    assert "puntaje_mediana" in columnas
    assert "puntaje_p10" in columnas
    assert "puntaje_p90" in columnas
    assert "robustez" in columnas


def test_gemini_service_sanitizacion_y_fallback():
    """
    Verifica que GeminiService limpie palabras prohibidas (RN-IA-04) y devuelva
    plantilla determinista segura si ocurre un fallo.
    """
    from app.services.gemini_service import GeminiService
    service = GeminiService(api_key="clave-invalida-para-forzar-fallback")

    # 1. Sanitización de texto prohibido
    texto_con_prohibidas = "El cultivo garantiza una cosecha óptima y producirá altos ingresos asegurando rendimiento."
    texto_limpio = service._sanitizar_texto_ia(texto_con_prohibidas)
    assert "garantiza" not in texto_limpio.lower()
    assert "producirá" not in texto_limpio.lower()

    # 2. Fallback determinista automático ante fallo
    t1, t2 = service.generar_insights(
        cultivo_propuesto="frijol",
        secuencia_4_ciclos=["maiz", "maiz", "maiz", "frijol"],
        tipo_tierra="negra",
        riego_veces_semana=0,
        prioridad_principal="igual",
        puntaje_global=0.75,
        criterios={"c_agua": 0.8, "c_riesgo": 0.7, "c_suelo": 0.9, "c_apt": 0.8},
    )
    assert t1.contenido is not None and len(t1.contenido) > 10
    assert t2.contenido is not None and len(t2.contenido) > 10
    assert t1.origen == "gemini_flash_lite"
    assert "garantiza" not in t1.contenido.lower()
    assert "producirá" not in t1.contenido.lower()
