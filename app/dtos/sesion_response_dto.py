from pydantic import BaseModel, Field
from datetime import datetime


class SesionResponseDTO(BaseModel):
    token: str = Field(..., examples=["eyJhbGciOiJIUzI1NiIs..."])
    tipo: str = "Bearer"
    expira_utc: datetime