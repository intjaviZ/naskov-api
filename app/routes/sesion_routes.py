from fastapi import APIRouter, Depends, Response, status
from app.core.security import validar_api_key
from app.core.dependencies import (
    get_sesion_controller,
    obtener_contexto_token,
)
from app.controllers.sesion_controller import SesionController
from app.dtos.sesion_create_dto import SesionCreateDTO
from app.dtos.sesion_response_dto import SesionResponseDTO

router = APIRouter(prefix="/v1/sesiones", tags=["Cuenta y sesión"])


@router.post(
    "",
    response_model=SesionResponseDTO,
    status_code=status.HTTP_201_CREATED,
    operation_id="iniciarSesion",
    dependencies=[Depends(validar_api_key)],
)
async def iniciar_sesion_endpoint(
    payload: SesionCreateDTO,
    controller: SesionController = Depends(get_sesion_controller),
) -> SesionResponseDTO:
    return await controller.iniciar_sesion(payload)


@router.delete(
    "/actual",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="cerrarSesion",
)
async def cerrar_sesion_endpoint(
    ctx: dict = Depends(obtener_contexto_token),
    controller: SesionController = Depends(get_sesion_controller),
) -> Response:
    await controller.cerrar_sesion_actual(ctx["jti"], ctx["id_cuenta"])
    return Response(status_code=status.HTTP_204_NO_CONTENT)