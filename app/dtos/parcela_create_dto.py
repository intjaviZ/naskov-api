from enum import Enum
from typing import Annotated, Any, Literal, Self
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

RADIO_MAX_M = 1_000.0

Longitud = Annotated[float, Field(ge=-180.0, le=180.0, allow_inf_nan=False)]
Latitud = Annotated[float, Field(ge=-90.0, le=90.0, allow_inf_nan=False)]
Posicion = tuple[Longitud, Latitud]

class _EntradaGeoBase(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

class ModoMarcadoEnum(str, Enum):
    poligono = "poligono"
    punto_radio = "punto_radio"

class GeometriaGeoJSONDTO(_EntradaGeoBase):
    type: Literal["Polygon"] = Field(..., description="Tipo de geometría GeoJSON; debe ser 'Polygon'.")
    coordinates: list[list[Posicion]] = Field(
        ...,
        repr=False,
        description=(
            "Un solo anillo exterior en formato [longitud, latitud]. "
            "El primer y el último punto deben coincidir; mínimo 4 posiciones."
        ),
    )

    @field_validator("coordinates")
    @classmethod
    def validar_anillo(cls, coordinates: list[list[Posicion]]) -> list[list[Posicion]]:
        if len(coordinates) != 1:
            raise ValueError("Solo se admite el anillo exterior del polígono, sin huecos.")
        anillo = coordinates[0]
        if len(anillo) < 4:
            raise ValueError("El anillo del polígono necesita al menos 4 posiciones.")
        if anillo[0] != anillo[-1]:
            raise ValueError("El primer y el último punto del anillo deben ser idénticos.")
        if len(set(anillo[:-1])) < 3:
            raise ValueError("El polígono necesita al menos 3 vértices distintos.")
        return coordinates

class PuntoCoordenadaDTO(_EntradaGeoBase):
    lat: Latitud = Field(..., repr=False, description="Latitud en grados.")
    lon: Longitud = Field(..., repr=False, description="Longitud en grados.")

class PuntoRadioDTO(_EntradaGeoBase):
    punto: PuntoCoordenadaDTO
    radio_m: float = Field(
        ...,
        gt=0.0,
        le=RADIO_MAX_M,
        allow_inf_nan=False,
        description="Radio de la parcela en metros.",
    )

class ParcelaCreateDTO(_EntradaGeoBase):
    model_config = ConfigDict(
        extra="ignore",
        hide_input_in_errors=True,
        json_schema_extra={
            "examples": [
                {
                    "modo": "poligono",
                    "geometria": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-93.2700, 16.2300],
                                [-93.2690, 16.2300],
                                [-93.2690, 16.2310],
                                [-93.2700, 16.2310],
                                [-93.2700, 16.2300],
                            ]
                        ],
                    },
                }
            ]
        },
    )

    modo: ModoMarcadoEnum = Field(
        default=ModoMarcadoEnum.poligono,
        description="Forma en que se marcó la parcela en el mapa.",
    )
    geometria: GeometriaGeoJSONDTO | None = Field(
        default=None, description="Obligatoria si el modo es 'poligono'; prohibida en otro caso."
    )
    punto_radio: PuntoRadioDTO | None = Field(
        default=None, description="Obligatorio si el modo es 'punto_radio'; prohibido en otro caso."
    )

    # Campos opcionales para compatibilidad con el frontend
    nombre: str | None = Field(default=None, max_length=100)
    area_ha: float | None = Field(default=None, ge=0.0)
    metodo_delimitacion: str | None = Field(default=None)
    poligono: GeometriaGeoJSONDTO | None = Field(default=None)

    @model_validator(mode="before")
    @classmethod
    def adaptar_payload_frontend(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "poligono" in data and "geometria" not in data:
                data["geometria"] = data["poligono"]
            if "geometria" in data and "modo" not in data:
                data["modo"] = "poligono"
        return data

    @model_validator(mode="after")
    def validar_modo_y_geometria(self) -> Self:
        if self.modo == ModoMarcadoEnum.poligono:
            if self.geometria is None or self.punto_radio is not None:
                raise ValueError("Con el modo 'poligono' se envía únicamente 'geometria'.")
        elif self.modo == ModoMarcadoEnum.punto_radio:
            if self.punto_radio is None or self.geometria is not None:
                raise ValueError("Con el modo 'punto_radio' se envía únicamente 'punto_radio'.")
        return self