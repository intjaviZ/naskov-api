from pydantic import BaseModel, Field


class CuentaResponseDTO(BaseModel):
    id_cuenta: str = Field(..., examples=["c3f2a1b4-7890-4123-9abc-def012345678"])