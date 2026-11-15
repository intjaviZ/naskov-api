import pytest
from httpx import AsyncClient
from app.core.config import settings


@pytest.mark.asyncio
async def test_flujo_completo_auth_y_sesiones(async_client: AsyncClient):
    client = async_client
    headers_api_key = {"X-Api-Key": settings.PWA_API_KEY}

    # 1. Registrar nueva cuenta
    payload_registro = {
        "correo": "productor.frailesca@naskob.org",
        "contrasena": "Chiapas2026!",
    }
    res_reg = await client.post("/v1/cuentas", json=payload_registro, headers=headers_api_key)
    assert res_reg.status_code == 201, res_reg.text
    data_reg = res_reg.json()
    assert "id_cuenta" in data_reg

    # 2. Intentar registrar el mismo correo (debe fallar con 409 conflicto)
    res_dup = await client.post("/v1/cuentas", json=payload_registro, headers=headers_api_key)
    assert res_dup.status_code == 409, res_dup.text
    assert res_dup.json()["codigo"] == "correo_ya_registrado"

    # 3. Iniciar sesión con contraseña incorrecta (debe fallar con 401)
    res_bad_login = await client.post(
        "/v1/sesiones",
        json={"correo": "productor.frailesca@naskob.org", "contrasena": "Erronea123"},
        headers=headers_api_key,
    )
    assert res_bad_login.status_code == 401, res_bad_login.text
    assert res_bad_login.json()["codigo"] == "credenciales_invalidas"

    # 4. Iniciar sesión válida
    res_login = await client.post(
        "/v1/sesiones",
        json=payload_registro,
        headers=headers_api_key,
    )
    assert res_login.status_code == 201, res_login.text
    data_login = res_login.json()
    assert "token" in data_login
    token = data_login["token"]

    auth_headers = {
        "X-Api-Key": settings.PWA_API_KEY,
        "Authorization": f"Bearer {token}",
    }

    # 5. Cerrar sesión actual (DELETE /v1/sesiones/actual)
    res_logout = await client.delete("/v1/sesiones/actual", headers=auth_headers)
    assert res_logout.status_code == 204, res_logout.text

    # 6. Intentar usar el token revocado (debe dar 401 no_autenticado)
    res_post_revoked = await client.delete("/v1/cuenta", headers=auth_headers)
    assert res_post_revoked.status_code == 401, res_post_revoked.text
    assert res_post_revoked.json()["codigo"] == "no_autenticado"

    # 7. Iniciar sesión nuevamente para probar borrado de cuenta
    res_relogin = await client.post(
        "/v1/sesiones",
        json=payload_registro,
        headers=headers_api_key,
    )
    assert res_relogin.status_code == 201
    new_token = res_relogin.json()["token"]
    new_auth_headers = {
        "X-Api-Key": settings.PWA_API_KEY,
        "Authorization": f"Bearer {new_token}",
    }

    # 8. Borrar cuenta actual (DELETE /v1/cuenta)
    res_del_cuenta = await client.delete("/v1/cuenta", headers=new_auth_headers)
    assert res_del_cuenta.status_code == 204, res_del_cuenta.text

    # 9. Intentar iniciar sesión con la cuenta borrada (debe dar 401)
    res_login_deleted = await client.post(
        "/v1/sesiones",
        json=payload_registro,
        headers=headers_api_key,
    )
    assert res_login_deleted.status_code == 401
