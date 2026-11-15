from pydantic import BaseModel, EmailStr, Field


class CuentaCreateDTO(BaseModel):
    correo: EmailStr = Field(..., examples=["persona@ejemplo.org"])
    contrasena: str = Field(..., min_length=8, examples=["MiClaveSegura2026!"])