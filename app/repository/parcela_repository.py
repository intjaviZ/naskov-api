from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID
from sqlalchemy import delete, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, undefer
from app.models.declaracion_model import (
    CultivoEnum,
    Declaracion,
    PrioridadPrincipalEnum,
    TipoTierraEnum,
)
from app.models.parcela_model import EstadoParcelaEnum, Parcela

ClavePagina = tuple[datetime, UUID]

class ParcelaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def crear(
        self, *, id_cuenta: str, area_ha: float, geometria_cifrada: bytes
    ) -> Parcela:
        parcela = Parcela(
            id_cuenta=id_cuenta, area_ha=area_ha, geometria_cifrada=geometria_cifrada
        )
        self._session.add(parcela)
        await self._session.flush()
        await self._session.refresh(parcela, ["creada_utc", "actualizada_utc"])
        return parcela

    async def obtener_de_cuenta(
        self,
        id_parcela: UUID,
        id_cuenta: str,
        *,
        con_declaracion: bool = False,
        con_geometria: bool = False,
        para_actualizar: bool = False,
    ) -> Parcela | None:
        consulta = select(Parcela).where(
            Parcela.id_parcela == id_parcela, Parcela.id_cuenta == id_cuenta
        )
        if con_declaracion:
            consulta = consulta.options(selectinload(Parcela.declaracion))
        if con_geometria:
            consulta = consulta.options(undefer(Parcela.geometria_cifrada))
        if para_actualizar:
            consulta = consulta.with_for_update()
        return await self._session.scalar(consulta)

    async def listar_por_cuenta(
        self,
        id_cuenta: str,
        limite: int,
        despues: ClavePagina | None = None,
    ) -> tuple[Sequence[Parcela], ClavePagina | None]:
        consulta = (
            select(Parcela)
            .where(Parcela.id_cuenta == id_cuenta)
            .order_by(Parcela.creada_utc.desc(), Parcela.id_parcela.desc())
            .limit(limite + 1)
        )
        if despues is not None:
            consulta = consulta.where(
                tuple_(Parcela.creada_utc, Parcela.id_parcela) < tuple_(*despues)
            )

        filas = list((await self._session.scalars(consulta)).all())
        if len(filas) <= limite:
            return filas, None

        filas = filas[:limite]
        ultima = filas[-1]
        return filas, (ultima.creada_utc, ultima.id_parcela)

    async def eliminar_de_cuenta(self, id_parcela: UUID, id_cuenta: str) -> bool:
        consulta = (
            delete(Parcela)
            .where(Parcela.id_parcela == id_parcela, Parcela.id_cuenta == id_cuenta)
            .returning(Parcela.id_parcela)
        )
        resultado = await self._session.execute(consulta)
        return resultado.scalar_one_or_none() is not None

    async def guardar_declaracion(
        self,
        id_parcela: UUID,
        *,
        cultivos: tuple[CultivoEnum, CultivoEnum, CultivoEnum],
        tipo_tierra: TipoTierraEnum,
        agrego_productos: bool,
        riego_veces_semana: int,
        considerar_riesgo: bool,
        prioridad_principal: PrioridadPrincipalEnum,
    ) -> Declaracion:
        declaracion = await self._session.get(Declaracion, id_parcela)
        if declaracion is None:
            declaracion = Declaracion(id_parcela=id_parcela)
            self._session.add(declaracion)

        declaracion.cultivo_ciclo_1, declaracion.cultivo_ciclo_2, declaracion.cultivo_ciclo_3 = cultivos
        declaracion.tipo_tierra = tipo_tierra
        declaracion.agrego_productos = agrego_productos
        declaracion.riego_veces_semana = riego_veces_semana
        declaracion.considerar_riesgo = considerar_riesgo
        declaracion.prioridad_principal = prioridad_principal
        declaracion.actualizada_utc = datetime.now(UTC)

        parcela = await self._session.get(Parcela, id_parcela)
        if parcela and parcela.estado != EstadoParcelaEnum.con_declaracion:
            parcela.estado = EstadoParcelaEnum.con_declaracion

        await self._session.flush()
        return declaracion

    async def actualizar_estado(self, parcela: Parcela, estado: EstadoParcelaEnum) -> None:
        parcela.estado = estado
        await self._session.flush()