from pydantic import BaseModel, EmailStr, Field


class SesionCreateDTO(BaseModel):
    correo: EmailStr = Field(..., examples=["persona@ejemplo.org"])
    contrasena: str = Field(..., examples=["MiClaveSegura2026!"])