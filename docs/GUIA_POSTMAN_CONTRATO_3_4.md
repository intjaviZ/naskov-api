# NasKob · Guía de Pruebas en Postman (Contrato 3.4: Evaluación Multicriterio)

Este documento detalla la arquitectura por capas implementada en FastAPI, el funcionamiento del motor de decisión para el **Ciclo 4** (basado en la Matriz Chiapas M1 y datos satelitales NASA 2001–2025), la generación de tarjetas con **Gemini Flash Lite**, y los pasos exactos para probar los endpoints en **Postman** o mediante **cURL**.

---

## 1. Arquitectura por Capas (Layered Architecture)

La API fue reprogramada bajo una arquitectura limpia y desacoplada organizada en cuatro capas:

```
api/
├── presentation/          # Capa de Presentación (Controladores REST y DTOs Pydantic v2)
│   ├── rutas_evaluacion.py# Endpoints del Contrato 3.4
│   └── esquemas_dto.py    # DTOs de petición y respuesta validados
├── application/           # Capa de Aplicación (Casos de uso y Orquestación)
│   ├── evaluacion_service.py # Orquestador de la evaluación, Monte Carlo y tarjetas
│   └── gemini_service.py  # Integración con Google Gemini Flash Lite (2 Insights IA)
├── domain/                # Capa de Dominio (Lógica y Reglas de Negocio Puras)
│   ├── modelos_cultivo.py # Catálogo de los 6 cultivos M1 (FAO-56, Kc 5 nodos, umbrales)
│   ├── ponderaciones.py   # Matriz oficial de pesos y cálculo de puntaje global S(s)
│   ├── motor_calculo.py   # Los 4 criterios agroclimáticos (c_agua, c_riesgo, c_suelo, c_apt)
│   ├── monte_carlo.py     # Simulación de robustez con 1,000 réplicas (±20% en pesos)
│   └── tarjetas.py        # Generación de tarjeta de 5 partes y tarjetas informativas
└── infrastructure/        # Capa de Infraestructura (Persistencia y Datos Externos)
    ├── repositorio_evaluacion.py # Acceso a datos y persistencia SQLAlchemy
    ├── series_nasa.py     # Carga de series satelitales IMERG y POWER
    ├── modelos_orm.py     # Entidades de base de datos
    └── db.py              # Sesión de base de datos (PostgreSQL / SQLite fallback)
```

---

## 2. Lógica del Motor de Decisión (Ciclo 4)

### 2.1 Los 6 Cultivos Prioritarios (Matriz M1)
1. **Maíz (`maiz`):** Gramínea base de temporal, ciclo de 125 d, extrae nitrógeno ($q_N = 0$), umbral de calor 35.0 °C.
2. **Frijol (`frijol`):** Leguminosa de temporal, ciclo de 110 d, fija nitrógeno biológico ($q_N = 1$), umbral de calor 31.0 °C.
3. **Cacahuate (`cacahuate`):** Fabácea de temporal, ciclo de 130 d, excelente drenaje, balance de N neutro/excluido, umbral de calor 35.0 °C.
4. **Calabaza (`calabaza`):** Cucurbitácea de cobertura extensa, ciclo de 100 d, alta retención de humedad, umbral de calor 34.5 °C.
5. **Sandía (`sandia`):** Cucurbitácea de ciclo corto (80 d), **requiere riego obligatorio** (filtro RC5), umbral de calor 35.0 °C.
6. **Chile habanero (`habanero`):** Solanácea de ciclo de 120 d, raíz superficial, **requiere riego obligatorio** (filtro RC5), umbral de calor 34.0 °C.

### 2.2 Los 4 Criterios de Evaluación ($c_k \in [0, 1]$)
- **Balance de Humedad ($c_{agua}$):** Demanda $ET_c(d) = Kc(d) \times ET_0(d)$ interpolada en curva de 5 nodos vs lluvia efectiva ($f_e = 0.75$), con peso doble en la ventana crítica ($w_c = 2$). Si el cultivo cuenta con riego disponible, su demanda se cubre al 100% ($c_{agua} = 1.0$).
- **Resiliencia a Extremos ($c_{riesgo}$):** Penaliza si en los 25 años históricos hubo rachas secas críticas ($\ge 7$ d en floración), racha acumulada $\ge D_{tol} \times \text{factor}$, olas de calor ($\ge 3$ d consecutivos con $T_{max} \ge$ umbral) o heladas ($T_{min} \le 2$ °C).
- **Suelo y Rotación ($c_{suelo}$):** Evalúa la rotación de 4 ciclos combinando el balance de nitrógeno ($q_N$: frijol aporta 1, maíz/sandía extraen 0) y diversidad botánica ($q_{div}$ entre 4 familias), ponderado según el riesgo de erosión (RRE).
- **Aptitud Agroclimática y Zona ($c_{apt}$):** Ajuste adiabático de temperatura por altitud ($0.0065 \times \Delta z$), trapecio de idoneidad térmica y factor de zona tradicional en Chiapas ($f_{zona} = 1.0$ o $0.5$).

### 2.3 Matriz de Pesos Oficial

$$S(s) = w_{agua} \cdot c_{agua} + w_{riesgo} \cdot c_{riesgo} + w_{suelo} \cdot c_{suelo} + w_{apt} \cdot c_{apt}$$

| ¿Considerar riesgo? | Prioridad declarada | $w_{agua}$ | $w_{riesgo}$ | $w_{suelo}$ | $w_{apt}$ |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **Sí** | **Agua** | **0.40** | 0.20 | 0.20 | 0.20 |
| **Sí** | **Riesgo** | 0.20 | **0.40** | 0.20 | 0.20 |
| **Sí** | **Suelo** | 0.20 | 0.20 | **0.40** | 0.20 |
| **Sí** | **Igual** | 0.25 | 0.25 | 0.25 | 0.25 |
| **No** | **Agua** | **0.50** | 0.00 | 0.25 | 0.25 |
| **No** | **Suelo** | 0.25 | 0.00 | **0.50** | 0.25 |
| **No** | **Igual** | 0.333 | 0.00 | 0.333 | 0.334 |

### 2.4 Regla RC5 (Riego) y Escenario A
- Si `riego_veces_semana == 0` (temporal estricto): Sandía y Habanero se descartan como nuevas recomendaciones.
- **Excepción:** Si el agricultor sembró Sandía o Habanero en el Ciclo 1, el **Escenario A nunca se descarta** (representa su práctica histórica), mostrándose con advertencia visible de que requiere riego.

### 2.5 Generación de Tarjetas con Gemini Flash Lite
La interfaz genera un conjunto estructurado de tarjetas informativas. **Dos de estas tarjetas son generadas en tiempo real por Google Gemini Flash Lite**:
1. **Insight IA: Oportunidades Agronómicas y Nutrición:** Explica la sinergia biológica de la rotación de los 4 ciclos, el balance nutricional de N y el rompimiento de plagas del suelo.
2. **Insight IA: Estrategia Preventiva de Resiliencia Climática:** Consejos prácticos para tolerar la canícula, retener humedad según el tipo de tierra declarado y mitigar el calor.

---

## 3. Catálogo de Endpoints del Contrato 3.4

### 3.1 `POST /v1/evaluaciones/simular`
**Descripción:** Ejecuta la evaluación multicriterio, la simulación Monte Carlo y la generación de insights con Gemini de forma inmediata a partir de los datos de la declaración, sin necesidad de haber registrado previamente una parcela en la base de datos. Ideal para pruebas en Postman.

- **URL:** `http://localhost:8000/v1/evaluaciones/simular`
- **Método:** `POST`
- **Headers:** `Content-Type: application/json`

#### Cuerpo de Petición (Ejemplo: Temporal estricto con prioridad en Suelo):
```json
{
  "rotacion_existente": [
    {"ciclo": 1, "cultivo": "maiz"},
    {"ciclo": 2, "cultivo": "maiz"},
    {"ciclo": 3, "cultivo": "frijol"}
  ],
  "tipo_tierra": "negra",
  "agrego_productos": true,
  "riego_veces_semana": 0,
  "considerar_riesgo": true,
  "prioridad_principal": "suelo",
  "region": "frailesca"
}
```

#### Respuesta (200 OK):
```json
{
  "id_evaluacion": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "id_parcela": null,
  "id_declaracion": null,
  "generado_utc": "2026-11-14T22:15:00Z",
  "vigencia_hasta": "2026-12-14T22:15:00Z",
  "pesos_usados": {
    "c_agua": 0.20,
    "c_riesgo": 0.20,
    "c_suelo": 0.40,
    "c_apt": 0.20
  },
  "escenarios": [
    {
      "codigo_escenario": "A",
      "orden_visual": 1,
      "nombre": "Continuidad: Maíz",
      "cultivo": "maiz",
      "es_linea_base": true,
      "secuencia_cultivos": ["maiz", "maiz", "frijol", "maiz"],
      "confianza": "alta",
      "puntaje_mediana": 0.6230,
      "puntaje_p10": 0.5810,
      "puntaje_p90": 0.6650,
      "robustez": "baja_consistencia",
      "criterios_detalle": {
        "c_agua": 0.9076,
        "c_riesgo": 0.6800,
        "c_suelo": 0.3500,
        "c_apt": 1.0000
      },
      "delta_vs_a": null,
      "tarjeta_5_partes": {
        "por_que_se_sugirio": "Representa tu práctica de manejo declarada...",
        "evidencia_agroclimatica": "Serie NASA IMERG/POWER (2001-2025)...",
        "beneficios_posibles": "Mejora la diversidad de la parcela...",
        "carencias_informacion": "Declaraste que agregas productos; esta versión no evalúa cuantitativamente su efecto químico en el suelo.",
        "riesgos_revision_local": "Monitorear drenaje y humedad residual."
      }
    },
    {
      "codigo_escenario": "D",
      "orden_visual": 2,
      "nombre": "Alternativa: Calabaza",
      "cultivo": "calabaza",
      "es_linea_base": false,
      "secuencia_cultivos": ["maiz", "maiz", "frijol", "calabaza"],
      "confianza": "alta",
      "puntaje_mediana": 0.7485,
      "robustez": "consistente",
      "etiqueta_robustez": "Consistente con tus prioridades",
      "criterios_detalle": {
        "c_agua": 0.9865,
        "c_riesgo": 0.7600,
        "c_suelo": 0.6000,
        "c_apt": 1.0000
      },
      "delta_vs_a": {
        "puntaje": 0.1255,
        "c_agua": 0.0789,
        "c_riesgo": 0.0800,
        "c_suelo": 0.2500,
        "c_apt": 0.0000
      }
    }
  ],
  "escenarios_descartados": [
    {
      "id": "SANDIA",
      "cultivo": "sandia",
      "nombre": "Sandía",
      "motivo": "RC5",
      "texto": "Sandía requiere riego externo garantizado y declaraste 0 riegos por semana."
    },
    {
      "id": "HABANERO",
      "cultivo": "habanero",
      "nombre": "Chile habanero",
      "motivo": "RC5",
      "texto": "Chile habanero requiere riego externo garantizado y declaraste 0 riegos por semana."
    }
  ],
  "tarjetas_destacadas": [
    {
      "id_tarjeta": "card_gemini_agronomico",
      "titulo": "Insight IA: Oportunidades Agronómicas y Nutrición",
      "subtitulo": "Generado con Gemini Flash-Lite",
      "tipo": "gemini_insight_agronomico",
      "contenido": "Sembrar calabaza después del frijol aprovecha los nutrientes que este dejó en la tierra y rompe el ciclo de plagas del maíz. Su amplio follaje funciona como una sombrilla natural que ahoga la maleza y protege la vida biológica del suelo sin necesidad de químicos.",
      "origen": "gemini_flash_lite",
      "icono": "sparkles",
      "destacado": true
    },
    {
      "id_tarjeta": "card_gemini_resiliencia",
      "titulo": "Insight IA: Estrategia Preventiva de Resiliencia Climática",
      "subtitulo": "Generado con Gemini Flash-Lite",
      "tipo": "gemini_insight_resiliencia",
      "contenido": "Aunque tu tierra negra retiene bien la humedad, las rachas de calor y la canícula en La Frailesca pueden resecar la superficie rápidamente. Te sugiero dejar los residuos de las cosechas anteriores sobre el suelo para conservar el agua de las lluvias y evitar que el sol caliente demasiado las raíces.",
      "origen": "gemini_flash_lite",
      "icono": "shield",
      "destacado": true
    }
  ]
}
```

---

### 3.2 `POST /v1/parcelas/{id_parcela}/evaluaciones`
**Descripción:** Endpoint formal del Contrato 3.4. Evalúa la parcela persistida en base de datos tomando su declaración activa, aplica los cálculos agroclimáticos, genera los 2 insights de Gemini y persiste el resultado y las cifras de trazabilidad.

- **URL:** `http://localhost:8000/v1/parcelas/{{id_parcela}}/evaluaciones`
- **Método:** `POST`
- **Headers:**
  - `Content-Type: application/json`
  - `Idempotency-Key: eval-20261114-001` *(Opcional)*
- **Cuerpo (Opcional):**
  ```json
  {
    "pesos": null
  }
  ```
- **Respuesta (201 Created):** Retorna el objeto `EvaluacionResponse` con su `id_evaluacion` asignado.

---

### 3.3 `GET /v1/evaluaciones/{id_evaluacion}`
**Descripción:** Recupera una evaluación persistida previamente por su identificador UUID.

- **URL:** `http://localhost:8000/v1/evaluaciones/{{id_evaluacion}}`
- **Método:** `GET`
- **Respuesta (200 OK):** Detalle de escenarios, puntajes, robustez y tarjetas.

---

### 3.4 `GET /v1/evaluaciones/{id_evaluacion}/cifras/{id_cifra}`
**Descripción:** Proporciona la trazabilidad matemática formal (RF11 / "¿Por qué?") de cualquier cifra que aparezca en pantalla.

- **URL:** `http://localhost:8000/v1/evaluaciones/{{id_evaluacion}}/cifras/cifra_lluvia_mediana`
- **Método:** `GET`
- **Respuesta (200 OK):**
  ```json
  {
    "id_cifra": "cifra_lluvia_mediana",
    "id_evaluacion": "9a299084-9a1d-4339-a568-63f1c8ea8766",
    "indicador": "Precipitación Anual Mediana",
    "valor": 1250.0,
    "unidad": "mm/año",
    "fuente_datos": "NASA GPM IMERG v07B",
    "fecha_fuente": "2026-11-14",
    "resolucion": "10.0 km",
    "f_val": 0.95,
    "parametros_aplicados": {
      "periodo": "2001-2025",
      "metodo": "mediana"
    },
    "version_regla": "RN-LLU-01"
  }
  ```

---

## 4. Colección de Postman para Importar Directamente

Copia el siguiente bloque JSON y pégalo en Postman: **Import** $\to$ **Raw text**:

```json
{
  "info": {
    "name": "NasKob - Contrato 3.4 Evaluaciones",
    "description": "Pruebas del motor de decisión agroclimática y tarjetas con Gemini Flash Lite.",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "baseUrl",
      "value": "http://localhost:8000",
      "type": "string"
    },
    {
      "key": "id_parcela",
      "value": "525e1285-7678-4b6b-92bc-12276c5b3c76",
      "type": "string"
    },
    {
      "key": "id_evaluacion",
      "value": "",
      "type": "string"
    }
  ],
  "item": [
    {
      "name": "1. Simular Evaluación (Temporal - Prioridad Suelo)",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"rotacion_existente\": [\n    {\"ciclo\": 1, \"cultivo\": \"maiz\"},\n    {\"ciclo\": 2, \"cultivo\": \"maiz\"},\n    {\"ciclo\": 3, \"cultivo\": \"frijol\"}\n  ],\n  \"tipo_tierra\": \"negra\",\n  \"agrego_productos\": true,\n  \"riego_veces_semana\": 0,\n  \"considerar_riesgo\": true,\n  \"prioridad_principal\": \"suelo\",\n  \"region\": \"frailesca\"\n}"
        },
        "url": {
          "raw": "{{baseUrl}}/v1/evaluaciones/simular",
          "host": ["{{baseUrl}}"],
          "path": ["v1", "evaluaciones", "simular"]
        }
      }
    },
    {
      "name": "2. Simular Evaluación (Con Riego - Diversificación)",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"rotacion_existente\": [\n    {\"ciclo\": 1, \"cultivo\": \"maiz\"},\n    {\"ciclo\": 2, \"cultivo\": \"frijol\"},\n    {\"ciclo\": 3, \"cultivo\": \"maiz\"}\n  ],\n  \"tipo_tierra\": \"arenosa\",\n  \"agrego_productos\": false,\n  \"riego_veces_semana\": 3,\n  \"considerar_riesgo\": true,\n  \"prioridad_principal\": \"agua\",\n  \"region\": \"villaflores\"\n}"
        },
        "url": {
          "raw": "{{baseUrl}}/v1/evaluaciones/simular",
          "host": ["{{baseUrl}}"],
          "path": ["v1", "evaluaciones", "simular"]
        }
      }
    },
    {
      "name": "3. Ejecutar Evaluación de Parcela (Contrato 3.4 Oficial)",
      "event": [
        {
          "listen": "test",
          "script": {
            "exec": [
              "var jsonData = pm.response.json();",
              "if (jsonData.id_evaluacion) {",
              "    pm.collectionVariables.set('id_evaluacion', jsonData.id_evaluacion);",
              "}"
            ],
            "type": "text/javascript"
          }
        }
      ],
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          },
          {
            "key": "Idempotency-Key",
            "value": "postman-test-01"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{}"
        },
        "url": {
          "raw": "{{baseUrl}}/v1/parcelas/{{id_parcela}}/evaluaciones",
          "host": ["{{baseUrl}}"],
          "path": ["v1", "parcelas", "{{id_parcela}}", "evaluaciones"]
        }
      }
    },
    {
      "name": "4. Obtener Evaluación por ID",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{baseUrl}}/v1/evaluaciones/{{id_evaluacion}}",
          "host": ["{{baseUrl}}"],
          "path": ["v1", "evaluaciones", "{{id_evaluacion}}"]
        }
      }
    },
    {
      "name": "5. Consultar Cifra de Trazabilidad (RF11)",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{baseUrl}}/v1/evaluaciones/{{id_evaluacion}}/cifras/cifra_lluvia_mediana",
          "host": ["{{baseUrl}}"],
          "path": ["v1", "evaluaciones", "{{id_evaluacion}}", "cifras", "cifra_lluvia_mediana"]
        }
      }
    }
  ]
}
```

---

## 5. Ejemplos Rápidos con cURL

### Probar Simulación Directa (Temporal estricto, 0 riegos):
```bash
curl -X POST "http://localhost:8000/v1/evaluaciones/simular" \
  -H "Content-Type: application/json" \
  -d '{
    "rotacion_existente": [
      {"ciclo": 1, "cultivo": "maiz"},
      {"ciclo": 2, "cultivo": "maiz"},
      {"ciclo": 3, "cultivo": "frijol"}
    ],
    "tipo_tierra": "negra",
    "agrego_productos": true,
    "riego_veces_semana": 0,
    "considerar_riesgo": true,
    "prioridad_principal": "suelo",
    "region": "frailesca"
  }'
```

### Probar Simulación con Riego (3 riegos semanales):
```bash
curl -X POST "http://localhost:8000/v1/evaluaciones/simular" \
  -H "Content-Type: application/json" \
  -d '{
    "rotacion_existente": [
      {"ciclo": 1, "cultivo": "maiz"},
      {"ciclo": 2, "cultivo": "frijol"},
      {"ciclo": 3, "cultivo": "maiz"}
    ],
    "tipo_tierra": "arenosa",
    "agrego_productos": false,
    "riego_veces_semana": 3,
    "considerar_riesgo": true,
    "prioridad_principal": "agua",
    "region": "villaflores"
  }'
```

---

## 6. Aclaración sobre Archivos y Datasets

**No es necesario descargar ni suministrar ningún dataset adicional.**  
Todo lo requerido para operar el motor de evaluación está completamente integrado en el proyecto:
- Los parámetros agronómicos de los 6 cultivos prioritarios (FAO-56, curvas Kc por tramos, rangos térmicos, umbrales de calor y respuestas edáficas) provienen directamente de la **Matriz Agronómica de Chiapas (M1)** y están programados en [`api/domain/modelos_cultivo.py`](file:///home/emma/Proyectos/NasKob/api/domain/modelos_cultivo.py).
- Las series satelitales climáticas históricas ($2001\text{--}2025$) de precipitación y evapotranspiración de la NASA (GPM IMERG y NASA POWER) residen en `datos/series/` y son cargadas por el adaptador [`api/infrastructure/series_nasa.py`](file:///home/emma/Proyectos/NasKob/api/infrastructure/series_nasa.py) con soporte satelital global dinámico.
- La clave de API de **Google Gemini** para el modelo Flash Lite (`gemini-flash-lite-latest`) se encuentra configurada en [`api/core/config.py`](file:///home/emma/Proyectos/NasKob/api/core/config.py).
