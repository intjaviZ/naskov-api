from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.escenario_model import EscenarioORM


class EvaluacionORM(Base):
    __tablename__ = "evaluaciones"

    id_evaluacion: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    id_parcela: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    id_cuenta: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    modo_ponderacion: Mapped[str] = mapped_column(String(50), default="equilibrado", nullable=False)
    version_declaracion: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    evaluada_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    metadatos_evaluacion: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    escenarios: Mapped[list["EscenarioORM"]] = relationship(
        backref="evaluacion",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    cifras_trazabilidad: Mapped[list["CifraTrazabilidadORM"]] = relationship(
        backref="evaluacion",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )


class CifraTrazabilidadORM(Base):
    __tablename__ = "cifras_trazabilidad"

    id_cifra: Mapped[str] = mapped_column(String(50), primary_key=True)
    id_evaluacion: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("evaluaciones.id_evaluacion", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    etiqueta: Mapped[str] = mapped_column(String(150), nullable=False)
    valor_mostrado: Mapped[str] = mapped_column(String(100), nullable=False)
    formula: Mapped[str] = mapped_column(Text, nullable=False)
    fuente_datos: Mapped[str] = mapped_column(String(200), nullable=False)
    pasos_calculo: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    variables_utilizadas: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
