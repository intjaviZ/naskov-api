import base64
import json
import math
from datetime import datetime
from uuid import UUID
from cryptography.fernet import Fernet
from shapely.geometry import Point, Polygon, shape

from app.core.config import settings
from app.core.exceptions import ErroresContrato, NasKobException
from app.dtos.declaracion_create_dto import DeclaracionPatchRequestDTO
from app.dtos.declaracion_response_dto import DeclaracionActualizadaResponseDTO
from app.dtos.parcela_create_dto import ModoMarcadoEnum, ParcelaCreateDTO
from app.dtos.parcela_response_dto import (
    ParcelaCreadaResponseDTO,
    ParcelaDetalleResponseDTO,
    ParcelaItemDTO,
    ParcelaListaResponseDTO,
)
from app.models.declaracion_model import CultivoEnum
from app.repository.parcela_repository import ClavePagina, ParcelaRepository

# Límite geográfico aproximado del estado de Chiapas (WGS84)
POLIGONO_CHIAPAS = Polygon([
    (-94.13, 16.03), (-94.24, 16.50), (-93.75, 17.50), (-93.30, 17.98),
    (-92.00, 17.60), (-91.10, 17.30), (-90.80, 16.80), (-90.38, 16.10),
    (-91.20, 15.00), (-92.05, 14.70), (-92.30, 14.53), (-93.20, 15.20),
    (-94.13, 16.03)
])


def _obtener_cipher() -> Fernet:
    clave_base = settings.JWT_SECRET_KEY.encode()[:32].ljust(32, b"0")
    return Fernet(base64.urlsafe_b64encode(clave_base))


def cifrar_geometria(geometria_dict: dict) -> bytes:
    cipher = _obtener_cipher()
    return cipher.encrypt(json.dumps(geometria_dict).encode())


def descifrar_geometria(cifrada: bytes) -> dict:
    cipher = _obtener_cipher()
    return json.loads(cipher.decrypt(cifrada).decode())


class ParcelaService:
    def __init__(self, repo: ParcelaRepository) -> None:
        self._repo = repo

    async def registrar_parcela(self, dto: ParcelaCreateDTO, id_cuenta: str) -> ParcelaCreadaResponseDTO:
        if dto.modo == ModoMarcadoEnum.poligono:
            assert dto.geometria is not None
            geojson_geom = dto.geometria.model_dump()
            geom_shapely = shape(geojson_geom)

            # Validación de Chiapas
            if not POLIGONO_CHIAPAS.intersects(geom_shapely):
                raise NasKobException(
                    422,
                    "region_no_preparada",
                    "Región no preparada",
                    "La parcela está fuera de Chiapas, que es el estado donde funciona la app."
                )

            lat_media = geom_shapely.centroid.y
            metros_lat = 110650.0
            metros_lon = 111320.0 * math.cos(math.radians(lat_media))
            
            anillo = dto.geometria.coordinates[0]
            area_m2 = 0.5 * abs(
                sum(
                    (anillo[i][0] * metros_lon) * (anillo[i + 1][1] * metros_lat)
                    - (anillo[i + 1][0] * metros_lon) * (anillo[i][1] * metros_lat)
                    for i in range(len(anillo) - 1)
                )
            )
            area_ha = round(area_m2 / 10000.0, 2)
            geometria_para_guardar = geojson_geom

        else:
            assert dto.punto_radio is not None
            punto_shapely = Point(dto.punto_radio.punto.lon, dto.punto_radio.punto.lat)
            if not POLIGONO_CHIAPAS.contains(punto_shapely):
                raise NasKobException(
                    422,
                    "region_no_preparada",
                    "Región no preparada",
                    "La parcela está fuera de Chiapas, que es el estado donde funciona la app."
                )

            radio_m = dto.punto_radio.radio_m
            area_m2 = math.pi * (radio_m ** 2)
            area_ha = round(area_m2 / 10000.0, 2)
            geometria_para_guardar = dto.punto_radio.model_dump()

        # Cifrado de geometría 
        geometria_cifrada = cifrar_geometria(geometria_para_guardar)

        parcela = await self._repo.crear(
            id_cuenta=id_cuenta,
            area_ha=area_ha,
            geometria_cifrada=geometria_cifrada,
        )

        return ParcelaCreadaResponseDTO(id_parcela=parcela.id_parcela, area_ha=parcela.area_ha)

    async def listar_parcelas(
        self, id_cuenta: str, limite: int = 10, cursor: str | None = None
    ) -> ParcelaListaResponseDTO:
        despues: ClavePagina | None = None
        if cursor:
            try:
                decodificado = base64.urlsafe_b64decode(cursor.encode()).decode()
                ts_iso, id_str = decodificado.split("|")
                despues = (datetime.fromisoformat(ts_iso), UUID(id_str))
            except Exception:
                raise ErroresContrato.solicitud_invalida("El cursor de paginación no es válido.", "cursor")

        filas, siguiente_clave = await self._repo.listar_por_cuenta(
            id_cuenta=id_cuenta, limite=limite, despues=despues
        )

        siguiente_cursor = None
        if siguiente_clave:
            siguiente_cursor = base64.urlsafe_b64encode(
                f"{siguiente_clave[0].isoformat()}|{siguiente_clave[1]}".encode()
            ).decode()

        items = [
            ParcelaItemDTO(
                id_parcela=p.id_parcela,
                area_ha=p.area_ha,
                estado=p.estado,
            )
            for p in filas
        ]
        return ParcelaListaResponseDTO(parcelas=items, siguiente_cursor=siguiente_cursor)

    async def obtener_parcela(self, id_parcela: UUID, id_cuenta: str) -> ParcelaDetalleResponseDTO:
        parcela = await self._repo.obtener_de_cuenta(
            id_parcela=id_parcela, id_cuenta=id_cuenta, con_declaracion=True
        )
        if not parcela:
            raise ErroresContrato.no_encontrado("Parcela")

        declaracion_dto = None
        if parcela.declaracion:
            declaracion_dto = {
                "rotacion_existente": parcela.declaracion.rotacion_existente,
                "suelo": parcela.declaracion.suelo,
                "riego_veces_semana": parcela.declaracion.riego_veces_semana,
                "considerar_riesgo": parcela.declaracion.considerar_riesgo,
                "prioridad_principal": parcela.declaracion.prioridad_principal,
            }

        return ParcelaDetalleResponseDTO(
            id_parcela=parcela.id_parcela,
            area_ha=parcela.area_ha,
            estado=parcela.estado,
            declaracion=declaracion_dto,
        )

    async def guardar_declaracion(
        self, id_parcela: UUID, id_cuenta: str, dto: DeclaracionPatchRequestDTO
    ) -> DeclaracionActualizadaResponseDTO:
        parcela = await self._repo.obtener_de_cuenta(id_parcela=id_parcela, id_cuenta=id_cuenta)
        if not parcela:
            raise ErroresContrato.no_encontrado("Parcela")

        d = dto.declaracion
        cultivos = (
            CultivoEnum(d.rotacion_existente[0].cultivo),
            CultivoEnum(d.rotacion_existente[1].cultivo),
            CultivoEnum(d.rotacion_existente[2].cultivo),
        )

        declaracion = await self._repo.guardar_declaracion(
            id_parcela=id_parcela,
            cultivos=cultivos,
            tipo_tierra=d.suelo.tipo_tierra,
            agrego_productos=d.suelo.agrego_productos,
            riego_veces_semana=d.riego_veces_semana,
            considerar_riesgo=d.considerar_riesgo,
            prioridad_principal=d.prioridad_principal,
        )

        return DeclaracionActualizadaResponseDTO(
            id_parcela=id_parcela,
            declaracion_actualizada_utc=declaracion.actualizada_utc,
        )

    async def eliminar_parcela(self, id_parcela: UUID, id_cuenta: str) -> None:
        eliminado = await self._repo.eliminar_de_cuenta(id_parcela=id_parcela, id_cuenta=id_cuenta)
        if not eliminado:
            raise ErroresContrato.no_encontrado("Parcela")