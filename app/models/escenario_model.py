from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class EscenarioORM(Base):
    __tablename__ = "escenarios"

    id_escenario: Mapped[str] = mapped_column(String(36), primary_key=True)
    id_evaluacion: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("evaluaciones.id_evaluacion", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    codigo: Mapped[str] = mapped_column(String(10), nullable=False)
    cultivo_id: Mapped[str] = mapped_column(String(50), nullable=False)
    cultivo_nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    es_linea_base: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    orden_visual: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    posicion_ranking: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    puntuacion_final: Mapped[float] = mapped_column(Float, nullable=False)
    criterio_agua: Mapped[float] = mapped_column(Float, nullable=False)
    criterio_riesgo: Mapped[float] = mapped_column(Float, nullable=False)
    criterio_suelo: Mapped[float] = mapped_column(Float, nullable=False)
    criterio_aptitud: Mapped[float] = mapped_column(Float, nullable=False)
    probabilidad_exito_pct: Mapped[float] = mapped_column(Float, nullable=False)
    rendimiento_esperado_kg_ha: Mapped[float] = mapped_column(Float, nullable=False)
    ic_inferior_kg_ha: Mapped[float] = mapped_column(Float, nullable=False)
    ic_superior_kg_ha: Mapped[float] = mapped_column(Float, nullable=False)
    tarjetas_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    tarjeta_5_partes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    delta_vs_a: Mapped[dict | None] = mapped_column(JSON, nullable=True)
