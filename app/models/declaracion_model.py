from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class DeclaracionORM(Base):
    __tablename__ = "declaraciones"

    id_declaracion: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    id_parcela: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("parcelas.id_parcela", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    cultivo_c1: Mapped[str] = mapped_column(String(50), default="maiz", nullable=False)
    cultivo_c2: Mapped[str] = mapped_column(String(50), default="frijol", nullable=False)
    cultivo_c3: Mapped[str] = mapped_column(String(50), default="calabaza", nullable=False)
    tipo_tierra: Mapped[str] = mapped_column(String(50), default="negra", nullable=False)
    riego_veces_semana: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    agrego_productos: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ph_estimado: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadatos: Mapped[dict] = mapped_column(JSON, default=dict)
    creada_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
