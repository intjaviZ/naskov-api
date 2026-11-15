from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, undefer

from app.models.declaracion_model import DeclaracionORM
from app.models.parcela_model import EstadoParcelaEnum, ParcelaORM

ClavePagina = tuple[datetime, UUID]


def _normalizar_uuid(val: UUID | str) -> UUID:
    if isinstance(val, UUID):
        return val
    return UUID(str(val))


class ParcelaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def crear(
        self,
        *,
        id_cuenta: str,
        area_ha: float,
        geometria_cifrada: bytes,
        nombre: str | None = None,
        latitud: float | None = None,
        longitud: float | None = None,
        region: str = "frailesca",
    ) -> ParcelaORM:
        parcela = ParcelaORM(
            id_cuenta=str(id_cuenta),
            area_ha=area_ha,
            geometria_cifrada=geometria_cifrada,
            nombre=nombre or "Parcela La Frailesca",
            latitud=latitud if latitud is not None else 16.2333,
            longitud=longitud if longitud is not None else -93.2667,
            region=region or "frailesca",
        )
        self._session.add(parcela)
        await self._session.commit()
        await self._session.refresh(parcela)
        return parcela

    async def obtener_de_cuenta(
        self,
        id_parcela: UUID | str,
        id_cuenta: str,
        *,
        con_declaracion: bool = False,
        con_geometria: bool = False,
        para_actualizar: bool = False,
    ) -> ParcelaORM | None:
        u_id = _normalizar_uuid(id_parcela)
        consulta = select(ParcelaORM).where(
            ParcelaORM.id_parcela == u_id,
            ParcelaORM.id_cuenta == str(id_cuenta),
        )
        if con_declaracion:
            consulta = consulta.options(selectinload(ParcelaORM.declaracion))
        if con_geometria:
            consulta = consulta.options(undefer(ParcelaORM.geometria_cifrada))
        if para_actualizar:
            consulta = consulta.with_for_update()
        return await self._session.scalar(consulta)

    async def listar_por_cuenta(
        self,
        id_cuenta: str,
        limite: int,
        despues: ClavePagina | None = None,
    ) -> tuple[Sequence[ParcelaORM], ClavePagina | None]:
        consulta = (
            select(ParcelaORM)
            .where(ParcelaORM.id_cuenta == str(id_cuenta))
            .order_by(ParcelaORM.creada_utc.desc(), ParcelaORM.id_parcela.desc())
            .limit(limite + 1)
        )
        if despues is not None:
            consulta = consulta.where(
                tuple_(ParcelaORM.creada_utc, ParcelaORM.id_parcela)
                < tuple_(despues[0], _normalizar_uuid(despues[1]))
            )

        filas = list((await self._session.scalars(consulta)).all())
        if len(filas) <= limite:
            return filas, None

        filas = filas[:limite]
        ultima = filas[-1]
        return filas, (ultima.creada_utc, _normalizar_uuid(ultima.id_parcela))

    async def eliminar_de_cuenta(self, id_parcela: UUID | str, id_cuenta: str) -> bool:
        u_id = _normalizar_uuid(id_parcela)
        existe = await self._session.scalar(
            select(ParcelaORM.id_parcela).where(
                ParcelaORM.id_parcela == u_id,
                ParcelaORM.id_cuenta == str(id_cuenta),
            )
        )
        if existe is None:
            return False
        await self._session.execute(
            delete(DeclaracionORM).where(DeclaracionORM.id_parcela == u_id)
        )
        await self._session.execute(delete(ParcelaORM).where(ParcelaORM.id_parcela == u_id))
        await self._session.commit()
        return True

    async def guardar_declaracion(
        self,
        id_parcela: UUID | str,
        *,
        cultivos: tuple[str, str, str],
        tipo_tierra: str,
        agrego_productos: bool,
        riego_veces_semana: int,
        considerar_riesgo: bool,
        prioridad_principal: str,
        region: str,
    ) -> DeclaracionORM:
        u_id = _normalizar_uuid(id_parcela)
        declaracion = await self._session.scalar(
            select(DeclaracionORM).where(DeclaracionORM.id_parcela == u_id)
        )
        if declaracion is None:
            declaracion = DeclaracionORM(id_declaracion=str(uuid4()), id_parcela=u_id)
            self._session.add(declaracion)
        else:
            declaracion.version += 1

        declaracion.cultivo_c1 = cultivos[0]
        declaracion.cultivo_c2 = cultivos[1]
        declaracion.cultivo_c3 = cultivos[2]
        declaracion.tipo_tierra = tipo_tierra
        declaracion.agrego_productos = agrego_productos
        declaracion.riego_veces_semana = riego_veces_semana
        declaracion.metadatos = {
            "considerar_riesgo": considerar_riesgo,
            "prioridad_principal": prioridad_principal,
            "region": region,
            "actualizada_utc": datetime.now(UTC).isoformat(),
        }

        parcela = await self._session.get(ParcelaORM, u_id)
        if parcela is not None and parcela.estado != EstadoParcelaEnum.con_declaracion.value:
            parcela.estado = EstadoParcelaEnum.con_declaracion.value

        await self._session.commit()
        await self._session.refresh(declaracion)
        return declaracion

    async def actualizar_estado(self, parcela: ParcelaORM, estado: EstadoParcelaEnum) -> None:
        parcela.estado = estado.value
        await self._session.commit()