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
from app.dtos.evaluacion_response_dto import (
    EvaluacionResponseDTO,
    SensibilidadRequestDTO,
    SensibilidadResponseDTO,
    TextosIAResponseDTO,
    ExportacionRequestDTO,
    ExportacionResponseDTO,
)
from app.dtos.escenario_tarjeta_dto import EscenarioDetalleDTO
from app.dtos.cifra_explicacion_dto import CifraTrazabilidadDTO

router = APIRouter(prefix="/v1", tags=["Evaluaciones (comparador de escenarios)"])


@router.post(
    "/parcelas/{id_parcela}/evaluaciones",
    response_model=EvaluacionResponseDTO,
    status_code=status.HTTP_201_CREATED,
    operation_id="evaluar",
    name="evaluar",
    summary="Evalúa una versión de declaración con el motor de reglas.",
    dependencies=[Depends(validar_api_key)],
)
async def evaluar(
    id_parcela: str,
    payload: EvaluacionCreateDTO,
    controller: EvaluacionController = Depends(get_evaluacion_controller),
    authorization: Optional[str] = Header(None),
) -> EvaluacionResponseDTO:
    """
    Evalúa una versión de declaración con el motor de reglas determinista y satelital NASA 2001-2025.
    Genera escenarios de rotación, Monte Carlo y 2 insights estructurados con Gemini Flash Lite.
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


@router.get(
    "/evaluaciones/{id_evaluacion}",
    response_model=EvaluacionResponseDTO,
    status_code=status.HTTP_200_OK,
    operation_id="obtenerEvaluacion",
    name="obtenerEvaluacion",
    summary="Lista de 3 a 5 escenarios (A primero) con puntaje, rango, Δ frente a A, robustez, confianza y escenarios descartados con motivo.",
    dependencies=[Depends(validar_api_key)],
)
async def obtener_evaluacion(
    id_evaluacion: str,
    controller: EvaluacionController = Depends(get_evaluacion_controller),
) -> EvaluacionResponseDTO:
    return await controller.obtener_evaluacion(id_evaluacion)


@router.get(
    "/evaluaciones/{id_evaluacion}/escenarios/{id_escenario}",
    response_model=EscenarioDetalleDTO,
    status_code=status.HTTP_200_OK,
    operation_id="obtenerEscenario",
    name="obtenerEscenario",
    summary="Tarjeta completa con las cinco partes y el aviso de apoyo.",
    dependencies=[Depends(validar_api_key)],
)
async def obtener_escenario(
    id_evaluacion: str,
    id_escenario: str,
    controller: EvaluacionController = Depends(get_evaluacion_controller),
) -> EscenarioDetalleDTO:
    return await controller.obtener_escenario(id_evaluacion, id_escenario)


@router.get(
    "/evaluaciones/{id_evaluacion}/cifras/{id_cifra}",
    response_model=CifraTrazabilidadDTO,
    status_code=status.HTTP_200_OK,
    operation_id="obtenerCifra",
    name="obtenerCifra",
    summary="Panel «¿por qué?»: indicador, fuente, fecha, parámetros y versión de regla.",
    dependencies=[Depends(validar_api_key)],
)
async def obtener_cifra(
    id_evaluacion: str,
    id_cifra: str,
    controller: EvaluacionController = Depends(get_evaluacion_controller),
) -> CifraTrazabilidadDTO:
    return await controller.obtener_cifra(id_evaluacion, id_cifra)


@router.post(
    "/evaluaciones/{id_evaluacion}/sensibilidad",
    response_model=SensibilidadResponseDTO,
    status_code=status.HTTP_200_OK,
    operation_id="evaluarSensibilidad",
    name="evaluarSensibilidad",
    summary="Reevalúa sobre el historial con variante = mas_seco, mas_calido o secuencia_seca_adicional.",
    dependencies=[Depends(validar_api_key)],
)
async def evaluar_sensibilidad(
    id_evaluacion: str,
    payload: SensibilidadRequestDTO,
    controller: EvaluacionController = Depends(get_evaluacion_controller),
) -> SensibilidadResponseDTO:
    return await controller.evaluar_sensibilidad(id_evaluacion, payload.variante)


@router.get(
    "/evaluaciones/{id_evaluacion}/textos",
    response_model=TextosIAResponseDTO,
    status_code=status.HTTP_200_OK,
    operation_id="obtenerTextos",
    name="obtenerTextos",
    summary="Texto de IA-2 por escenario con resultado de cada control, o la plantilla si se descartó.",
    dependencies=[Depends(validar_api_key)],
)
async def obtener_textos(
    id_evaluacion: str,
    controller: EvaluacionController = Depends(get_evaluacion_controller),
) -> TextosIAResponseDTO:
    return await controller.obtener_textos(id_evaluacion)


@router.post(
    "/evaluaciones/{id_evaluacion}/exportaciones",
    response_model=ExportacionResponseDTO,
    status_code=status.HTTP_200_OK,
    operation_id="crearExportacion",
    name="crearExportacion",
    summary="Genera un resumen con formato = json, csv o pdf, con pesos, versión y fecha, sin geometría exacta.",
    dependencies=[Depends(validar_api_key)],
)
async def crear_exportacion(
    id_evaluacion: str,
    payload: ExportacionRequestDTO,
    controller: EvaluacionController = Depends(get_evaluacion_controller),
) -> ExportacionResponseDTO:
    return await controller.exportar(id_evaluacion, payload.formato)


@router.post(
    "/evaluaciones/simular",
    response_model=EvaluacionResponseDTO,
    status_code=status.HTTP_200_OK,
    operation_id="simularEvaluacionDirecta",
    name="simularEvaluacionDirecta",
    summary="Simulación directa multicriterio sin requerir persistencia previa en base de datos.",
    dependencies=[Depends(validar_api_key)],
)
async def simular_evaluacion_endpoint(
    payload: EvaluacionCreateDTO,
    controller: EvaluacionController = Depends(get_evaluacion_controller),
) -> EvaluacionResponseDTO:
    return await controller.simular(payload)
