from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ParcelaORM(Base):
    __tablename__ = "parcelas"

    id_parcela: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    id_cuenta: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cuentas.id_cuenta", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    area_ha: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    latitud: Mapped[float] = mapped_column(Float, default=16.2333, nullable=False)
    longitud: Mapped[float] = mapped_column(Float, default=-93.2667, nullable=False)
    region: Mapped[str] = mapped_column(String(50), default="frailesca", nullable=False)
    creada_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
