"""
app/services/gemini_service.py
Servicio de generación de insights con Google Gemini Flash Lite.
"""

from __future__ import annotations
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import httpx

from app.core.config import settings
from app.domain.tarjetas import TarjetaInformativa

logger = logging.getLogger("naskob.gemini")

GEMINI_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
]


class GeminiService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY

    def generar_insights(
        self,
        cultivo_propuesto: str,
        secuencia_4_ciclos: List[str],
        tipo_tierra: str,
        riego_veces_semana: int,
        prioridad_principal: str,
        puntaje_global: float,
        criterios: Dict[str, float],
        region: str = "Frailesca, Chiapas",
    ) -> Tuple[TarjetaInformativa, TarjetaInformativa]:
        if not self.api_key:
            return self._formatear_respuesta(None, cultivo_propuesto, tipo_tierra, riego_veces_semana)

        try:
            prompt = self._construir_prompt(
                cultivo_propuesto,
                secuencia_4_ciclos,
                tipo_tierra,
                riego_veces_semana,
                prioridad_principal,
                puntaje_global,
                criterios,
                region,
            )
            respuesta_json = self._invocar_gemini(prompt)
            return self._formatear_respuesta(respuesta_json, cultivo_propuesto, tipo_tierra, riego_veces_semana)
        except Exception as e:
            logger.warning("Fallo o timeout en Gemini generar_insights: %s", e)
            return self._formatear_respuesta(None, cultivo_propuesto, tipo_tierra, riego_veces_semana)

    async def generar_insights_async(
        self,
        cultivo_propuesto: str,
        secuencia_4_ciclos: List[str],
        tipo_tierra: str,
        riego_veces_semana: int,
        prioridad_principal: str,
        puntaje_global: float,
        criterios: Dict[str, float],
        region: str = "Frailesca, Chiapas",
    ) -> Tuple[TarjetaInformativa, TarjetaInformativa]:
        if not self.api_key:
            return self._formatear_respuesta(None, cultivo_propuesto, tipo_tierra, riego_veces_semana)

        try:
            prompt = self._construir_prompt(
                cultivo_propuesto,
                secuencia_4_ciclos,
                tipo_tierra,
                riego_veces_semana,
                prioridad_principal,
                puntaje_global,
                criterios,
                region,
            )
            respuesta_json = await self._invocar_gemini_async(prompt)
            return self._formatear_respuesta(respuesta_json, cultivo_propuesto, tipo_tierra, riego_veces_semana)
        except Exception as e:
            logger.warning("Fallo o timeout en Gemini generar_insights_async: %s", e)
            return self._formatear_respuesta(None, cultivo_propuesto, tipo_tierra, riego_veces_semana)

    def _sanitizar_texto_ia(self, texto: str) -> str:
        """
        Limpia palabras y frases prescriptivas o predictivas prohibidas por RN-TAR-07 y RN-IA-04.
        """
        reemplazos = [
            (r"\bgarantiza(?:rá|n)?\b", "podría favorecer"),
            (r"\bgarantizar\b", "favorecer"),
            (r"\bproducirá\b", "podría generar"),
            (r"\bproducir\b", "generar"),
            (r"\basegura(?:rá|n)?\b", "favorece"),
            (r"\basegurar cosecha\b", "apoyar el ciclo"),
            (r"\brendirá\b", "se proyecta"),
            (r"\bobtendrás\b", "se estima históricamente"),
            (r"\bdebes sembrar\b", "se sugiere evaluar"),
            (r"\bsiembra esto\b", "una opción a considerar es"),
        ]
        limpio = texto
        for patron, rep in reemplazos:
            limpio = re.sub(patron, rep, limpio, flags=re.IGNORECASE)
        return limpio

    def _formatear_respuesta(
        self,
        respuesta_json: Optional[Dict[str, str]],
        cultivo_propuesto: str,
        tipo_tierra: str,
        riego_veces_semana: int,
    ) -> Tuple[TarjetaInformativa, TarjetaInformativa]:
        insight_agronomico = respuesta_json.get("insight_agronomico") if respuesta_json else None
        insight_resiliencia = respuesta_json.get("insight_resiliencia") if respuesta_json else None

        if insight_agronomico:
            insight_agronomico = self._sanitizar_texto_ia(insight_agronomico)
        else:
            insight_agronomico = self._fallback_agronomico(cultivo_propuesto, tipo_tierra)

        if insight_resiliencia:
            insight_resiliencia = self._sanitizar_texto_ia(insight_resiliencia)
        else:
            insight_resiliencia = self._fallback_resiliencia(
                cultivo_propuesto, tipo_tierra, riego_veces_semana
            )

        tarjeta_1 = TarjetaInformativa(
            id_tarjeta="card_gemini_agronomico",
            titulo="Insight IA: Oportunidades Agronómicas y Nutrición",
            subtitulo="Generado con Gemini Flash-Lite",
            tipo="gemini_insight_agronomico",
            contenido=insight_agronomico,
            origen="gemini_flash_lite",
            icono="sparkles",
            destacado=True,
            tags=["ia_gemini", "nutricion", "rotacion"],
        )

        tarjeta_2 = TarjetaInformativa(
            id_tarjeta="card_gemini_resiliencia",
            titulo="Insight IA: Estrategia Preventiva de Resiliencia Climática",
            subtitulo="Generado con Gemini Flash-Lite",
            tipo="gemini_insight_resiliencia",
            contenido=insight_resiliencia,
            origen="gemini_flash_lite",
            icono="shield",
            destacado=True,
            tags=["ia_gemini", "resiliencia", "clima"],
        )

        return tarjeta_1, tarjeta_2

    def _construir_prompt(
        self,
        cultivo_propuesto: str,
        secuencia_4_ciclos: List[str],
        tipo_tierra: str,
        riego_veces_semana: int,
        prioridad_principal: str,
        puntaje_global: float,
        criterios: Dict[str, float],
        region: str,
    ) -> str:
        secuencia_str = " -> ".join(secuencia_4_ciclos)
        regimen_agua = (
            "temporal estricto (0 riegos)"
            if riego_veces_semana == 0
            else f"{riego_veces_semana} riegos/semana"
        )

        return f"""Eres un ingeniero agrónomo especialista en Chiapas, México para la plataforma NasKob (NASA Space Apps).
Analiza el siguiente escenario agroclimático para un pequeño productor:
- Ubicación: {region}
- Secuencia de rotación (4 ciclos): {secuencia_str}
- Cultivo candidato evaluado para Ciclo 4: {cultivo_propuesto}
- Suelo declarado: tierra {tipo_tierra}
- Régimen hídrico: {regimen_agua}
- Prioridad del productor: {prioridad_principal}
- Puntaje de ajuste histórico NASA: {puntaje_global:.2f}/1.00 (Agua: {criterios.get('c_agua', 0.5):.2f}, Riesgo: {criterios.get('c_riesgo', 0.5):.2f}, Suelo: {criterios.get('c_suelo', 0.5):.2f}, Aptitud térmica: {criterios.get('c_apt', 0.5):.2f})

Redacta EXACTAMENTE dos (2) insights prácticos y fundamentados para el agricultor (máximo 2 a 3 oraciones cada uno, lenguaje directo y sin tecnicismos excesivos):
1. 'insight_agronomico': Explicar la sinergia biológica de sembrar {cultivo_propuesto} tras los ciclos previos, balance de nitrógeno y prevención de plagas de raíz.
2. 'insight_resiliencia': Consejo preventivo ante la canícula, rachas secas o calor en suelo {tipo_tierra}, y manejo de la humedad.

Responde ÚNICAMENTE un objeto JSON válido con estas dos claves:
{{
  "insight_agronomico": "...",
  "insight_resiliencia": "..."
}}
"""

    def _limpiar_json(self, raw_text: str) -> Optional[Dict[str, str]]:
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()
        raw_text = re.sub(r',\s*([\]\}])', r'\1', raw_text)
        try:
            parsed = json.loads(raw_text)
            if "insight_agronomico" in parsed and "insight_resiliencia" in parsed:
                return parsed
        except Exception:
            pass
        return None

    def _invocar_gemini(self, prompt: str) -> Optional[Dict[str, str]]:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1200,
            },
        }

        for model in GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            try:
                with httpx.Client(timeout=3.0) as client:
                    resp = client.post(url, json=payload, headers={"Content-Type": "application/json"})
                    if resp.status_code == 200:
                        data = resp.json()
                        cands = data.get("candidates", [])
                        if cands and "content" in cands[0] and "parts" in cands[0]["content"]:
                            raw_text = cands[0]["content"]["parts"][0].get("text", "").strip()
                            parsed = self._limpiar_json(raw_text)
                            if parsed:
                                return parsed
            except Exception as e:
                logger.warning("Fallo al consultar Gemini model %s: %s", model, e)
                continue

        return None

    async def _invocar_gemini_async(self, prompt: str) -> Optional[Dict[str, str]]:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1200,
            },
        }

        for model in GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
                    if resp.status_code == 200:
                        data = resp.json()
                        cands = data.get("candidates", [])
                        if cands and "content" in cands[0] and "parts" in cands[0]["content"]:
                            raw_text = cands[0]["content"]["parts"][0].get("text", "").strip()
                            parsed = self._limpiar_json(raw_text)
                            if parsed:
                                return parsed
            except Exception as e:
                logger.warning("Fallo al consultar Gemini model async %s: %s", model, e)
                continue

        return None

    def _fallback_agronomico(self, cultivo: str, tierra: str) -> str:
        c_clean = cultivo.lower().strip()
        if c_clean == "frijol":
            return (
                f"Sembrar frijol en el Ciclo 4 aporta fijación biológica de nitrógeno tras los ciclos previos, "
                f"rompiendo el ciclo de plagas del suelo como la gallina ciega y mejorando la fertilidad en tierra {tierra}."
            )
        elif c_clean == "calabaza":
            return (
                f"La calabaza ofrece una cobertura foliar extensa que protege la tierra {tierra} de la erosión hídrica "
                f"y suprime el crecimiento de malezas competidoras."
            )
        elif c_clean == "cacahuate":
            return (
                f"El cacahuate diversifica la parcela y explora un estrato radicular diferente, "
                f"favoreciendo la porosidad del suelo {tierra} y facilitando la cosecha si se mantiene buen drenaje."
            )
        elif c_clean in ["sandia", "habanero"]:
            return (
                f"Cultivo de alto valor comercial que diversifica la rotación, exigiendo monitoreo fitosanitario "
                f"contra pudriciones radiculares en tierra {tierra}."
            )
        else:
            return f"El cultivo de {cultivo} en suelo {tierra} aporta biomasa y estabilidad al lote."

    def _fallback_resiliencia(self, cultivo: str, tierra: str, riego: int) -> str:
        if riego == 0:
            return (
                f"En temporal estricto sobre tierra {tierra}, programa la siembra con el establecimiento firme de lluvias "
                f"en mayo-junio para que la etapa crítica no coincida con el pico de la canícula de agosto."
            )
        else:
            return (
                f"Aprovecha los {riego} riegos semanales disponibles para asegurar humedad constante durante la floración "
                f"y cuajado, previniendo estrés térmico en las semanas de mayor calor."
            )
