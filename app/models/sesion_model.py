from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class SesionRevocadaORM(Base):
    __tablename__ = "sesiones_revocadas"

    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_cuenta: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cuentas.id_cuenta", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revocada_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )