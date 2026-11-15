from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.cuenta_model import CuentaORM


class CuentaRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def obtener_por_correo(self, correo: str) -> CuentaORM | None:
        correo_norm = correo.lower().strip()
        stmt = select(CuentaORM).where(CuentaORM.correo == correo_norm)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def obtener_por_id(self, id_cuenta: str) -> CuentaORM | None:
        stmt = select(CuentaORM).where(CuentaORM.id_cuenta == id_cuenta)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def crear(self, cuenta: CuentaORM) -> CuentaORM:
        self.db.add(cuenta)
        await self.db.commit()
        await self.db.refresh(cuenta)
        return cuenta

    async def eliminar_en_cascada(self, id_cuenta: str) -> None:
        stmt = delete(CuentaORM).where(CuentaORM.id_cuenta == id_cuenta)
        await self.db.execute(stmt)
        await self.db.commit()