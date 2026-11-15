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
