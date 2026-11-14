"""
api/domain/tarjetas.py
Modelos y generadores de tarjetas informativas para la interfaz de usuario.
Incluye la tarjeta tradicional de 5 partes y la estructura enriquecida de tarjetas
informativas, de las cuales dos son generadas por Gemini Flash Lite.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TarjetaInformativa(BaseModel):
    id_tarjeta: str
    titulo: str
    subtitulo: Optional[str] = None
    tipo: str  # diagnostico, evidencia_satelital, gemini_insight_agronomico, gemini_insight_resiliencia, manejo_local
    contenido: str
    origen: str  # gemini_flash_lite, determinista_nasa, matriz_chiapas_m1
    icono: str = "sparkles"
    destacado: bool = False
    tags: List[str] = Field(default_factory=list)


class Tarjeta5Partes(BaseModel):
    por_que_se_sugirio: str
    evidencia_agroclimatica: str
    beneficios_posibles: str
    carencias_informacion: str
    riesgos_revision_local: str


def generar_tarjetas_deterministas(
    cultivo_nombre: str,
    es_linea_base: bool,
    puntaje: float,
    criterios: Dict[str, float],
    tipo_tierra: str,
    agrego_productos: bool,
    riego_veces_semana: int,
    advertencias_tierra: Dict[str, str],
    rotacion_4: List[str],
) -> List[TarjetaInformativa]:
    """
    Genera las tarjetas informativas deterministas basadas en datos satelitales NASA y Matriz M1.
    """
    tarjetas: List[TarjetaInformativa] = []

    # 1. Diagnóstico Agroclimático
    if es_linea_base:
        diagnostico = (
            f"Representa tu esquema de manejo actual sembrando {cultivo_nombre} para el Ciclo 4. "
            f"Obtuvo un ajuste global ponderado de {puntaje:.2f}/1.00 contra los 25 años históricos analizados."
        )
    else:
        diagnostico = (
            f"Se propone {cultivo_nombre} para el Ciclo 4 tras la secuencia de cultivos declarada "
            f"({', '.join(rotacion_4[:-1])}). "
            f"Alcanza un puntaje global de {puntaje:.2f}/1.00 adaptándose a tus prioridades."
        )

    tarjetas.append(
        TarjetaInformativa(
            id_tarjeta="card_diagnostico",
            titulo="Diagnóstico Agroclimático",
            subtitulo=f"Ajuste al ciclo: {cultivo_nombre}",
            tipo="diagnostico",
            contenido=diagnostico,
            origen="determinista_nasa",
            icono="award",
            destacado=True,
            tags=["agroclima", "evaluacion"],
        )
    )

    # 2. Evidencia Satelital NASA
    evidencia = (
        f"Precipitación y temperaturas evaluadas sobre la serie satelital NASA IMERG y POWER (2001–2025). "
        f"Ajuste a humedad pluvial: {criterios.get('c_agua', 0.5):.2f}, "
        f"resistencia a extremos y canícula: {criterios.get('c_riesgo', 0.5):.2f}, "
        f"aptitud térmica y de zona: {criterios.get('c_apt', 0.5):.2f}."
    )
    tarjetas.append(
        TarjetaInformativa(
            id_tarjeta="card_evidencia_satelital",
            titulo="Evidencia Satelital Histórica NASA",
            subtitulo="NASA IMERG & NASA POWER (25 años)",
            tipo="evidencia_satelital",
            contenido=evidencia,
            origen="determinista_nasa",
            icono="satellite",
            destacado=False,
            tags=["satelite", "nasa", "clima"],
        )
    )

    # 3. Manejo de Suelo y Observaciones Locales (Sección 8)
    notas_suelo = []
    if agrego_productos:
        notas_suelo.append(
            "Declaraste que agregas productos; esta versión no evalúa cuantitativamente su efecto químico en el suelo."
        )

    tierra_adv = advertencias_tierra.get(tipo_tierra.lower())
    if tierra_adv:
        notas_suelo.append(f"Para tierra {tipo_tierra}: {tierra_adv}.")

    if riego_veces_semana == 0:
        notas_suelo.append("Régimen de temporal estricto (0 riegos semanales declarados).")
    else:
        notas_suelo.append(f"Dispones de {riego_veces_semana} riegos semanales.")

    contenido_suelo = " ".join(notas_suelo) if notas_suelo else f"Tierra {tipo_tierra} con manejo tradicional en Chiapas."

    tarjetas.append(
        TarjetaInformativa(
            id_tarjeta="card_manejo_local",
            titulo="Manejo Local y Suelo",
            subtitulo=f"Condición de tierra {tipo_tierra}",
            tipo="manejo_local",
            contenido=contenido_suelo,
            origen="matriz_chiapas_m1",
            icono="layers",
            destacado=False,
            tags=["suelo", "practica_local"],
        )
    )

    return tarjetas


def ensamblar_tarjeta_5_partes(
    cultivo_nombre: str,
    es_linea_base: bool,
    puntaje: float,
    criterios: Dict[str, float],
    tipo_tierra: str,
    agrego_productos: bool,
    riego_veces_semana: int,
    advertencias_tierra: Dict[str, str],
    gemini_insight_agronomico: Optional[str] = None,
    gemini_insight_resiliencia: Optional[str] = None,
) -> Tarjeta5Partes:
    """
    Construye la tarjeta estándar de 5 partes de NasKob integrando los datos de cálculo
    y los insights especializados de Gemini.
    """
    if es_linea_base:
        por_que = f"Representa tu práctica de manejo declarada. Puntuación global {puntaje:.2f}/1.00 en la serie 2001-2025."
    else:
        por_que = f"Ofrece una opción favorable de rotación para el Ciclo 4 con puntaje {puntaje:.2f}/1.00."

    evidencia = (
        f"Serie NASA IMERG/POWER (2001-2025): Agua {criterios.get('c_agua', 0.5):.2f}, "
        f"Riesgo {criterios.get('c_riesgo', 0.5):.2f}, Suelo {criterios.get('c_suelo', 0.5):.2f}, "
        f"Aptitud {criterios.get('c_apt', 0.5):.2f}."
    )

    beneficios = gemini_insight_agronomico or (
        f"Mejora la diversidad de la parcela y optimiza el aprovechamiento agroclimático en suelo {tipo_tierra}."
    )

    carencias = (
        "Declaraste que agregas productos; esta versión no evalúa cuantitativamente su efecto químico en el suelo."
        if agrego_productos else
        "No considera análisis químico de fertilidad ni plagas imprevistas en laboratorio."
    )

    adv_t = advertencias_tierra.get(tipo_tierra.lower(), "Monitorear drenaje y humedad residual.")
    riesgos = f"{adv_t}. {gemini_insight_resiliencia or 'Verificar pronóstico local a corto plazo.'}"

    return Tarjeta5Partes(
        por_que_se_sugirio=por_que,
        evidencia_agroclimatica=evidencia,
        beneficios_posibles=beneficios,
        carencias_informacion=carencias,
        riesgos_revision_local=riesgos,
    )
