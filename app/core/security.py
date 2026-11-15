import uuid
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Security
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.exceptions import ErroresContrato

# Esquemas exactos del Anexo A del Contrato v1.2
api_key_scheme = APIKeyHeader(name="X-Api-Key", scheme_name="claveCliente", auto_error=False)
bearer_scheme = HTTPBearer(scheme_name="tokenSesion", auto_error=False)


def hashear_contrasena(contrasena_plana: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(contrasena_plana.encode("utf-8"), salt).decode("utf-8")


def verificar_contrasena(contrasena_plana: str, hash_guardado: str) -> bool:
    return bcrypt.checkpw(contrasena_plana.encode("utf-8"), hash_guardado.encode("utf-8"))


def crear_token_jwt(id_cuenta: str) -> tuple[str, str, datetime]:
    ahora = datetime.now(timezone.utc)
    expira = ahora + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    jti = str(uuid.uuid4())
    payload = {
        "sub": id_cuenta,
        "jti": jti,
        "iat": ahora,
        "exp": expira,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expira


def decodificar_token_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise ErroresContrato.no_autenticado()


async def validar_api_key(api_key: str | None = Security(api_key_scheme)) -> str:
    if not api_key or api_key != settings.PWA_API_KEY:
        raise ErroresContrato.no_autenticado("La clave de cliente (X-Api-Key) falta o no es válida.")
    return api_key