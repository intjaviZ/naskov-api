import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from main import app
from app.core.database import Base, get_db_session
from app.core.config import settings

TEST_DB_URL = "sqlite+aiosqlite:///./test_errores.db"
test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db_session():
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db_session] = override_get_db_session


@pytest.mark.asyncio
async def test_errores_rfc_9457():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Error de API Key ausente o inválida -> 401 Problem Details
        res_no_key = await client.post("/v1/evaluaciones/simular", json={})
        assert res_no_key.status_code == 401
        assert "application/problem+json" in res_no_key.headers["content-type"]
        problem_key = res_no_key.json()
        assert problem_key["codigo"] == "no_autenticado"

        headers_valid = {"X-Api-Key": settings.PWA_API_KEY}

        # 2. Error de Recurso no encontrado -> 404 Problem Details
        res_404 = await client.get("/v1/evaluaciones/eval-inexistente-12345", headers=headers_valid)
        assert res_404.status_code == 404
        assert "application/problem+json" in res_404.headers["content-type"]
        problem_404 = res_404.json()
        assert problem_404["codigo"] == "no_encontrado"

        # 3. Error de validación de esquema -> 400 Problem Details (RFC 9457 según Contrato v1.2)
        res_bad_body = await client.post(
            "/v1/evaluaciones/simular",
            json={
                "version_declaracion": -5,  # Debe ser >= 1
            },
            headers=headers_valid,
        )
        assert res_bad_body.status_code == 400
        assert "application/problem+json" in res_bad_body.headers["content-type"]
        problem_val = res_bad_body.json()
        assert problem_val["codigo"] == "solicitud_invalida"
