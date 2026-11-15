from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class CicloRotacionDTO(BaseModel):
    ciclo: int = Field(..., ge=1, le=3)
    cultivo: str = Field(
        ...,
        description="maiz, frijol, cacahuate, calabaza, sandia, habanero, no_se, no_hubo",
    )
    etiqueta: Optional[str] = Field(default=None, description="Etiqueta opcional UI ej: 'Hace 3 temporadas'")

    @field_validator("cultivo", mode="before")
    @classmethod
    def normalizar_cultivo(cls, v: Any) -> str:
        if isinstance(v, str):
            c = v.lower().strip()
            c = c.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            c = c.replace(" ", "_")
            return c
        return str(v)


class SueloDeclaracionDTO(BaseModel):
    tipo_tierra: Literal["negra", "arcillosa", "arenosa"] = Field(
        default="negra",
        description="Tipo de suelo: negra (25 d), arcillosa (30 d), arenosa (20 d)",
    )
    agrego_productos: bool = Field(
        default=False,
        description="¿Agregó fertilizantes o agroquímicos al suelo?",
    )


class DeclaracionDetallePayloadDTO(BaseModel):
    rotacion_existente: List[CicloRotacionDTO] = Field(..., min_length=3, max_length=3)
    suelo: SueloDeclaracionDTO = Field(default_factory=SueloDeclaracionDTO)
    riego_veces_semana: int = Field(default=0, ge=0, le=7)
    considerar_riesgo: bool = Field(default=True)
    prioridad_principal: Literal["agua", "riesgo", "suelo", "igual"] = Field(default="igual")

    @model_validator(mode="before")
    @classmethod
    def preprocesar_datos_frontend(cls, data: Any) -> Any:
        if isinstance(data, dict):
            manejo = data.get("manejo")
            if isinstance(manejo, dict):
                if "riego_veces_semana" in manejo and "riego_veces_semana" not in data:
                    data["riego_veces_semana"] = manejo["riego_veces_semana"]
                if "considerar_riesgo" in manejo and "considerar_riesgo" not in data:
                    data["considerar_riesgo"] = manejo["considerar_riesgo"]
                if "agrego_productos" in manejo and "agrego_productos" not in data:
                    data["agrego_productos"] = manejo["agrego_productos"]
                if "prioridad_principal" in manejo and "prioridad_principal" not in data:
                    data["prioridad_principal"] = manejo["prioridad_principal"]

            suelo = data.get("suelo")
            if isinstance(suelo, dict):
                if "tipo_tierra" in suelo and "tipo_tierra" not in data:
                    data["tipo_tierra"] = suelo["tipo_tierra"]
                if "agrego_productos" in suelo and "agrego_productos" not in data:
                    data["agrego_productos"] = suelo["agrego_productos"]
            elif "tipo_tierra" in data:
                data.setdefault("suelo", {
                    "tipo_tierra": data["tipo_tierra"],
                    "agrego_productos": data.get("agrego_productos", False),
                })
        return data


# Alias de compatibilidad para ParcelaDetalleResponseDTO
DeclaracionPayloadDTO = DeclaracionDetallePayloadDTO


class DeclaracionPatchRequestDTO(BaseModel):
    declaracion: DeclaracionDetallePayloadDTO

    @model_validator(mode="before")
    @classmethod
    def envolver_payload_directo(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "declaracion" not in data and ("rotacion_existente" in data or "manejo" in data):
                return {"declaracion": data}
        return data


class DeclaracionCreateDTO(BaseModel):
    rotacion_existente: List[CicloRotacionDTO] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Historial exacto de 3 ciclos previos",
        examples=[[
            {"ciclo": 1, "cultivo": "maiz"},
            {"ciclo": 2, "cultivo": "maiz"},
            {"ciclo": 3, "cultivo": "frijol"},
        ]],
    )
    tipo_tierra: Literal["negra", "arcillosa", "arenosa"] = Field(
        default="negra",
        description="Tipo de suelo: negra (25 d), arcillosa (30 d), arenosa (20 d)",
    )
    riego_veces_semana: int = Field(
        default=0,
        ge=0,
        le=7,
        description="Frecuencia de riegos semanales (0 = temporal)",
    )
    agrego_productos: bool = Field(
        default=False,
        description="¿Agregó fertilizantes o agroquímicos al suelo?",
    )
    considerar_riesgo: bool = Field(
        default=True,
        description="¿Incluir criterio de resiliencia a extremos?",
    )
    prioridad_principal: Literal["agua", "riesgo", "suelo", "igual"] = Field(
        default="igual",
        description="Prioridad declarada por el agricultor",
    )
    region: str = Field(
        default="frailesca",
        description="Región o municipio de Chiapas para perfil agroclimático NASA",
    )

    @model_validator(mode="before")
    @classmethod
    def adaptar_datos_frontend(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "declaracion" in data and isinstance(data["declaracion"], dict):
                inner = dict(data["declaracion"])
                for k, v in data.items():
                    if k != "declaracion" and k not in inner:
                        inner[k] = v
                data = inner

            manejo = data.get("manejo")
            if isinstance(manejo, dict):
                if "riego_veces_semana" in manejo and "riego_veces_semana" not in data:
                    data["riego_veces_semana"] = manejo["riego_veces_semana"]
                if "considerar_riesgo" in manejo and "considerar_riesgo" not in data:
                    data["considerar_riesgo"] = manejo["considerar_riesgo"]
                if "agrego_productos" in manejo and "agrego_productos" not in data:
                    data["agrego_productos"] = manejo["agrego_productos"]
                if "prioridad_principal" in manejo and "prioridad_principal" not in data:
                    data["prioridad_principal"] = manejo["prioridad_principal"]

            suelo = data.get("suelo")
            if isinstance(suelo, dict):
                if "tipo_tierra" in suelo and "tipo_tierra" not in data:
                    data["tipo_tierra"] = suelo["tipo_tierra"]
                if "agrego_productos" in suelo and "agrego_productos" not in data:
                    data["agrego_productos"] = suelo["agrego_productos"]
        return data
