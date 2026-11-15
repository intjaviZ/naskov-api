import asyncio
import logging
import app.models
from app.core.database import engine, Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_db")

async def init_tables():
    logger.info("Verificando e inicializando tablas en la base de datos...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Tablas inicializadas exitosamente.")
    except Exception as e:
        logger.error(f"Error al inicializar tablas: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(init_tables())
