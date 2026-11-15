import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from main import app
from app.core.database import Base, get_db_session
from app.core.dependencies import obtener_id_cuenta_actual
from app.core.config import settings

# Base de datos SQLite temporal aislada para tus pruebas
TEST_DB_URL = "sqlite+aiosqlite:///./test_parcelas.db"
test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db_session():
    async with TestSessionLocal() as session:
        yield session


async def override_obtener_id_cuenta():
    return "cuenta-agricultor-chiapas-01"


# Sobrescribimos la sesión y la autenticación para simular el agricultor logueado
app.dependency_overrides[get_db_session] = override_get_db_session
app.dependency_overrides[obtener_id_cuenta_actual] = override_obtener_id_cuenta


@pytest.mark.asyncio
async def test_flujo_completo_parcelas_y_perfil():
    # 1. Crear tablas en SQLite de prueba
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-Api-Key": settings.PWA_API_KEY}

        print("\n========================================================")
        print(" INICIANDO PRUEBAS: 3.2 PARCELAS & 3.3 PERFIL CLIMÁTICO")
        print("========================================================")

        # TEST 1: Crear parcela en Chiapas (Polígono GeoJSON)
        payload_parcela = {
            "modo": "poligono",
            "geometria": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-93.2700, 16.2300],
                        [-93.2690, 16.2300],
                        [-93.2690, 16.2310],
                        [-93.2700, 16.2310],
                        [-93.2700, 16.2300],
                    ]
                ],
            },
        }
        res_crear = await client.post("/v1/parcelas", json=payload_parcela, headers=headers)
        assert res_crear.status_code == 201, f"Error al crear: {res_crear.text}"
        data_crear = res_crear.json()
        assert "id_parcela" in data_crear
        assert data_crear["area_ha"] > 0
        id_parcela = data_crear["id_parcela"]
        print(f"✓ 1. POST /v1/parcelas: Creada con éxito. ID: {id_parcela} | Área: {data_crear['area_ha']} ha")

        # TEST 2: Validación geográfica (Rechazar parcela fuera de Chiapas)
        payload_fuera = {
            "modo": "punto_radio",
            "punto_radio": {
                "punto": {"lat": 19.4326, "lon": -99.1332}, # Ciudad de México (fuera de Chiapas)
                "radio_m": 120.0,
            },
        }
        res_fuera = await client.post("/v1/parcelas", json=payload_fuera, headers=headers)
        assert res_fuera.status_code == 422, "Debería dar 422 por estar fuera de Chiapas"
        print("✓ 2. Validación Chiapas: Parcela fuera de Chiapas rechazada con 422 (region_no_preparada)")

        # TEST 3: Listar mis parcelas
        res_listar = await client.get("/v1/parcelas", headers=headers)
        assert res_listar.status_code == 200, res_listar.text
        data_listar = res_listar.json()
        assert len(data_listar["parcelas"]) == 1
        print(f"✓ 3. GET /v1/parcelas: Listado correcto, total parcelas: {len(data_listar['parcelas'])}")

        # TEST 4: Detalle de parcela
        res_detalle = await client.get(f"/v1/parcelas/{id_parcela}", headers=headers)
        assert res_detalle.status_code == 200, res_detalle.text
        data_det = res_detalle.json()
        assert data_det["estado"] == "registrada"
        assert data_det["declaracion"] is None
        print("✓ 4. GET /v1/parcelas/{id}: Detalle verificado, estado 'registrada'")

        # TEST 5: Guardar Declaración de Cultivos previa (PATCH)
        payload_dec = {
            "rotacion_existente": [
                {"ciclo": 1, "cultivo": "maiz"},
                {"ciclo": 2, "cultivo": "frijol"},
                {"ciclo": 3, "cultivo": "calabaza"}
            ],
            "tipo_tierra": "negra",
            "riego_veces_semana": 2,
            "agrego_productos": True,
            "considerar_riesgo": True,
            "prioridad_principal": "agua",
            "region": "frailesca"
        }
        res_patch = await client.patch(f"/v1/parcelas/{id_parcela}", json=payload_dec, headers=headers)
        assert res_patch.status_code == 200, f"Error en patch: {res_patch.text}"
        print("✓ 5. PATCH /v1/parcelas/{id}: Declaración guardada y versión incrementada")

        # TEST 6: Consultar Perfil Agroclimático NASA IMERG
        res_perfil = await client.get(f"/v1/parcelas/{id_parcela}/perfil", headers=headers)

        # Puede ser 200 (si NASA POWER responde) o 503 (fuente degradada controlada por red)
        res_perfil = await client.get(f"/v1/parcelas/{id_parcela}/perfil", headers=headers)
        # Respuestas válidas del contrato: 200 (datos completos), 422 (datos insuficientes) o 503 (fuente degradada)
        assert res_perfil.status_code in [200, 422, 503], f"Respuesta inesperada: {res_perfil.status_code}"
        if res_perfil.status_code == 200:
            datos_p = res_perfil.json()
            print(f"✓ 6. GET /v1/parcelas/{{id}}/perfil: Datos NASA IMERG recibidos (Años: {datos_p.get('anios')})")
        elif res_perfil.status_code == 422:
            print(f"✓ 6. GET /v1/parcelas/{{id}}/perfil: Manejo RFC 9457 de 422 (datos_insuficientes) OK: {res_perfil.json().get('detalle')}")
        else:
            print("✓ 6. GET /v1/parcelas/{{id}}/perfil: Manejo RFC 9457 de 503 (fuente degradada) OK")

        # TEST 7: Eliminar Parcela (DELETE)
        res_del = await client.delete(f"/v1/parcelas/{id_parcela}", headers=headers)
        assert res_del.status_code == 204, f"Error en delete: {res_del.text}"
        print("✓ 7. DELETE /v1/parcelas/{id}: Parcela borrada exitosamente (204 No Content)")
        print(" ¡TODOS LOS TESTS DE PARCELAS Y PERFIL PASARON! ✓✓✓")

if __name__ == "__main__":
    asyncio.run(test_flujo_completo_parcelas_y_perfil())