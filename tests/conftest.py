import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Importar todos los modelos ORM para que Base.metadata conozca todas las tablas
import app.models
from main import app
from app.core.database import Base, get_db_session

TEST_DB_PATH = "./test_naskob_suite.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db_session():
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db_session] = override_get_db_session


@pytest_asyncio.fixture(autouse=True)
async def inicializar_bd():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
