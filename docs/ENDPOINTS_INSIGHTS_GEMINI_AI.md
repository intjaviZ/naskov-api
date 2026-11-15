# NasKob · Endpoints e Integración de Insights con Gemini Flash Lite

Este documento detalla la arquitectura, el funcionamiento y los endpoints de la API de **NasKob** encargados de generar y exponer los **insights agronómicos y de resiliencia climática** mediante inteligencia artificial con **Google Gemini Flash Lite**, en estricto cumplimiento con el documento `NasKob_APIs_API-First.docx` y las reglas de negocio agroclimáticas (RN-IA-04, RN-IA-06, RN-IA-09, RN-TAR-07 y RNF17).

---

## 1. Arquitectura de Integración con Gemini Flash Lite

NasKob utiliza un enfoque híbrido:
1. **Motor Agroclimático Determinista (Capa de Dominio):** Calcula de manera determinista los 4 criterios agronómicos ($c_{agua}, c_{riesgo}, c_{suelo}, c_{apt}$) y ejecuta la simulación Monte Carlo de 1,000 réplicas usando 25 años de series satelitales NASA (GPM IMERG y NASA POWER).
2. **Generación de Insights con Gemini Flash Lite (Capa de Aplicación):** Se invoca a Google Gemini Flash Lite exclusivamente para el escenario alternativo ganador, sintetizando la sinergia biológica y las recomendaciones prácticas para el agricultor en Chiapas.

### Modelos y Fallback
- **Modelos invocados:** `gemini-flash-lite-latest`, `gemini-3.1-flash-lite`, `gemini-3.5-flash-lite`.
- **Hiperparámetros:** `temperature = 0.2` (enfoque factual y de baja alucinación), `maxOutputTokens = 1200`.
- **Timeout estricto:** 3.0 segundos tanto en llamadas síncronas como asíncronas (`httpx.Client(timeout=3.0)` y `httpx.AsyncClient(timeout=3.0)`).
- **Fallback Determinista:** Si la red se degrada o la API de Gemini agota cuota, se activa una plantilla agronómica determinista basada en el cultivo y tipo de tierra, garantizando alta disponibilidad sin interrumpir la experiencia del productor.

---

## 2. Los Dos (2) Insights Generados por IA

Gemini Flash Lite genera exactamente dos tarjetas estructuradas identificadas con `origen: "gemini_flash_lite"`:

### 2.1 Insight 1: Oportunidades Agronómicas y Nutrición (`card_gemini_agronomico`)
- **Tipo:** `gemini_insight_agronomico`
- **Enfoque:**
  - Sinergia biológica al introducir el cultivo propuesto tras los 3 ciclos previos.
  - Balance nutricional de nitrógeno ($q_N$): fijación biológica en leguminosas (frijol/cacahuate) o recuperación tras gramíneas extractoras (maíz).
  - Rompimiento del ciclo biológico de plagas del suelo (ej. gallina ciega o nematodos).

### 2.2 Insight 2: Manejo de Riesgo y Resiliencia Climática (`card_gemini_resiliencia`)
- **Tipo:** `gemini_insight_resiliencia`
- **Enfoque:**
  - Mitigación del estrés hídrico durante la canícula o rachas secas históricas de la región (Frailesca).
  - Adaptación térmica y manejo de cobertura según la textura del suelo (`arcillosa`, `migajon`, `arenosa`).
  - Eficiencia en el aprovechamiento de la humedad de temporal o régimen de riego disponible.

---

## 3. Catálogo de Endpoints de Insights de IA

Los insights de Gemini Flash Lite se consumen a través de cinco (5) endpoints de la API REST:

| Método | Endpoint | `operation_id` | Propósito | Requerimiento |
| :--- | :--- | :--- | :--- | :--- |
| **`GET`** | **`/v1/evaluaciones/{id_evaluacion}/textos`** | `obtenerTextos` | **Endpoint exclusivo de IA:** Devuelve únicamente los insights de Gemini y la descripción textual de escenarios. | **RF16 (Texto IA)** |
| **`POST`** | **`/v1/parcelas/{id_parcela}/evaluaciones`** | `evaluar` | Evalúa la parcela, invoca a Gemini Flash Lite en tiempo real e inserta los insights en el escenario recomendado. | **RF08 / RF10** |
| **`GET`** | **`/v1/evaluaciones/{id_evaluacion}`** | `obtenerEvaluacion` | Recupera la evaluación completa con todos los escenarios y sus tarjetas informativas persistidas. | **RF08 / RF10** |
| **`GET`** | **`/v1/evaluaciones/{id_evaluacion}/escenarios/{id_escenario}`** | `obtenerEscenario` | Consulta la tarjeta individual del escenario (ej. `B`), incluyendo sus insights de Gemini. | **RF09 / RF17** |
| **`POST`** | **`/v1/evaluaciones/simular`** | `simularEvaluacionDirecta` | Simulación directa interactiva sin persistencia, ejecutando Gemini en vivo. | **Simulador / Piloto** |

---

## 4. Detalle y Ejemplos de Petición/Respuesta

### 4.1 `GET /v1/evaluaciones/{id_evaluacion}/textos` (RF16)
Este endpoint fue diseñado específicamente para clientes o interfaces que solo requieren los textos generados por IA y las descripciones explicativas.

#### Petición cURL
```bash
curl -X GET "http://localhost:8000/v1/evaluaciones/eval-frailesca-demo-001/textos" \
  -H "X-Api-Key: naskob_demo_key_2026"
```

#### Respuesta HTTP 200 OK
```json
{
  "id_evaluacion": "eval-frailesca-demo-001",
  "version_ia": "gemini-2.5-flash-lite",
  "aviso_apoyo": "Esta herramienta apoya tu decisión; no sustituye el criterio técnico en campo.",
  "textos_por_escenario": {
    "B": {
      "cultivo": "frijol",
      "tarjeta_5_partes": {
        "por_que_se_sugirio": "El frijol diversifica la rotación tras maíz y aporta fijación biológica de nitrógeno...",
        "evidencia_agroclimatica": "En 25 años históricos analizados con GPM IMERG y NASA POWER...",
        "beneficios_posibles": "Mejora la fertilidad residual del suelo y reduce la dependencia de fertilizantes sintéticos.",
        "carencias_informacion": "Sin análisis de hongos ni bacterias del suelo en la parcela.",
        "riesgos_revision_local": "Monitorear plagas de raíz si hubo exceso de humedad en el ciclo previo."
      },
      "insights_ia": [
        {
          "id_tarjeta": "card_gemini_agronomico",
          "titulo": "Insight IA: Oportunidades Agronómicas y Nutrición",
          "tipo": "gemini_insight_agronomico",
          "contenido": "Sembrar frijol en el Ciclo 4 tras maíz permite fijar nitrógeno biológico en el suelo, rompiendo el ciclo reproductivo de plagas como la gallina ciega y mejorando la estructura en tierra arcillosa.",
          "origen": "gemini_flash_lite"
        },
        {
          "id_tarjeta": "card_gemini_resiliencia",
          "titulo": "Insight IA: Manejo de Riesgo y Resiliencia Climática",
          "tipo": "gemini_insight_resiliencia",
          "contenido": "Frente a posibles rachas secas o canícula en la Frailesca, la cobertura foliar del frijol protege la tierra arcillosa de la evaporación directa, favoreciendo la retención de agua en el perfil radicular.",
          "origen": "gemini_flash_lite"
        }
      ]
    }
  }
}
```

---

### 4.2 `POST /v1/parcelas/{id_parcela}/evaluaciones` (RF08, RF10)
Orquestador principal. Almacena la evaluación en base de datos cifrada y retorna la evaluación con los insights incrustados en `tarjetas_informativas`.

#### Petición cURL
```bash
curl -X POST "http://localhost:8000/v1/parcelas/3fa85f64-5717-4562-b3fc-2c963f66afa6/evaluaciones" \
  -H "X-Api-Key: naskob_demo_key_2026" \
  -H "Authorization: Bearer <TOKEN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "version_declaracion": 1,
    "modo_evaluacion": "recomendacion_ciclo_4"
  }'
```

#### Fragmento de Respuesta con Insights de Gemini
```json
{
  "id_evaluacion": "c8a493b2-7634-4b5c-a5bc-b70d4fc9fa01",
  "generado_utc": "2026-11-15T00:15:00Z",
  "vigencia_hasta": "2026-02-13T00:15:00Z",
  "pesos_usados": {
    "agua": 0.40,
    "riesgo": 0.20,
    "suelo": 0.20,
    "aptitud": 0.20
  },
  "escenarios": [
    {
      "codigo_escenario": "B",
      "nombre": "Frijol (Rotación de Leguminosa)",
      "cultivo": "frijol",
      "puntaje_mediana": 0.7420,
      "puntaje_p10": 0.6810,
      "puntaje_p90": 0.8030,
      "robustez": "alta",
      "etiqueta_robustez": "Resistente a variación climática",
      "tarjeta_5_partes": { ... },
      "tarjetas_informativas": [
        {
          "id_tarjeta": "card_resumen_frijol",
          "titulo": "Resumen Agroclimático: Frijol",
          "tipo": "resumen_cultivo",
          "origen": "motor_determinista"
        },
        {
          "id_tarjeta": "card_gemini_agronomico",
          "titulo": "Insight IA: Oportunidades Agronómicas y Nutrición",
          "subtitulo": "Generado con Gemini Flash-Lite",
          "tipo": "gemini_insight_agronomico",
          "contenido": "Sembrar frijol en el Ciclo 4 aporta fijación biológica de nitrógeno tras los ciclos previos...",
          "origen": "gemini_flash_lite",
          "destacado": true
        },
        {
          "id_tarjeta": "card_gemini_resiliencia",
          "titulo": "Insight IA: Manejo de Riesgo y Resiliencia Climática",
          "subtitulo": "Generado con Gemini Flash-Lite",
          "tipo": "gemini_insight_resiliencia",
          "contenido": "Frente a eventos de canícula, la tolerancia moderada a calor del frijol en tierra arcillosa...",
          "origen": "gemini_flash_lite",
          "destacado": true
        }
      ]
    }
  ]
}
```

---

### 4.3 `GET /v1/evaluaciones/{id_evaluacion}/escenarios/{id_escenario}` (RF09, RF17)
Permite a la aplicación móvil o PWA consultar la tarjeta en detalle de un único escenario.

#### Petición cURL
```bash
curl -X GET "http://localhost:8000/v1/evaluaciones/eval-frailesca-demo-001/escenarios/B" \
  -H "X-Api-Key: naskob_demo_key_2026"
```

---

### 4.4 `POST /v1/evaluaciones/simular`
Permite a extensionistas o investigadores ejecutar simulaciones "qué pasaría si" de inmediato con datos climáticos reales de la NASA y la IA de Gemini.

#### Petición cURL
```bash
curl -X POST "http://localhost:8000/v1/evaluaciones/simular" \
  -H "X-Api-Key: naskob_demo_key_2026" \
  -H "Content-Type: application/json" \
  -d '{
    "declaracion_directa": {
      "rotacion_existente": [
        {"ciclo": 1, "cultivo": "maiz"},
        {"ciclo": 2, "cultivo": "frijol"},
        {"ciclo": 3, "cultivo": "calabaza"}
      ],
      "tipo_tierra": "arcillosa",
      "agrego_productos": true,
      "riego_veces_semana": 0,
      "considerar_riesgo": true,
      "prioridad_principal": "agua"
    }
  }'
```

---

## 5. Reglas de Negocio y Sanitización de Textos IA

Para cumplir con las normas de evaluación y privacidad del proyecto (RN-IA-04, RN-IA-06, RN-IA-09 y RN-TAR-07):

1. **No-Predicción y Prohibición de Prescripción (R4 y RN-IA-06):**
   La IA tiene terminantemente prohibido garantizar cosechas o predecir rendimientos en kilogramos/hectárea.
2. **Sanitizador Automático de Textos (`_sanitizar_texto_ia`):**
   Toda respuesta generada por Gemini pasa por un filtro de expresiones regulares antes de salir al cliente:
   - `"garantiza"` / `"garantizará"` $\rightarrow$ `"podría favorecer"`
   - `"producirá"` / `"producir"` $\rightarrow$ `"podría generar"`
   - `"asegura"` / `"asegurar cosecha"` $\rightarrow$ `"apoyar el ciclo"`
   - `"debes sembrar"` / `"siembra esto"` $\rightarrow$ `"se sugiere evaluar"`
   - `"rendirá"` / `"obtendrás"` $\rightarrow$ `"se proyecta"` / `"se estima históricamente"`
3. **Aviso Legal de Apoyo a la Decisión (RNF09 / RF17):**
   Toda tarjeta y endpoint de IA acompaña el texto con la leyenda:
   > *"Esta herramienta apoya tu decisión; no sustituye el criterio técnico en campo."*
