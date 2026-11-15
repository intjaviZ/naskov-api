import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
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


class Parcela(Base):
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
    area_ha: Mapped[float] = mapped_column(Float, nullable=False, default=2.5)
    estado: Mapped[EstadoParcelaEnum] = mapped_column(
        SAEnum(
            EstadoParcelaEnum,
            native_enum=False,
            length=20,
            create_constraint=True,
            name="ck_parcelas_estado",
            values_callable=lambda enum: [m.value for m in enum],
        ),
        nullable=False,
        default=EstadoParcelaEnum.registrada,
        server_default=EstadoParcelaEnum.registrada.value,
    )

    geometria_cifrada: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=True, default=b""
    )
    creada_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizada_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    declaracion: Mapped[Optional["Declaracion"]] = relationship(
        back_populates="parcela",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    # Región por defecto para análisis agroclimático satelital
    region: str = "frailesca"

    def __repr__(self) -> str:
        return f"<Parcela id={self.id_parcela} estado={self.estado.value if self.estado else None}>"


ParcelaORM = Parcela
