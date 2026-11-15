from typing import Optional
from fastapi import APIRouter, Depends, Header, status
from app.core.security import validar_api_key
from app.core.dependencies import (
    get_evaluacion_controller,
    obtener_id_cuenta_actual,
    obtener_contexto_token,
)
from app.controllers.evaluacion_controller import EvaluacionController
from app.dtos.evaluacion_create_dto import EvaluacionCreateDTO
from app.dtos.evaluacion_response_dto import EvaluacionResponseDTO
from app.dtos.cifra_explicacion_dto import CifraTrazabilidadDTO

router = APIRouter(prefix="/v1", tags=["Evaluaciones y simulación"])


@router.post(
    "/parcelas/{id_parcela}/evaluaciones",
    response_model=EvaluacionResponseDTO,
    status_code=status.HTTP_201_CREATED,
    operation_id="crearEvaluacionParcela",
    dependencies=[Depends(validar_api_key)],
)
async def evaluar_parcela_endpoint(
    id_parcela: str,
    payload: EvaluacionCreateDTO,
    controller: EvaluacionController = Depends(get_evaluacion_controller),
    authorization: Optional[str] = Header(None),
) -> EvaluacionResponseDTO:
    """
    Contrato 3.4: Evalúa una parcela contra la serie agroclimática NASA 2001-2025,
    ponderaciones multicriterio, regla RC5, simulación Monte Carlo y genera 2 insights con Gemini Flash Lite.
    """
    id_cuenta = None
    if authorization and authorization.lower().startswith("bearer "):
        try:
            from app.core.security import decodificar_token_jwt
            token = authorization.split(" ")[1]
            jwt_data = decodificar_token_jwt(token)
            id_cuenta = jwt_data.get("sub")
        except Exception:
            pass

    return await controller.evaluar_parcela(
        id_parcela=id_parcela,
        payload=payload,
        id_cuenta=id_cuenta,
    )


@router.post(
    "/evaluaciones/simular",
    response_model=EvaluacionResponseDTO,
    status_code=status.HTTP_200_OK,
    operation_id="simularEvaluacionDirecta",
    dependencies=[Depends(validar_api_key)],
)
async def simular_evaluacion_endpoint(
    payload: EvaluacionCreateDTO,
    controller: EvaluacionController = Depends(get_evaluacion_controller),
) -> EvaluacionResponseDTO:
    """
    Simulación directa multicriterio sin requerir persistencia previa en base de datos.
    Permite evaluar escenarios 'qué pasaría si' con los 6 cultivos y Gemini Flash Lite.
    """
    return await controller.simular(payload)


@router.get(
    "/evaluaciones/{id_evaluacion}",
    response_model=EvaluacionResponseDTO,
    status_code=status.HTTP_200_OK,
    operation_id="obtenerEvaluacion",
    dependencies=[Depends(validar_api_key)],
)
async def obtener_evaluacion_endpoint(
    id_evaluacion: str,
    controller: EvaluacionController = Depends(get_evaluacion_controller),
) -> EvaluacionResponseDTO:
    """
    Recupera una evaluación previamente calculada con todos sus escenarios y tarjetas.
    """
    return await controller.obtener_evaluacion(id_evaluacion)


@router.get(
    "/evaluaciones/{id_evaluacion}/cifras/{id_cifra}",
    response_model=CifraTrazabilidadDTO,
    status_code=status.HTTP_200_OK,
    operation_id="obtenerCifraTrazabilidad",
    dependencies=[Depends(validar_api_key)],
)
async def obtener_cifra_endpoint(
    id_evaluacion: str,
    id_cifra: str,
    controller: EvaluacionController = Depends(get_evaluacion_controller),
) -> CifraTrazabilidadDTO:
    """
    Explica el desglose y trazabilidad matemática paso a paso de una cifra (RF11).
    """
    return await controller.obtener_cifra(id_evaluacion, id_cifra)
