from typing import TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.parcela_model import ParcelaORM
    from app.models.sesion_model import SesionRevocadaORM


class CuentaORM(Base):
    __tablename__ = "cuentas"

    id_cuenta: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    correo: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    contrasena_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    creada_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    parcelas: Mapped[list["ParcelaORM"]] = relationship(
        "ParcelaORM",
        backref="cuenta",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    sesiones_revocadas: Mapped[list["SesionRevocadaORM"]] = relationship(
        "SesionRevocadaORM",
        backref="cuenta",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
