import hashlib
import logging
import math
import time
from collections.abc import Mapping
from datetime import UTC, date, datetime, timedelta
from typing import Any, ClassVar

import httpx

from app.core.exceptions import ErroresContrato
from app.services.perfil_service import (
    DIAS_TEMPORADA,
    DatosClimaParcela,
    ProveedorClima,
    SerieAnual,
)

logger = logging.getLogger(__name__)

INICIO_TEMPORADA = (5, 1)
URL_POWER = "https://power.larc.nasa.gov/api/temporal/daily/point"
PRIMER_ANIO = 2001
TTL_CACHE_S = 7 * 24 * 3600
MAX_CELDAS_EN_CACHE = 500
VIGENCIA_DIAS = 30


def construir_serie_anual(
    anio: int,
    precipitacion_mm: Mapping[date, float | None],
    temperatura_min_c: Mapping[date, float | None] | None = None,
) -> SerieAnual:
    inicio = date(anio, *INICIO_TEMPORADA)
    fechas = [inicio + timedelta(days=i) for i in range(DIAS_TEMPORADA)]
    return SerieAnual(
        anio=anio,
        lluvia_mm=[precipitacion_mm.get(f) for f in fechas],
        tmin_c=None if temperatura_min_c is None else [temperatura_min_c.get(f) for f in fechas],
    )


def _centro(geometria: dict[str, Any]) -> tuple[float, float]:
    if "coordinates" in geometria:
        vertices = geometria["coordinates"][0][:-1]
        lat = sum(p[1] for p in vertices) / len(vertices)
        lon = sum(p[0] for p in vertices) / len(vertices)
        return lat, lon
    punto = geometria["punto"]
    return punto["lat"], punto["lon"]


class ProveedorClimaImerg(ProveedorClima):
    _cliente: ClassVar[httpx.AsyncClient | None] = None
    _cache: ClassVar[dict[tuple[int, int], tuple[float, DatosClimaParcela]]] = {}

    @classmethod
    def _http(cls) -> httpx.AsyncClient:
        if cls._cliente is None:
            cls._cliente = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
        return cls._cliente

    @classmethod
    async def cerrar(cls) -> None:
        if cls._cliente is not None:
            await cls._cliente.aclose()
            cls._cliente = None

    async def obtener(self, geometria: dict[str, Any]) -> DatosClimaParcela:
        lat, lon = _centro(geometria)
        celda = (math.floor(lat * 10), math.floor(lon * 10))
        guardado = self._cache.get(celda)
        if guardado is not None and guardado[0] > time.monotonic():
            return guardado[1]
        datos = await self._descargar(celda)
        if len(self._cache) >= MAX_CELDAS_EN_CACHE:
            self._cache.clear()
        self._cache[celda] = (time.monotonic() + TTL_CACHE_S, datos)
        return datos

    async def _descargar(self, celda: tuple[int, int]) -> DatosClimaParcela:
        anio_final = datetime.now(UTC).year - 1
        parametros = {
            "parameters": "IMERG_PRECTOT",
            "community": "AG",
            "latitude": round(celda[0] / 10 + 0.05, 2),
            "longitude": round(celda[1] / 10 + 0.05, 2),
            "start": str(PRIMER_ANIO) + "0101",
            "end": str(anio_final) + "1231",
            "format": "JSON",
        }
        try:
            respuesta = await self._http().get(URL_POWER, params=parametros)
            respuesta.raise_for_status()
            diario = respuesta.json()["properties"]["parameter"]["IMERG_PRECTOT"]
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            logger.warning("Fallo la descarga de IMERG para la celda %s", celda, exc_info=True)
            raise ErroresContrato.fuente_degradada(
                "No se pudo obtener la lluvia satelital IMERG."
            ) from None

        lluvia: dict[date, float | None] = {}
        for clave, valor in diario.items():
            if valor is None or valor < 0:
                continue
            lluvia[date(int(clave[:4]), int(clave[4:6]), int(clave[6:8]))] = float(valor)

        series = []
        for anio in range(PRIMER_ANIO, anio_final + 1):
            serie = construir_serie_anual(anio, lluvia)
            if any(v is not None for v in serie.lluvia_mm):
                series.append(serie)

        return DatosClimaParcela(
            anios=series,
            rre=None,
            fuente="NASA GPM IMERG via NASA POWER",
            resolucion_km=10,
            version_pipeline="imerg-power-1.0",
            id_ejecucion=hashlib.sha256((str(celda) + str(anio_final)).encode()).hexdigest()[:16],
            vigencia_hasta=datetime.now(UTC) + timedelta(days=VIGENCIA_DIAS),
        )


ProveedorClimaFrailesca = ProveedorClimaImerg