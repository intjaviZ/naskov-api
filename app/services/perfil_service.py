import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from itertools import accumulate
from typing import Any, Literal, Protocol
from uuid import UUID
from app.dtos.perfil_response_dto import (
    HeladasDTO,
    InicioLluviasDTO,
    LluviaMensualDTO,
    PerfilAgroclimaticoResponseDTO,
    SecuenciaSecaDTO,
)
from app.repository.parcela_repository import ParcelaRepository


class ParcelaNoEncontradaError(Exception):
    """La parcela no existe o pertenece a otra cuenta."""


class DatosInsuficientesError(Exception):
    """No hay serie suficiente para calcular el perfil; el mensaje es el motivo (R6)."""


class IndicadoresInvalidosError(ValueError):
    """El parámetro ?indicadores= trae un nombre desconocido."""


INDICADORES_VALIDOS = frozenset(
    {"lluvia_mensual", "secuencia_seca_max_dias", "rre", "inicio_lluvias", "heladas"}
)
MESES_TEMPORADA = (5, 6, 7, 8, 9, 10)
_DIAS_POR_MES = (31, 30, 31, 31, 30, 31)
DIAS_TEMPORADA = sum(_DIAS_POR_MES)
_INICIO_DE_MES = tuple(accumulate((0, *_DIAS_POR_MES[:-1])))
_ANIO_NO_BISIESTO = 2001


@dataclass(frozen=True)
class ParametrosPerfil:
    f_min: float = 0.6
    dia_seco_mm: float = 1.0
    inicio_mm: float = 20.0
    inicio_dias: int = 3
    inicio_racha_seca_dias: int = 10
    inicio_ventana_dias: int = 30
    t_helada_c: float = 2.0
    helada_dias_min: int = 1
    helada_anios_min: int = 3
    anios_min: int = 15
    anios_ok: int = 20
    f_val_ok: float = 0.8


@dataclass(frozen=True)
class SerieAnual:
    anio: int
    lluvia_mm: Sequence[float | None]
    tmin_c: Sequence[float | None] | None = None


@dataclass(frozen=True)
class DatosClimaParcela:
    anios: Sequence[SerieAnual]
    rre: Literal["bajo", "medio", "alto"] | None
    fuente: str
    resolucion_km: int
    version_pipeline: str
    id_ejecucion: str
    vigencia_hasta: datetime
    concordancia_baja: bool | None = None


class ProveedorClima(Protocol):
    async def obtener(self, geometria: dict[str, Any]) -> DatosClimaParcela:
        ...


def percentil(valores: Sequence[float], p: float) -> float:
    if not valores:
        raise ValueError("No hay valores para calcular el percentil.")
    orden = sorted(valores)
    posicion = (len(orden) - 1) * p / 100
    bajo, alto = math.floor(posicion), math.ceil(posicion)
    if bajo == alto:
        return float(orden[bajo])
    return orden[bajo] + (orden[alto] - orden[bajo]) * (posicion - bajo)


def fraccion_valida(lluvia: Sequence[float | None]) -> float:
    return sum(v is not None for v in lluvia) / DIAS_TEMPORADA


def racha_seca(lluvia: Sequence[float | None], inicio: int, fin: int, dia_seco_mm: float) -> int:
    mejor = actual = 0
    for v in lluvia[inicio:fin]:
        if v is not None and v < dia_seco_mm:
            actual += 1
            mejor = max(mejor, actual)
        else:
            actual = 0
    return mejor


def lluvia_por_mes(lluvia: Sequence[float | None]) -> list[float]:
    return [
        sum(v for v in lluvia[inicio : inicio + dias] if v is not None)
        for inicio, dias in zip(_INICIO_DE_MES, _DIAS_POR_MES, strict=True)
    ]


def indice_inicio_lluvias(lluvia: Sequence[float | None], p: ParametrosPerfil) -> int | None:
    for d in range(DIAS_TEMPORADA - p.inicio_dias + 1):
        ventana = lluvia[d : d + p.inicio_dias]
        if any(v is None for v in ventana) or sum(ventana) < p.inicio_mm:
            continue
        desde = d + p.inicio_dias
        if racha_seca(lluvia, desde, desde + p.inicio_ventana_dias, p.dia_seco_mm) < p.inicio_racha_seca_dias:
            return d
    return None


def dias_de_helada(tmin: Sequence[float | None], t_helada_c: float) -> int:
    return sum(t is not None and t <= t_helada_c for t in tmin)


def _indice_a_mm_dd(indice: int) -> str:
    dia = date(_ANIO_NO_BISIESTO, 5, 1) + timedelta(days=indice)
    return str(dia.month).zfill(2) + "-" + str(dia.day).zfill(2)


class PerfilService:
    def __init__(
        self,
        parcelas: ParcelaRepository,
        clima: ProveedorClima,
        descifrar_geometria: Callable[[bytes], dict[str, Any]],
        version_reglas: str,
        parametros: ParametrosPerfil | None = None,
        ahora: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._parcelas = parcelas
        self._clima = clima
        self._descifrar = descifrar_geometria
        self._version_reglas = version_reglas
        self._p = parametros or ParametrosPerfil()
        self._ahora = ahora

    async def obtener_perfil(
        self,
        id_parcela: UUID,
        id_cuenta: str,
        indicadores: Sequence[str] | None = None,
    ) -> PerfilAgroclimaticoResponseDTO:
        pedidos = self._normalizar_indicadores(indicadores)

        parcela = await self._parcelas.obtener_de_cuenta(id_parcela, id_cuenta, con_geometria=True)
        if parcela is None:
            raise ParcelaNoEncontradaError
        if parcela.geometria_cifrada is None:
            raise DatosInsuficientesError("La parcela no tiene geometría registrada.")

        geometria = self._descifrar(parcela.geometria_cifrada)
        datos = await self._clima.obtener(geometria)
        del geometria

        validos = self._anios_validos(datos.anios)
        if len(validos) < self._p.anios_min:
            raise DatosInsuficientesError(
                "Hay menos de " + str(self._p.anios_min) + " años con datos válidos para esta zona."
            )

        campos: dict[str, Any] = {}
        if "lluvia_mensual" in pedidos:
            campos["lluvia_mensual"] = self._lluvia_mensual(validos)
        if "secuencia_seca_max_dias" in pedidos:
            campos["secuencia_seca_max_dias"] = self._secuencia_seca(validos)
        if "rre" in pedidos:
            campos["rre"] = datos.rre
        if "inicio_lluvias" in pedidos:
            campos["inicio_lluvias"] = self._inicio_lluvias(validos)
        if "heladas" in pedidos:
            campos["heladas"] = self._heladas(validos)

        f_val_medio = sum(fraccion_valida(s.lluvia_mm) for s in validos) / len(validos)

        vigencia = datos.vigencia_hasta
        if vigencia.tzinfo is None:
            vigencia = vigencia.replace(tzinfo=UTC)

        return PerfilAgroclimaticoResponseDTO(
            **campos,
            fuente=datos.fuente,
            resolucion_km=datos.resolucion_km,
            anios=len(validos),
            f_val=round(f_val_medio, 2),
            confianza=self._confianza(len(validos), f_val_medio, datos.concordancia_baja),
            version_pipeline=datos.version_pipeline,
            id_ejecucion=datos.id_ejecucion,
            version_reglas=self._version_reglas,
            generado_utc=self._ahora(),
            vigencia_hasta=vigencia,
        )

    @staticmethod
    def _normalizar_indicadores(indicadores: Sequence[str] | None) -> frozenset[str]:
        if not indicadores:
            return INDICADORES_VALIDOS
        pedidos = frozenset(i.strip() for i in indicadores if i.strip())
        desconocidos = pedidos - INDICADORES_VALIDOS
        if desconocidos:
            raise IndicadoresInvalidosError(
                "Indicadores no válidos. Opciones: " + ", ".join(sorted(INDICADORES_VALIDOS))
            )
        return pedidos or INDICADORES_VALIDOS

    def _anios_validos(self, anios: Sequence[SerieAnual]) -> list[SerieAnual]:
        for serie in anios:
            if len(serie.lluvia_mm) != DIAS_TEMPORADA:
                raise ValueError("La serie de lluvia no tiene la longitud de la temporada.")
        return [s for s in anios if fraccion_valida(s.lluvia_mm) >= self._p.f_min]

    @staticmethod
    def _lluvia_mensual(validos: list[SerieAnual]) -> list[LluviaMensualDTO]:
        por_anio = [lluvia_por_mes(s.lluvia_mm) for s in validos]
        salida: list[LluviaMensualDTO] = []
        for i, mes in enumerate(MESES_TEMPORADA):
            valores = [mensual[i] for mensual in por_anio]
            salida.append(
                LluviaMensualDTO(
                    mes=mes,
                    mediana_mm=round(percentil(valores, 50), 1),
                    p10_mm=round(percentil(valores, 10), 1),
                    p90_mm=round(percentil(valores, 90), 1),
                )
            )
        return salida

    def _secuencia_seca(self, validos: list[SerieAnual]) -> SecuenciaSecaDTO:
        maximas = [racha_seca(s.lluvia_mm, 0, DIAS_TEMPORADA, self._p.dia_seco_mm) for s in validos]
        return SecuenciaSecaDTO(
            p10=round(percentil(maximas, 10), 1),
            p90=round(percentil(maximas, 90), 1),
        )

    def _inicio_lluvias(self, validos: list[SerieAnual]) -> InicioLluviasDTO | None:
        indices = [
            i for s in validos if (i := indice_inicio_lluvias(s.lluvia_mm, self._p)) is not None
        ]
        if not indices:
            return None
        return InicioLluviasDTO(
            mediana_fecha=_indice_a_mm_dd(round(percentil(indices, 50))),
            p10_fecha=_indice_a_mm_dd(round(percentil(indices, 10))),
            p90_fecha=_indice_a_mm_dd(round(percentil(indices, 90))),
        )

    def _heladas(self, validos: list[SerieAnual]) -> HeladasDTO | None:
        con_tmin = [s for s in validos if s.tmin_c is not None and any(t is not None for t in s.tmin_c)]
        if not con_tmin:
            return None
        anios_con_helada = sum(
            dias_de_helada(s.tmin_c, self._p.t_helada_c) >= self._p.helada_dias_min for s in con_tmin
        )
        if anios_con_helada >= self._p.helada_anios_min:
            return HeladasDTO(
                aplica=True,
                motivo="hay días de helada en al menos "
                + str(self._p.helada_anios_min)
                + " años del periodo",
            )
        return HeladasDTO(aplica=False, motivo="sin días de helada en el periodo")

    def _confianza(
        self, n_anios: int, f_val_medio: float, concordancia_baja: bool | None
    ) -> Literal["alta", "media", "baja"]:
        nivel = 3
        nivel -= n_anios < self._p.anios_ok
        nivel -= f_val_medio < self._p.f_val_ok
        nivel -= concordancia_baja is True
        return ("baja", "baja", "media", "alta")[max(nivel, 0)]