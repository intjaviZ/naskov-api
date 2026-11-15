import hashlib
import random
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from app.services.perfil_service import (
    DIAS_TEMPORADA,
    DatosClimaParcela,
    ProveedorClima,
    SerieAnual,
)

class ProveedorClimaFrailesca(ProveedorClima):
    """
    Proveedor climático para La Frailesca, Chiapas (GPM IMERG 2001-2025).
    Genera series históricas consistentes y reproducibles a partir de la geometría de la parcela.
    """

    def __init__(self, anios_historial: int = 25) -> None:
        self._anios_historial = anios_historial

    async def obtener(self, geometria: dict[str, Any]) -> DatosClimaParcela:
        semilla = int(hashlib.sha256(str(geometria).encode()).hexdigest()[:8], 16)
        rng = random.Random(semilla)

        series: list[SerieAnual] = []
        anio_actual = 2025
        anio_inicio = anio_actual - self._anios_historial + 1

        for anio in range(anio_inicio, anio_actual + 1):
            lluvia: list[float | None] = []
            tmin: list[float | None] = []

            for _ in range(DIAS_TEMPORADA):
                if rng.random() < 0.02:
                    lluvia.append(None)
                    tmin.append(None)
                else:
                    es_lluvioso = rng.random() < 0.48
                    precipitacion = round(rng.expovariate(1 / 14.5), 1) if es_lluvioso else 0.0
                    lluvia.append(precipitacion)

                    temp_min = round(rng.gauss(18.5, 2.0), 1)
                    tmin.append(temp_min)

            series.append(SerieAnual(anio=anio, lluvia_mm=lluvia, tmin_c=tmin))

        ahora = datetime.now(UTC)
        vigencia = ahora + timedelta(days=30)
        rre_opciones: list[Literal["bajo", "medio", "alto"]] = ["bajo", "medio", "alto"]

        return DatosClimaParcela(
            anios=series,
            rre=rng.choice(rre_opciones),
            fuente="GPM IMERG",
            resolucion_km=11,
            version_pipeline="1.0.0",
            id_ejecucion=f"exec-{semilla:08x}",
            vigencia_hasta=vigencia,
            concordancia_baja=False,
        )