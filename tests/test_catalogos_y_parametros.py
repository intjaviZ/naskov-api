import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_catalogos_y_parametros():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-Api-Key": settings.PWA_API_KEY}

        print("\n========================================================")
        print(" INICIANDO PRUEBAS: 3.5 CATÁLOGOS Y REFERENCIA")
        print("========================================================")

        # 1. Test GET /v1/catalogos/cultivos
        res_cultivos = await client.get("/v1/catalogos/cultivos", headers=headers)
        assert res_cultivos.status_code == 200, res_cultivos.text
        data_c = res_cultivos.json()
        assert "cultivos" in data_c
        assert data_c["total"] == 6

        maiz = next(c for c in data_c["cultivos"] if c["id"] == "maiz")
        assert maiz["nombre"] == "Maíz"
        assert maiz["familia"] == "poaceas"
        assert "kc_puntos" in maiz
        assert "origen" in maiz
        # Verificar contrato 4.6 en suelo
        assert "suelo" in maiz
        assert maiz["suelo"]["nitrogeno"] == "extrae"
        assert maiz["suelo"]["cobertura"] is None
        assert maiz["suelo"]["residuos"] is None
        assert maiz["suelo"]["infiltracion"] is None
        print(f"✓ 1. GET /v1/catalogos/cultivos: 200 OK ({data_c['total']} cultivos con ficha, suelo 4.6 y trazabilidad)")

        # 2. Test GET /v1/parametros
        res_param = await client.get("/v1/parametros", headers=headers)
        assert res_param.status_code == 200, res_param.text
        data_p = res_param.json()
        assert data_p["version_reglas"] == "1.2.0"
        assert len(data_p["tolerancia_suelo"]) == 3
        assert len(data_p["pesos_prioridad"]) == 7
        print(f"✓ 2. GET /v1/parametros: 200 OK (Versión {data_p['version_reglas']}, tolerancias y matriz de pesos)")

        print("========================================================")
        print(" ¡TODOS LOS TESTS DE CATÁLOGOS Y PARÁMETROS PASARON! ✓✓")
        print("========================================================\n")
