from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import String, Float, DateTime, ForeignKey, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.declaracion_model import DeclaracionORM

class EstadoParcelaEnum(str, Enum):
    registrada = "registrada"
    con_declaracion = "con_declaracion"


class ParcelaORM(Base):
    __tablename__ = "parcelas"

    id_parcela: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    id_cuenta: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cuentas.id_cuenta", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(100), default="Parcela Principal", nullable=False)
    area_ha: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    latitud: Mapped[float] = mapped_column(Float, default=16.2333, nullable=False)
    longitud: Mapped[float] = mapped_column(Float, default=-93.2667, nullable=False)
    region: Mapped[str] = mapped_column(String(50), default="frailesca", nullable=False)
    geometria_cifrada: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, deferred=True)
    estado: Mapped[str] = mapped_column(
        String(30), default=EstadoParcelaEnum.registrada.value, nullable=False
    )
    creada_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    actualizada_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    declaracion: Mapped[DeclaracionORM | None] = relationship(
        DeclaracionORM,
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

Parcela = ParcelaORM