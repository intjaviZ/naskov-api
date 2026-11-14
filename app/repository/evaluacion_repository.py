from datetime import datetime, timezone
from sqlalchemy import select, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluacion_model import EvaluacionORM, CifraTrazabilidadORM
from app.models.escenario_model import EscenarioORM
from app.models.parcela_model import ParcelaORM
from app.models.declaracion_model import DeclaracionORM


class EvaluacionRepository:
    """Repositorio asíncrono para persistencia y consulta de evaluaciones agroclimáticas."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def guardar_evaluacion(
        self,
        evaluacion: EvaluacionORM,
        escenarios: list[EscenarioORM],
        cifras: list[CifraTrazabilidadORM],
    ) -> EvaluacionORM:
        self.db.add(evaluacion)
        for esc in escenarios:
            self.db.add(esc)
        for cif in cifras:
            self.db.add(cif)
        await self.db.commit()
        await self.db.refresh(evaluacion)
        return evaluacion

    async def obtener_evaluacion_por_id(self, id_evaluacion: str) -> EvaluacionORM | None:
        stmt = select(EvaluacionORM).where(EvaluacionORM.id_evaluacion == id_evaluacion)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def obtener_escenarios(self, id_evaluacion: str) -> list[EscenarioORM]:
        stmt = (
            select(EscenarioORM)
            .where(EscenarioORM.id_evaluacion == id_evaluacion)
            .order_by(EscenarioORM.orden_visual.asc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def obtener_cifra(self, id_evaluacion: str, id_cifra: str) -> CifraTrazabilidadORM | None:
        stmt = select(CifraTrazabilidadORM).where(
            CifraTrazabilidadORM.id_evaluacion == id_evaluacion,
            CifraTrazabilidadORM.id_cifra == id_cifra,
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def obtener_parcela(self, id_parcela: str) -> ParcelaORM | None:
        stmt = select(ParcelaORM).where(ParcelaORM.id_parcela == id_parcela)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def obtener_declaracion_vigente(
        self, id_parcela: str, version: int | None = None
    ) -> DeclaracionORM | None:
        stmt = select(DeclaracionORM).where(DeclaracionORM.id_parcela == id_parcela)
        if version is not None:
            stmt = stmt.where(DeclaracionORM.version == version)
        else:
            stmt = stmt.order_by(desc(DeclaracionORM.version))
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()
