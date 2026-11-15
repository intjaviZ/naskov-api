import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_catalogo_cultivos(async_client: AsyncClient):
    res = await async_client.get("/v1/catalogos/cultivos")
    assert res.status_code == 200, res.text
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 6
    ids = [c["id_cultivo"] for c in data]
    assert "maiz" in ids
    assert "frijol" in ids
    assert "sandia" in ids

    # Validar estructura de ficha técnica agronómica
    maiz = next(c for c in data if c["id_cultivo"] == "maiz")
    assert "kc_etapas" in maiz
    assert "etapa_critica" in maiz
    assert "atributos_suelo" in maiz
    assert "plagas_suelo" in maiz
    assert "gallina_del_suelo" in maiz["plagas_suelo"]


@pytest.mark.asyncio
async def test_catalogo_escenarios(async_client: AsyncClient):
    res = await async_client.get("/v1/catalogos/escenarios")
    assert res.status_code == 200, res.text
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    codigos = [e["codigo"] for e in data]
    assert "A" in codigos
    assert "B" in codigos
    assert "C" in codigos
    assert "D" in codigos
    assert "E" in codigos


@pytest.mark.asyncio
async def test_catalogo_criterios(async_client: AsyncClient):
    res = await async_client.get("/v1/catalogos/criterios")
    assert res.status_code == 200, res.text
    data = res.json()
    assert isinstance(data, list)
    ids = [cr["id_criterio"] for cr in data]
    assert "c_agua" in ids
    assert "c_riesgo" in ids
    assert "c_suelo" in ids


@pytest.mark.asyncio
async def test_catalogo_glosario(async_client: AsyncClient):
    res = await async_client.get("/v1/catalogos/glosario")
    assert res.status_code == 200, res.text
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0
    for item in data:
        assert "termino" in item
        assert "definicion" in item
        # Regla RF14: explicaciones de 25 palabras o menos
        conteo_palabras = len(item["definicion"].split())
        assert conteo_palabras <= 25, f"Término '{item['termino']}' excede 25 palabras ({conteo_palabras})"


@pytest.mark.asyncio
async def test_regiones_y_parametros(async_client: AsyncClient):
    # 1. Regiones
    res_reg = await async_client.get("/v1/regiones")
    assert res_reg.status_code == 200, res_reg.text
    regiones = res_reg.json()
    assert isinstance(regiones, list)
    assert len(regiones) >= 1
    assert regiones[0]["id_region"] == "frailesca"

    # Alias /v1/catalogos/regiones
    res_reg_alias = await async_client.get("/v1/catalogos/regiones")
    assert res_reg_alias.status_code == 200

    # 2. Parámetros de referencia vigentes
    res_param = await async_client.get("/v1/parametros")
    assert res_param.status_code == 200, res_param.text
    param = res_param.json()
    assert param["es_vigente"] is True
    assert "tolerancia_sequia_tierra" in param
    assert "pesos_por_prioridad" in param


@pytest.mark.asyncio
async def test_salud_y_version_operacion(async_client: AsyncClient):
    # 1. /v1/salud (RNF12)
    res_salud = await async_client.get("/v1/salud")
    assert res_salud.status_code == 200, res_salud.text
    salud = res_salud.json()
    assert salud["estado"] == "operativo"
    assert "fuentes" in salud
    assert salud["fuentes"]["gpm_imerg"] == "disponible"

    # 2. /v1/version (RNF05)
    res_ver = await async_client.get("/v1/version")
    assert res_ver.status_code == 200, res_ver.text
    ver = res_ver.json()
    assert "api" in ver
    assert "pipeline" in ver
    assert "reglas" in ver

    # 3. /health
    res_h = await async_client.get("/health")
    assert res_h.status_code == 200
    assert res_h.json()["status"] == "ok"
