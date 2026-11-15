import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    SmallInteger,
    Uuid,
    false,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.parcela_model import ParcelaORM


class CultivoEnum(str, Enum):
    maiz = "maiz"
    frijol = "frijol"
    cacahuate = "cacahuate"
    calabaza = "calabaza"
    sandia = "sandia"
    habanero = "habanero"
    no_se = "no_se"
    no_hubo = "no_hubo"


class TipoTierraEnum(str, Enum):
    negra = "negra"
    arcillosa = "arcillosa"
    arenosa = "arenosa"


class PrioridadPrincipalEnum(str, Enum):
    agua = "agua"
    riesgo = "riesgo"
    suelo = "suelo"
    igual = "igual"


def _columna_enum(enum_cls: type[Enum], nombre: str, longitud: int) -> SAEnum:
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=longitud,
        create_constraint=True,
        name=nombre,
        values_callable=lambda enum: [m.value for m in enum],
    )


class Declaracion(Base):
    __tablename__ = "declaraciones"
    __table_args__ = (
        CheckConstraint(
            "riego_veces_semana BETWEEN 0 AND 7", name="ck_declaraciones_riego_veces_semana"
        ),
    )

    id_parcela: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("parcelas.id_parcela", ondelete="CASCADE"), primary_key=True
    )
    cultivo_ciclo_1: Mapped[CultivoEnum] = mapped_column(
        _columna_enum(CultivoEnum, "ck_declaraciones_cultivo_ciclo_1", 20),
        nullable=False,
        default=CultivoEnum.maiz,
    )
    cultivo_ciclo_2: Mapped[CultivoEnum] = mapped_column(
        _columna_enum(CultivoEnum, "ck_declaraciones_cultivo_ciclo_2", 20),
        nullable=False,
        default=CultivoEnum.frijol,
    )
    cultivo_ciclo_3: Mapped[CultivoEnum] = mapped_column(
        _columna_enum(CultivoEnum, "ck_declaraciones_cultivo_ciclo_3", 20),
        nullable=False,
        default=CultivoEnum.calabaza,
    )

    tipo_tierra: Mapped[TipoTierraEnum] = mapped_column(
        _columna_enum(TipoTierraEnum, "ck_declaraciones_tipo_tierra", 10),
        nullable=False,
        default=TipoTierraEnum.negra,
    )
    agrego_productos: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    riego_veces_semana: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0
    )
    considerar_riesgo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    prioridad_principal: Mapped[PrioridadPrincipalEnum] = mapped_column(
        _columna_enum(PrioridadPrincipalEnum, "ck_declaraciones_prioridad_principal", 10),
        nullable=False,
        default=PrioridadPrincipalEnum.igual,
        server_default="igual",
    )

    actualizada_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    parcela: Mapped["Parcela"] = relationship(back_populates="declaracion", lazy="selectin")

    @property
    def rotacion_existente(self) -> list[dict[str, Any]]:
        return [
            {
                "ciclo": 1,
                "cultivo": (
                    self.cultivo_ciclo_1.value
                    if hasattr(self.cultivo_ciclo_1, "value")
                    else str(self.cultivo_ciclo_1)
                ),
            },
            {
                "ciclo": 2,
                "cultivo": (
                    self.cultivo_ciclo_2.value
                    if hasattr(self.cultivo_ciclo_2, "value")
                    else str(self.cultivo_ciclo_2)
                ),
            },
            {
                "ciclo": 3,
                "cultivo": (
                    self.cultivo_ciclo_3.value
                    if hasattr(self.cultivo_ciclo_3, "value")
                    else str(self.cultivo_ciclo_3)
                ),
            },
        ]

    @property
    def suelo(self) -> dict[str, Any]:
        return {
            "tipo_tierra": (
                self.tipo_tierra.value
                if hasattr(self.tipo_tierra, "value")
                else str(self.tipo_tierra)
            ),
            "agrego_productos": self.agrego_productos,
        }

    # Atributos de compatibilidad con EvaluacionRepository
    @property
    def version(self) -> int:
        return 1

    @property
    def cultivo_c1(self) -> str:
        return (
            self.cultivo_ciclo_1.value
            if hasattr(self.cultivo_ciclo_1, "value")
            else str(self.cultivo_ciclo_1)
        )

    @property
    def cultivo_c2(self) -> str:
        return (
            self.cultivo_ciclo_2.value
            if hasattr(self.cultivo_ciclo_2, "value")
            else str(self.cultivo_ciclo_2)
        )

    @property
    def cultivo_c3(self) -> str:
        return (
            self.cultivo_ciclo_3.value
            if hasattr(self.cultivo_ciclo_3, "value")
            else str(self.cultivo_ciclo_3)
        )

    def __repr__(self) -> str:
        return f"<Declaracion id_parcela={self.id_parcela}>"


DeclaracionORM = Declaracion
