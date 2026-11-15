import base64
import json
import math
from datetime import datetime
from uuid import UUID
from typing import Any

from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.exceptions import ErroresContrato, NasKobException
from app.dtos.declaracion_create_dto import CicloRotacionDTO, DeclaracionCreateDTO
from app.dtos.declaracion_response_dto import DeclaracionResponseDTO
from app.dtos.parcela_create_dto import ModoMarcadoEnum, ParcelaCreateDTO
from app.dtos.parcela_response_dto import (
    ParcelaCreadaResponseDTO,
    ParcelaDetalleResponseDTO,
    ParcelaItemDTO,
    ParcelaListaResponseDTO,
)
from app.models.declaracion_model import DeclaracionORM
from app.models.parcela_model import EstadoParcelaEnum
from app.repository.parcela_repository import ClavePagina, ParcelaRepository

CULTIVOS_VALIDOS = frozenset(
    {"maiz", "frijol", "cacahuate", "calabaza", "sandia", "habanero", "no_se", "no_hubo"}
)
AREA_MIN_HA = 1.0
AREA_MAX_HA = 10.0
LIMITE_VERTICES = 500
RADIO_TIERRA_M = 6_371_000.0

# Contorno aproximado de Chiapas en (longitud, latitud)
POLIGONO_CHIAPAS = [
    (-94.13, 16.03), (-94.24, 16.50), (-93.75, 17.50), (-93.30, 17.98),
    (-92.00, 17.60), (-91.10, 17.30), (-90.80, 16.80), (-90.38, 16.10),
    (-91.20, 15.00), (-92.05, 14.70), (-92.30, 14.53), (-93.20, 15.20),
    (-94.13, 16.03),
]


def _obtener_cipher() -> Fernet:
    clave_base = settings.JWT_SECRET_KEY.encode()[:32].ljust(32, b"0")
    return Fernet(base64.urlsafe_b64encode(clave_base))


def cifrar_geometria(geometria_dict: dict) -> bytes:
    return _obtener_cipher().encrypt(json.dumps(geometria_dict).encode())


def descifrar_geometria(cifrada: bytes) -> dict:
    return json.loads(_obtener_cipher().decrypt(cifrada).decode())


def area_anillo_ha(anillo: list[tuple[float, float]]) -> float:
    suma = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(anillo, anillo[1:]):
        suma += math.radians(lon2 - lon1) * (
            2.0 + math.sin(math.radians(lat1)) + math.sin(math.radians(lat2))
        )
    return abs(suma) * RADIO_TIERRA_M**2 / 2.0 / 10_000.0


def centroide_anillo(anillo: list[tuple[float, float]]) -> tuple[float, float]:
    vertices = anillo[:-1]
    lat = sum(p[1] for p in vertices) / len(vertices)
    lon = sum(p[0] for p in vertices) / len(vertices)
    return lat, lon


def punto_en_poligono(lon: float, lat: float, anillo: list[tuple[float, float]]) -> bool:
    dentro = False
    j = len(anillo) - 1
    for i in range(len(anillo)):
        lon_i, lat_i = anillo[i]
        lon_j, lat_j = anillo[j]
        if (lat_i > lat) != (lat_j > lat):
            if lon < (lon_j - lon_i) * (lat - lat_i) / (lat_j - lat_i) + lon_i:
                dentro = not dentro
        j = i
    return dentro


def _orientacion(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> int:
    valor = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if valor > 0:
        return 1
    if valor < 0:
        return -1
    return 0


def tiene_lados_cruzados(anillo: list[tuple[float, float]]) -> bool:
    segmentos = len(anillo) - 1
    for i in range(segmentos):
        for j in range(i + 2, segmentos):
            if i == 0 and j == segmentos - 1:
                continue
            o1 = _orientacion(anillo[i], anillo[i + 1], anillo[j])
            o2 = _orientacion(anillo[i], anillo[i + 1], anillo[j + 1])
            o3 = _orientacion(anillo[j], anillo[j + 1], anillo[i])
            o4 = _orientacion(anillo[j], anillo[j + 1], anillo[i + 1])
            if o1 * o2 < 0 and o3 * o4 < 0:
                return True
    return False


def _declaracion_a_dto(dec: DeclaracionORM) -> DeclaracionResponseDTO:
    c1 = dec.cultivo_c1.value if hasattr(dec.cultivo_c1, "value") else str(dec.cultivo_c1)
    c2 = dec.cultivo_c2.value if hasattr(dec.cultivo_c2, "value") else str(dec.cultivo_c2)
    c3 = dec.cultivo_c3.value if hasattr(dec.cultivo_c3, "value") else str(dec.cultivo_c3)
    tt = dec.tipo_tierra.value if hasattr(dec.tipo_tierra, "value") else str(dec.tipo_tierra)
    act_utc = getattr(dec, "actualizada_utc", None) or getattr(dec, "creada_utc", None) or datetime.now(timezone.utc)
    return DeclaracionResponseDTO(
        id_declaracion=str(dec.id_declaracion),
        id_parcela=str(dec.id_parcela),
        version=dec.version,
        rotacion_existente=[
            CicloRotacionDTO(ciclo=1, cultivo=c1),
            CicloRotacionDTO(ciclo=2, cultivo=c2),
            CicloRotacionDTO(ciclo=3, cultivo=c3),
        ],
        tipo_tierra=tt,
        riego_veces_semana=dec.riego_veces_semana,
        agrego_productos=dec.agrego_productos,
        creada_utc=getattr(dec, "creada_utc", None) or act_utc,
        actualizada_utc=act_utc,
        declaracion_actualizada_utc=act_utc,
    )


def _codificar_cursor(clave: ClavePagina) -> str:
    texto = clave[0].isoformat() + "|" + str(clave[1])
    return base64.urlsafe_b64encode(texto.encode()).decode()


def _decodificar_cursor(cursor: str) -> ClavePagina:
    try:
        texto = base64.urlsafe_b64decode(cursor.encode()).decode()
        marca, id_str = texto.split("|")
        return datetime.fromisoformat(marca), UUID(id_str)
    except Exception:
        raise ErroresContrato.solicitud_invalida(
            "El cursor de paginación no es válido.", "cursor"
        ) from None


class ParcelaService:
    def __init__(self, repo: ParcelaRepository) -> None:
        self._repo = repo

    async def registrar_parcela(
        self, dto: ParcelaCreateDTO, id_cuenta: str
    ) -> ParcelaCreadaResponseDTO:
        nombre = getattr(dto, "nombre", None) or "Parcela La Frailesca"

        if dto.modo == ModoMarcadoEnum.poligono:
            assert dto.geometria is not None
            anillo = [(p[0], p[1]) for p in dto.geometria.coordinates[0]]
            if len(anillo) > LIMITE_VERTICES:
                raise ErroresContrato.solicitud_invalida(
                    "El polígono no puede tener más de " + str(LIMITE_VERTICES) + " posiciones.",
                    "geometria",
                )
            if tiene_lados_cruzados(anillo):
                raise ErroresContrato.solicitud_invalida(
                    "El polígono no es válido: sus lados se cruzan.", "geometria"
                )
            lat, lon = centroide_anillo(anillo)
            area_ha = dto.area_ha if getattr(dto, "area_ha", None) is not None and dto.area_ha > 0 else area_anillo_ha(anillo)
            geometria_para_guardar = dto.geometria.model_dump(mode="json")
        else:
            assert dto.punto_radio is not None
            lat = dto.punto_radio.punto.lat
            lon = dto.punto_radio.punto.lon
            area_ha = dto.area_ha if getattr(dto, "area_ha", None) is not None and dto.area_ha > 0 else (math.pi * dto.punto_radio.radio_m**2 / 10_000.0)
            geometria_para_guardar = dto.punto_radio.model_dump(mode="json")

        if not punto_en_poligono(lon, lat, POLIGONO_CHIAPAS):
            raise NasKobException(
                422,
                "region_no_preparada",
                "Región no preparada",
                "La parcela está fuera de Chiapas, que es el estado donde funciona la app.",
            )

        area_ha = round(area_ha, 2)
        if area_ha < AREA_MIN_HA or area_ha > AREA_MAX_HA:
            raise ErroresContrato.parcela_fuera_de_rango()

        parcela = await self._repo.crear(
            id_cuenta=id_cuenta,
            area_ha=area_ha,
            geometria_cifrada=cifrar_geometria(geometria_para_guardar),
            nombre=nombre,
            latitud=round(lat, 4),
            longitud=round(lon, 4),
            region="frailesca",
        )
        coords_salida = None
        if isinstance(geometria_para_guardar, dict):
            if geometria_para_guardar.get("type") == "Polygon" and "coordinates" in geometria_para_guardar:
                coords_salida = geometria_para_guardar["coordinates"][0]
            elif "punto" in geometria_para_guardar:
                p = geometria_para_guardar["punto"]
                coords_salida = [[p["lon"], p["lat"]]]

        return ParcelaCreadaResponseDTO(
            id_parcela=parcela.id_parcela,
            area_ha=parcela.area_ha,
            nombre=parcela.nombre,
            region=getattr(parcela, "region", "frailesca"),
            latitud=round(lat, 4),
            longitud=round(lon, 4),
            coordenadas=coords_salida,
            geometria=geometria_para_guardar,
        )

    async def listar_parcelas(
        self, id_cuenta: str, limite: int = 10, cursor: str | None = None
    ) -> ParcelaListaResponseDTO:
        despues = _decodificar_cursor(cursor) if cursor else None
        filas, siguiente_clave = await self._repo.listar_por_cuenta(
            id_cuenta=id_cuenta, limite=limite, despues=despues
        )
        items = [
            ParcelaItemDTO(
                id_parcela=p.id_parcela,
                area_ha=p.area_ha,
                estado=p.estado.value if hasattr(p.estado, "value") else str(p.estado),
                nombre=p.nombre,
                region=getattr(p, "region", "frailesca"),
                latitud=getattr(p, "latitud", None),
                longitud=getattr(p, "longitud", None),
            )
            for p in filas
        ]
        siguiente = _codificar_cursor(siguiente_clave) if siguiente_clave else None
        return ParcelaListaResponseDTO(parcelas=items, siguiente_cursor=siguiente)

    async def obtener_parcela(self, id_parcela: UUID, id_cuenta: str) -> ParcelaDetalleResponseDTO:
        parcela = await self._repo.obtener_de_cuenta(
            id_parcela, id_cuenta, con_declaracion=True, con_geometria=True
        )
        if parcela is None:
            raise ErroresContrato.no_encontrado("Parcela")

        coordenadas = None
        geometria_dict = None
        if parcela.geometria_cifrada:
            try:
                geom = descifrar_geometria(parcela.geometria_cifrada)
                geometria_dict = geom
                if isinstance(geom, dict):
                    if geom.get("type") == "Polygon" and "coordinates" in geom:
                        coordenadas = geom["coordinates"][0]
                    elif "punto" in geom:
                        p = geom["punto"]
                        coordenadas = [[p["lon"], p["lat"]]]
            except Exception:
                pass

        declaracion = _declaracion_a_dto(parcela.declaracion) if parcela.declaracion else None
        return ParcelaDetalleResponseDTO(
            id_parcela=parcela.id_parcela,
            area_ha=parcela.area_ha,
            estado=parcela.estado.value if hasattr(parcela.estado, "value") else str(parcela.estado),
            nombre=parcela.nombre,
            region=getattr(parcela, "region", "frailesca"),
            declaracion=declaracion,
            latitud=getattr(parcela, "latitud", None),
            longitud=getattr(parcela, "longitud", None),
            coordenadas=coordenadas,
            geometria=geometria_dict,
        )

    async def guardar_declaracion(
        self, id_parcela: UUID, id_cuenta: str, dto: Any
    ) -> DeclaracionResponseDTO:
        parcela = await self._repo.obtener_de_cuenta(id_parcela, id_cuenta, para_actualizar=True)
        if parcela is None:
            raise ErroresContrato.no_encontrado("Parcela")

        d = dto.declaracion if hasattr(dto, "declaracion") else dto

        def normalizar_cultivo(val: Any) -> str:
            c = getattr(val, "cultivo", None) or (val.get("cultivo") if isinstance(val, dict) else str(val))
            c_str = str(c).strip().lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace(" ", "_")
            return c_str

        ciclos = sorted(d.rotacion_existente, key=lambda c: getattr(c, "ciclo", None) or (c.get("ciclo", 1) if isinstance(c, dict) else 1))
        if [getattr(c, "ciclo", None) or (c.get("ciclo") if isinstance(c, dict) else None) for c in ciclos] != [1, 2, 3]:
            raise ErroresContrato.solicitud_invalida(
                "Los ciclos deben ser 1, 2 y 3, sin repetir.", "rotacion_existente"
            )
        cultivos = tuple(normalizar_cultivo(c) for c in ciclos)
        for cultivo in cultivos:
            if cultivo not in CULTIVOS_VALIDOS:
                raise ErroresContrato.solicitud_invalida(
                    "Cultivo no válido: " + cultivo + ".", "rotacion_existente"
                )

        tipo_tierra = getattr(d, "tipo_tierra", None)
        if not tipo_tierra and hasattr(d, "suelo") and hasattr(d.suelo, "tipo_tierra"):
            tipo_tierra = d.suelo.tipo_tierra
        tipo_tierra = str(tipo_tierra or "negra")

        agrego_productos = getattr(d, "agrego_productos", None)
        if agrego_productos is None and hasattr(d, "suelo") and hasattr(d.suelo, "agrego_productos"):
            agrego_productos = d.suelo.agrego_productos
        agrego_productos = bool(agrego_productos or False)

        riego_veces_semana = getattr(d, "riego_veces_semana", 0)
        considerar_riesgo = getattr(d, "considerar_riesgo", True)
        prioridad_principal = str(getattr(d, "prioridad_principal", "igual"))
        region = str(getattr(d, "region", "frailesca") or "frailesca")

        declaracion = await self._repo.guardar_declaracion(
            id_parcela,
            cultivos=cultivos,
            tipo_tierra=tipo_tierra,
            agrego_productos=agrego_productos,
            riego_veces_semana=riego_veces_semana,
            considerar_riesgo=considerar_riesgo,
            prioridad_principal=prioridad_principal,
            region=region,
        )

        return _declaracion_a_dto(declaracion)

    async def eliminar_parcela(self, id_parcela: UUID, id_cuenta: str) -> None:
        eliminada = await self._repo.eliminar_de_cuenta(id_parcela, id_cuenta)
        if not eliminada:
            raise ErroresContrato.no_encontrado("Parcela")
