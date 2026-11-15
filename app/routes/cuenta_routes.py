from fastapi import APIRouter, Depends, Response, status
from app.core.security import validar_api_key
from app.core.dependencies import (
    get_cuenta_controller,
    obtener_contexto_token,
    get_sesion_controller,
)
from app.controllers.cuenta_controller import CuentaController
from app.controllers.sesion_controller import SesionController
from app.dtos.cuenta_create_dto import CuentaCreateDTO
from app.dtos.cuenta_response_dto import CuentaResponseDTO

router = APIRouter(prefix="/v1", tags=["Cuenta y sesión"])


@router.post(
    "/cuentas",
    response_model=CuentaResponseDTO,
    status_code=status.HTTP_201_CREATED,
    operation_id="crearCuenta",
    dependencies=[Depends(validar_api_key)],
)
async def crear_cuenta_endpoint(
    payload: CuentaCreateDTO,
    controller: CuentaController = Depends(get_cuenta_controller),
) -> CuentaResponseDTO:
    return await controller.crear_cuenta(payload)


@router.delete(
    "/cuenta",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="borrarCuenta",
)
async def borrar_cuenta_endpoint(
    ctx: dict = Depends(obtener_contexto_token),
    cuenta_controller: CuentaController = Depends(get_cuenta_controller),
    sesion_controller: SesionController = Depends(get_sesion_controller),
) -> Response:
    await sesion_controller.cerrar_sesion_actual(ctx["jti"])
    await cuenta_controller.eliminar_cuenta(ctx["id_cuenta"])
    return Response(status_code=status.HTTP_204_NO_CONTENT)