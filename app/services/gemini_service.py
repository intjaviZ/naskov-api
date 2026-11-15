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
    settings.GEMINI_MODEL,
    "gemini-flash-lite-latest",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-flash-latest",
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
        region: str = "Chiapas, México",
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
        region: str = "Chiapas, México",
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
        Limpia palabras y frases prescriptivas o predictivas prohibidas por RN-TAR-07, RN-IA-04, R4 y RC1.
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
            # Prohibición de predecir o asegurar prevención/eliminación de plagas (RC1, R4, RN-TAR-04)
            (r"\bpreviene (?:las )?plagas\b", "no acumula el mismo hospedero continuo"),
            (r"\bpreviene la plaga\b", "diversifica el lote frente a plagas"),
            (r"\bevita (?:las )?plagas\b", "busca diversificar hospederos"),
            (r"\bevita la presencia de plagas\b", "no asegura la ausencia de plagas"),
            (r"\belimina (?:las )?plagas\b", "interrumpe la continuidad biológica"),
            (r"\berradica (?:las )?plagas\b", "diversifica la rotación"),
            (r"\bpreviene enfermedades\b", "busca reducir la exposición a patógenos"),
            (r"\bevita enfermedades\b", "reduce la acumulación de hospederos"),
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
        insight_agronomico = None
        insight_resiliencia = None

        if respuesta_json:
            insight_agronomico = (
                respuesta_json.get("beneficios_posibles")
                or respuesta_json.get("insight_agronomico")
            )
            insight_resiliencia = (
                respuesta_json.get("riesgos_revision_local")
                or respuesta_json.get("insight_resiliencia")
            )

        if insight_agronomico:
            insight_agronomico = self._sanitizar_texto_ia(str(insight_agronomico))
        else:
            insight_agronomico = self._fallback_agronomico(cultivo_propuesto, tipo_tierra)

        if insight_resiliencia:
            insight_resiliencia = self._sanitizar_texto_ia(str(insight_resiliencia))
        else:
            insight_resiliencia = self._fallback_resiliencia(
                cultivo_propuesto, tipo_tierra, riego_veces_semana
            )

        tarjeta_1 = TarjetaInformativa(
            id_tarjeta="card_gemini_agronomico",
            titulo="Punto 4: Beneficios Posibles y Sinergia Agronómica",
            subtitulo="Generado con Gemini Flash-Lite",
            tipo="gemini_insight_agronomico",
            contenido=insight_agronomico,
            origen="gemini_flash_lite",
            icono="sparkles",
            destacado=True,
            tags=["ia_gemini", "beneficios_posibles", "nutricion", "rotacion"],
        )

        tarjeta_2 = TarjetaInformativa(
            id_tarjeta="card_gemini_resiliencia",
            titulo="Punto 5: Riesgos para la Revisión Local y Clima",
            subtitulo="Generado con Gemini Flash-Lite",
            tipo="gemini_insight_resiliencia",
            contenido=insight_resiliencia,
            origen="gemini_flash_lite",
            icono="shield",
            destacado=True,
            tags=["ia_gemini", "riesgos_revision_local", "resiliencia", "clima"],
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

        return f"""Eres un ingeniero agrónomo especialista en el estado de Chiapas, México para la plataforma agroclimática NasKob (NASA Space Apps).
Analiza el siguiente escenario para un productor agrícola:
- Ubicación de la parcela: {region}
- Secuencia de rotación (4 ciclos): {secuencia_str}
- Cultivo candidato evaluado para Ciclo 4: {cultivo_propuesto}
- Suelo declarado: tierra {tipo_tierra}
- Régimen hídrico: {regimen_agua}
- Prioridad del productor: {prioridad_principal}
- Puntaje de ajuste histórico NASA: {puntaje_global:.2f}/1.00 (Agua: {criterios.get('c_agua', 0.5):.2f}, Riesgo: {criterios.get('c_riesgo', 0.5):.2f}, Suelo: {criterios.get('c_suelo', 0.5):.2f}, Aptitud térmica: {criterios.get('c_apt', 0.5):.2f})

REGLAS OBLIGATORIAS DEL SISTEMA NASKOB (CUMPLIMIENTO ESTRICTO):
1. REGLA DE NO-PREDICCIÓN DE PLAGAS NI ENFERMEDADES (RC1, R4, RN-TAR-04, RN-TAR-05):
   - NUNCA afirmes que la rotación "previene plagas", "evita plagas", "elimina" o "erradica" plagas ni enfermedades.
   - NasKob NO monitorea plagas en tiempo real y los satélites de la NASA NO detectan insectos subterráneos, hongos ni bacterias del suelo.
   - Las plagas de suelo del maíz (gallina ciega y gusano de alambre) son riesgos biológicos conocidos que no son evaluados por satélite y deben revisarse físicamente en campo. La rotación de familias botánicas solo busca diversificar y no mantener el mismo hospedero continuo, pero NO asegura la ausencia de plagas ni garantiza sanidad.

2. REGLA DE NO-PREDICCIÓN DE RENDIMIENTOS (R4, RN-TAR-07, RN-IA-04):
   - PROHIBIDO predecir cosechas, toneladas por hectárea o usar palabras deterministas como "producirá", "garantiza", "asegura", "obtendrás", "rendirá".

3. REGLA DE LENGUAJE CONDICIONAL Y NO PRESCRIPTIVO (RN-TAR-07, RN-IA-04):
   - PROHIBIDO ordenar o prescribir ("debes sembrar", "siembra esto", "tienes que"). Usa siempre lenguaje condicional ("podría favorecer", "tiende a", "con tus prioridades declaradas").

4. REGLA DE NO-PRONÓSTICO CLIMÁTICO FUTURO (R4):
   - El sistema NO pronostica el clima del próximo año; evalúa únicamente el historial de 25 años NASA (2001–2025). Habla de comportamiento histórico en la serie analizada.

5. REGLA DE UBICACIÓN (TODO CHIAPAS):
   - La plataforma opera en todo el estado de Chiapas. Basa el análisis en la ubicación declarada ({region}).
   - NO menciones "La Frailesca" a menos que la ubicación diga explícitamente "Frailesca".

6. REGLA DE AVISO DE APOYO A LA DECISIÓN (RN-TAR-06, RF17):
   - En Punto 5 ("riesgos_revision_local"), concluye recordando que esta evaluación satelital histórica es una herramienta de orientación que complementa y no sustituye el criterio del productor ni la asesoría técnica local.

7. REGLA DE FORMATO, EXTENSIÓN Y LEGIBILIDAD:
   - Cada sección debe tener exactamente entre 3 y 4 oraciones concisas y directas (alrededor de 80 a 110 palabras por sección).
   - Ve directo al grano: NO uses saludos ("Estimado productor...") ni fórmulas de despedida. Inicia de inmediato con el análisis agronómico y el factor técnico.

1. Punto 4 - "beneficios_posibles":
   Explica en 3 a 4 oraciones directas:
   - Sinergia biológica y balance de nutrientes tras la rotación ({secuencia_str}), destacando la nutrición para tierra {tipo_tierra} (fijación biológica de nitrógeno si es leguminosa o aprovechamiento residual).
   - Cómo alternar familias botánicas busca diversificar hospederos frente a riesgos conocidos de suelo del maíz (gallina ciega y gusano de alambre), aclarando que no previene ni elimina su presencia.
   - Mejora gradual en porosidad, aireación y microbiología del suelo {tipo_tierra}.
   - Cumple con lenguaje condicional sin prometer rendimientos absolutos ni frases prohibidas ("garantiza", "asegura cosecha", "debes sembrar").

2. Punto 5 - "riesgos_revision_local":
   Explica en 3 a 4 oraciones directas:
   - Factores de riesgo agroclimático en {region} bajo {regimen_agua}, alertando sobre el impacto histórico de la canícula o calor en floración.
   - Retos del suelo {tipo_tierra} (drenaje lento y riesgo de asfixia radicular/hongos si es arcillosa; deshidratación y lixiviación si es arenosa).
   - Recomendación práctica de revisión en campo (verificar humedad a 15-20 cm de profundidad, drenaje superficial e inspección física de plagas no detectadas por satélite) y recordatorio de que esta guía tecnológica apoya las decisiones pero no sustituye la asesoría técnica local.

Responde ÚNICAMENTE un objeto JSON válido con esta estructura:
{{
  "beneficios_posibles": "Explicación directa de 3-4 oraciones...",
  "riesgos_revision_local": "Explicación directa de 3-4 oraciones..."
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
            b_val = parsed.get("beneficios_posibles") or parsed.get("insight_agronomico")
            r_val = parsed.get("riesgos_revision_local") or parsed.get("insight_resiliencia")
            if b_val and r_val:
                return {
                    "beneficios_posibles": str(b_val).strip(),
                    "riesgos_revision_local": str(r_val).strip(),
                    "insight_agronomico": str(b_val).strip(),
                    "insight_resiliencia": str(r_val).strip(),
                }
        except Exception:
            pass
        return None

    def _invocar_gemini(self, prompt: str) -> Optional[Dict[str, str]]:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 3500,
            },
        }

        for model in GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            try:
                with httpx.Client(timeout=12.0) as client:
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
                "maxOutputTokens": 3500,
            },
        }

        for model in GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            try:
                async with httpx.AsyncClient(timeout=12.0) as client:
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
        t_clean = tierra.lower().strip()
        if c_clean == "frijol":
            return (
                f"Sembrar frijol en el Ciclo 4 aporta una sinergia biológica mediante la fijación natural de nitrógeno "
                f"en nódulos radiculares, favoreciendo la fertilidad de la tierra {t_clean}. Esta rotación diversifica las familias botánicas "
                f"frente a riesgos conocidos de suelo del maíz como la gallina ciega y el gusano de alambre, sin asegurar su ausencia total. "
                f"Asimismo, su sistema radicular genera microcanales que podrían favorecer la porosidad y microbiología del suelo."
            )
        elif c_clean == "calabaza":
            return (
                f"La calabaza ofrece una cobertura foliar extensa que protege la tierra {t_clean} contra la erosión y suprime "
                f"malezas competidoras, aportando abundante biomasa fresca. Al alternar con gramíneas, diversifica hospederos frente a plagas "
                f"conocidas de suelo del maíz como la gallina ciega y el gusano de alambre, aunque esta práctica no elimina dichos insectos. "
                f"Su cultivo favorece la conservación de humedad biológica y estimula la actividad microbiana benéfica en la parcela."
            )
        elif c_clean == "cacahuate":
            return (
                f"El cacahuate actúa como leguminosa fijadora de nitrógeno que explora un estrato radicular diferente, mejorando "
                f"la porosidad y estructura en tierra {t_clean}. Su inclusión en la rotación diversifica hospederos biológicos frente a "
                f"riesgos de suelo como la gallina ciega y el gusano de alambre, dejando fertilidad residual para los siguientes ciclos."
            )
        elif c_clean in ["sandia", "habanero"]:
            return (
                f"Este cultivo diversifica los estratos de absorción de nutrientes e interrumpe la continuidad botánica del monocultivo anterior. "
                f"Diversifica la parcela frente a riesgos de plagas del suelo asociadas al maíz como la gallina ciega y el gusano de alambre en Chiapas. "
                f"Su manejo intensivo estimula la actividad microbiológica y favorece la aireación en tierra {t_clean}."
            )
        else:
            return (
                f"La inclusión de {cultivo} en el Ciclo 4 aporta diversidad biológica a la parcela, diversificando hospederos "
                f"frente a riesgos de plagas del suelo del maíz (gallina ciega y gusano de alambre) y favoreciendo la porosidad en tierra {t_clean}."
            )

    def _fallback_resiliencia(self, cultivo: str, tierra: str, riego: int) -> str:
        t_clean = tierra.lower().strip()
        regimen = "temporal estricto (0 riegos)" if riego == 0 else f"{riego} riegos semanales"

        if t_clean == "arcillosa":
            obs_suelo = "En tierra arcillosa, el drenaje tiende a ser lento; ante lluvias intensas vigile zanjas para evitar asfixia radicular y hongos."
        elif t_clean == "arenosa":
            obs_suelo = "En tierra arenosa, la retención de agua es baja; preste atención a la deshidratación rápida durante días secos continuos."
        else:
            obs_suelo = f"En tierra {t_clean}, monitoree periódicamente la infiltración para evitar sellado o compactación superficial."

        if riego == 0:
            obs_clima = f"Bajo {regimen}, el cultivo es sensible a la canícula (agosto) y rachas de calor que podrían estresar la floración."
        else:
            obs_clima = f"Bajo {regimen}, distribuya los riegos para amortiguar el calor extremo y el periodo de canícula."

        return (
            f"{obs_clima} {obs_suelo} Se recomienda validar en campo la humedad a 15-20 cm antes de sembrar, "
            f"recordando que esta evaluación es una herramienta de orientación que no sustituye la asesoría técnica local."
        )
