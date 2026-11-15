from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class NasKobException(Exception):
    def __init__(
        self,
        estado: int,
        codigo: str,
        titulo: str,
        detalle: str,
        campo: str | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.estado = estado
        self.codigo = codigo
        self.titulo = titulo
        self.detalle = detalle
        self.campo = campo
        self.headers = headers


# Fábricas de errores exactos de la Sección 5 del Contrato v1.2
class ErroresContrato:
    @staticmethod
    def solicitud_invalida(detalle: str, campo: str | None = None) -> NasKobException:
        return NasKobException(400, "solicitud_invalida", "Solicitud inválida", detalle, campo)

    @staticmethod
    def no_autenticado(detalle: str = "Falta el token de sesión, venció o la clave de cliente no es válida.") -> NasKobException:
        return NasKobException(401, "no_autenticado", "No autenticado", detalle)

    @staticmethod
    def credenciales_invalidas() -> NasKobException:
        return NasKobException(401, "credenciales_invalidas", "Credenciales inválidas", "Correo o contraseña incorrectos al iniciar sesión.")

    @staticmethod
    def no_encontrado(recurso: str = "Recurso") -> NasKobException:
        return NasKobException(404, "no_encontrado", "No encontrado", f"{recurso} inexistente o pertenece a otra cuenta.")

    @staticmethod
    def conflicto_version() -> NasKobException:
        return NasKobException(409, "conflicto_version", "Conflicto de versión", "Se pide evaluar una versión de declaración que ya no es la vigente.", "version_declaracion")

    @staticmethod
    def correo_ya_registrado() -> NasKobException:
        return NasKobException(409, "correo_ya_registrado", "Correo ya registrado", "Ya existe una cuenta con ese correo.", "correo")

    @staticmethod
    def region_no_preparada() -> NasKobException:
        return NasKobException(422, "region_no_preparada", "Región no preparada", "La parcela está fuera de una región con series precalculadas.")

    @staticmethod
    def datos_insuficientes(motivo: str) -> NasKobException:
        return NasKobException(422, "datos_insuficientes", "Datos insuficientes", motivo)

    @staticmethod
    def parcela_fuera_de_rango() -> NasKobException:
        return NasKobException(422, "parcela_fuera_de_rango", "Parcela fuera de rango", "El área de la parcela está fuera del rango de 1 a 10 ha.")

    @staticmethod
    def limite_excedido(retry_after: int = 60) -> NasKobException:
        return NasKobException(
            429, "limite_excedido", "Límite de consultas excedido",
            "Se superó el límite de consultas; intente más tarde.",
            headers={"Retry-After": str(retry_after)},
        )

    @staticmethod
    def fuente_degradada(detalle: str) -> NasKobException:
        return NasKobException(503, "fuente_degradada", "Fuente degradada", detalle)


async def naskob_exception_handler(request: Request, exc: NasKobException) -> JSONResponse:
    contenido = {
        "tipo": f"https://api.naskob.org/errores/{exc.codigo}",
        "titulo": exc.titulo,
        "estado": exc.estado,
        "detalle": exc.detalle,
        "codigo": exc.codigo,
    }
    if exc.campo:
        contenido["campo"] = exc.campo

    return JSONResponse(
        status_code=exc.estado,
        content=contenido,
        media_type="application/problem+json",
        headers=exc.headers,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    primer_error = exc.errors()[0] if exc.errors() else {}
    loc = primer_error.get("loc", [])
    campo = str(loc[-1]) if len(loc) > 1 else None
    msg = primer_error.get("msg", "Cuerpo mal formado o valor fuera de rango.")

    contenido = {
        "tipo": "https://api.naskob.org/errores/solicitud_invalida",
        "titulo": "Solicitud inválida",
        "estado": 400,
        "detalle": f"Error de validación: {msg}",
        "codigo": "solicitud_invalida",
    }
    if campo:
        contenido["campo"] = campo

    return JSONResponse(
        status_code=400,
        content=contenido,
        media_type="application/problem+json",
    )