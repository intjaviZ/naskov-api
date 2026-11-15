import pytest
from httpx import AsyncClient
from app.core.config import settings


@pytest.mark.asyncio
async def test_flujo_crud_parcela_y_declaracion(async_client: AsyncClient):
    client = async_client
    headers_api_key = {"X-Api-Key": settings.PWA_API_KEY}

    # 1. Crear cuenta y obtener token JWT
    payload_cuenta = {
        "correo": "ejidatario.villaflores@naskob.org",
        "contrasena": "Chiapas2026!",
    }
    await client.post("/v1/cuentas", json=payload_cuenta, headers=headers_api_key)
    res_login = await client.post("/v1/sesiones", json=payload_cuenta, headers=headers_api_key)
    token = res_login.json()["token"]

    auth_headers = {
        "X-Api-Key": settings.PWA_API_KEY,
        "Authorization": f"Bearer {token}",
    }

    # 2. Registrar parcela con punto y radio (La Frailesca: lat 16.2333, lon -93.2667)
    payload_parcela = {
        "modo": "punto_radio",
        "punto_radio": {
            "punto": {
                "lat": 16.2333,
                "lon": -93.2667,
            },
            "radio_m": 80.0,  # ~2 hectáreas
        },
    }
    res_crear = await client.post("/v1/parcelas", json=payload_parcela, headers=auth_headers)
    assert res_crear.status_code == 201, res_crear.text
    data_crear = res_crear.json()
    assert "id_parcela" in data_crear
    id_parcela = data_crear["id_parcela"]
    assert data_crear["area_ha"] > 0.0

    # 3. Listar parcelas de la cuenta
    res_listar = await client.get("/v1/parcelas", headers=auth_headers)
    assert res_listar.status_code == 200
    data_listar = res_listar.json()
    assert len(data_listar["parcelas"]) >= 1

    # 4. Obtener detalle de la parcela
    res_detalle = await client.get(f"/v1/parcelas/{id_parcela}", headers=auth_headers)
    assert res_detalle.status_code == 200
    data_detalle = res_detalle.json()
    assert data_detalle["id_parcela"] == id_parcela
    assert data_detalle["estado"] == "registrada"

    # 5. Guardar declaración de manejo (PATCH /v1/parcelas/{id})
    payload_declaracion = {
        "declaracion": {
            "rotacion_existente": [
                {"ciclo": 1, "cultivo": "maiz"},
                {"ciclo": 2, "cultivo": "frijol"},
                {"ciclo": 3, "cultivo": "calabaza"},
            ],
            "suelo": {
                "tipo_tierra": "negra",
                "agrego_productos": False,
            },
            "riego_veces_semana": 0,
            "considerar_riesgo": True,
            "prioridad_principal": "igual",
        }
    }
    res_decl = await client.patch(
        f"/v1/parcelas/{id_parcela}",
        json=payload_declaracion,
        headers=auth_headers,
    )
    assert res_decl.status_code == 200, res_decl.text
    data_decl = res_decl.json()
    assert "declaracion_actualizada_utc" in data_decl

    # 6. Consultar perfil agroclimático (GET /v1/parcelas/{id}/perfil)
    res_perfil = await client.get(f"/v1/parcelas/{id_parcela}/perfil", headers=auth_headers)
    assert res_perfil.status_code in (200, 422, 503), res_perfil.text
    if res_perfil.status_code == 200:
        data_perfil = res_perfil.json()
        assert "lluvia_mensual" in data_perfil
        assert "fuente" in data_perfil

    # 7. Eliminar parcela (DELETE /v1/parcelas/{id})
    res_del = await client.delete(f"/v1/parcelas/{id_parcela}", headers=auth_headers)
    assert res_del.status_code == 204

    # 8. Verificar que ya no existe (404)
    res_get_deleted = await client.get(f"/v1/parcelas/{id_parcela}", headers=auth_headers)
    assert res_get_deleted.status_code == 404
