from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sesion_model import SesionRevocadaORM


class SesionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def revocar_token(self, jti: str, id_cuenta: str) -> None:
        existe = await self.esta_revocado(jti)
        if not existe:
            sesion_rev = SesionRevocadaORM(jti=jti, id_cuenta=id_cuenta)
            self.db.add(sesion_rev)
            await self.db.commit()

    async def esta_revocado(self, jti: str) -> bool:
        stmt = select(SesionRevocadaORM.jti).where(SesionRevocadaORM.jti == jti)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None