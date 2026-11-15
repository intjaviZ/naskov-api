import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from enum import Enum
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.declaracion_model import Declaracion


class EstadoParcelaEnum(str, Enum):
    registrada = "registrada"
    con_declaracion = "con_declaracion"


class ParcelaORM(Base):
    __tablename__ = "parcelas"
    __table_args__ = (
        CheckConstraint("area_ha >= 0", name="ck_parcelas_area_ha_no_negativa"),
        Index("ix_parcelas_cuenta_creacion", "id_cuenta", "creada_utc", "id_parcela"),
    )

    id_parcela: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    id_cuenta: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cuentas.id_cuenta", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(100), default="Parcela La Frailesca", nullable=False)
    area_ha: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    latitud: Mapped[float] = mapped_column(Float, default=16.2333, nullable=False)
    longitud: Mapped[float] = mapped_column(Float, default=-93.2667, nullable=False)
    region: Mapped[str] = mapped_column(String(50), default="frailesca", nullable=False)
    geometria_cifrada: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, default=b"")
    estado: Mapped[str] = mapped_column(
        String(30), default=EstadoParcelaEnum.registrada.value, nullable=False
    )
    creada_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    actualizada_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    declaracion: Mapped[Optional["Declaracion"]] = relationship(
        "Declaracion",
        back_populates="parcela",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        est = self.estado.value if hasattr(self.estado, "value") else str(self.estado)
        return f"<Parcela id={self.id_parcela} estado={est}>"


Parcela = ParcelaORM
