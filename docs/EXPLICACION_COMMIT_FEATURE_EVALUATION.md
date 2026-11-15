# Documentación Técnica: Cambios y Correcciones en la Rama `feature/evaluation`

Este documento detalla exhaustivamente las correcciones arquitectónicas, de reglas de negocio, privacidad y estabilidad matemática implementadas en la rama **`feature/evaluation`** sobre el motor de evaluación multicriterio (Contrato 3.4) de **NasKob API**.

---

## 1. Contexto y Objetivos

Durante la revisión del flujo de evaluación multicriterio y generación de recomendaciones agroclimáticas, se identificaron cuatro áreas críticas que requerían alineación inmediata con los requerimientos no funcionales y las reglas de negocio del proyecto:

1. **Inconsistencia en el Ciclo Base del Escenario A (Línea Base):** Riesgo de tomar el último ciclo o asumir maíz por defecto en lugar del cultivo inicial declarado (Ciclo 1).
2. **Deficiencias en la reconstrucción de la Declaración:** Falta de propagación de los campos `considerar_riesgo` y `prioridad_principal` cuando se evalúa una parcela a partir de su registro persistido en la base de datos.
3. **Violación de Privacidad de Geometrías (`RNF01` / `RN-PRI-01`):** Presencia de coordenadas en texto plano en la capa de persistencia de parcelas.
4. **Uso de Términos y Columnas Prohibidas (`R4`, `RN-TAR-07`, `RN-IA-06`):** Columnas en base de datos nombradas con unidades de predicción agronómica (`kg_ha`) o probabilidad porcentual (`probabilidad_exito_pct`), lo cual contradice el principio ético no prescriptivo ni determinista de NasKob.
5. **Resiliencia y Sanitización de IA en `GeminiService` (`RN-IA-04`, `RN-IA-09`):** Necesidad de un timeout corto (3.0s), blindaje total con fallback determinista y filtro regex para eliminar vocabulario prescriptivo/predictivo.

---

## 2. Detalle de los Cambios por Módulo

### 2.1. Corrección de Índices y Lógica del Escenario A
**Archivo modificado:** `app/services/evaluacion_service.py`

* **Problema anterior:**
  Al procesar `declaracion.rotacion_existente`, el código tomaba `historial_cultivos[0]` directamente de la lista recibida sin garantizar el orden cronológico. Si el cliente enviaba los ciclos desordenados (ej. Ciclo 3, Ciclo 1, Ciclo 2), se asignaba un cultivo erróneo al Escenario A.
* **Solución aplicada:**
  1. Se ordenó la lista de entrada explícitamente mediante `key=lambda x: x.ciclo`.
  2. Se localiza de manera determinista el objeto con `ciclo == 1` (`item_c1`).
  3. El cultivo base para el Escenario A (`cultivo_c1`) se extrae directamente de dicho Ciclo 1.
  4. Para el cálculo del Criterio de Suelo ($c_{\text{suelo}}$), la secuencia de 4 ciclos queda estructurada como:
     $$\text{rotacion\_4} = [\text{ciclo\_1}, \, \text{ciclo\_2}, \, \text{ciclo\_3}, \, \text{candidato\_ciclo\_4}]$$
     donde para el Escenario A el candidato del Ciclo 4 es precisamente `cultivo_c1`, reiniciando fielmente la rotación del productor.

```python
# Ordenamiento secuencial estricto por número de ciclo
rotacion_ordenada = sorted(
    declaracion.rotacion_existente,
    key=lambda x: getattr(x, "ciclo", None) or (x.get("ciclo", 1) if isinstance(x, dict) else 1)
)

# Búsqueda explícita del Ciclo 1 como inicio de rotación
item_c1 = next(
    (it for it in rotacion_ordenada if (getattr(it, "ciclo", None) or (it.get("ciclo") if isinstance(it, dict) else None)) == 1),
    rotacion_ordenada[0] if rotacion_ordenada else None
)
```

---

### 2.2. Reconstrucción Completa de `DeclaracionCreateDTO` en `evaluar_para_parcela`
**Archivo modificado:** `app/services/evaluacion_service.py`

* **Problema anterior:**
  Cuando un usuario llamaba a `POST /v1/parcelas/{id}/evaluaciones` sin incluir `declaracion_directa`, el servicio cargaba la declaración de la base de datos (`decl_db`) o generaba la rotación estándar por omisión. En ambos casos, no se pasaban los parámetros `considerar_riesgo` ni `prioridad_principal`, provocando un `AttributeError` al intentar resolver las ponderaciones con `resolver_pesos_oficiales`.
* **Solución aplicada:**
  Al instanciar `DeclaracionCreateDTO`, se mapean explícitamente:
  * `considerar_riesgo=getattr(decl_db, "considerar_riesgo", True)`
  * `prioridad_principal=decl_db.prioridad_principal.value`
  * Mapeo de columnas actualizadas: `cultivo_ciclo_1`, `cultivo_ciclo_2` y `cultivo_ciclo_3`.

---

### 2.3. Cumplimiento de Privacidad Estricta de Geometrías (`RNF01` / `RN-PRI-01`)
**Archivos modificados:** `app/models/parcela_model.py`, `app/services/evaluacion_service.py`

* **Problema anterior:**
  El modelo `ParcelaORM` exponía atributos en texto plano `latitud: float = 16.2333` y `longitud: float = -93.2667`, y la creación de parcelas demo no cifraba la geometría.
* **Solución aplicada:**
  1. Se eliminaron de `ParcelaORM` los atributos de coordenadas en texto plano.
  2. Al crear parcelas demo o de respaldo, se cifra el GeoJSON en memoria mediante `cifrar_geometria(geom_dict)` y se persiste únicamente el binario cifrado (`geometria_cifrada: LargeBinary`).
  3. Durante la evaluación, si se requiere el centroide para cargar las series de la NASA, se descifra la geometría en memoria de forma efímera (`descifrar_geometria`), se calcula el par `(lat, lon)` y se destruye inmediatamente la referencia en memoria con `del geom_dict`.

---

### 2.4. Depuración de Nombres de Columnas Prohibidos (`R4`, `RN-TAR-07`, `RN-IA-06`)
**Archivos modificados:** `app/models/escenario_model.py`, `app/services/evaluacion_service.py`

* **Problema anterior:**
  La tabla `escenarios` contenía columnas que violaban los principios de no predicción de rendimiento y no prescripción:
  * `rendimiento_esperado_kg_ha`
  * `ic_inferior_kg_ha`
  * `ic_superior_kg_ha`
  * `probabilidad_exito_pct`
* **Solución aplicada:**
  Se renombraron y tiparon las columnas en `EscenarioORM` para reflejar puntajes multicriterio normalizados y métricas cualitativas de robustez:

| Nombre Anterior (Prohibido) | Nombre Nuevo (Normalizado) | Tipo | Significado |
| :--- | :--- | :--- | :--- |
| `rendimiento_esperado_kg_ha` | `puntaje_mediana` | `Float` | Mediana del puntaje multicriterio $S(s) \in [0.0, 1.0]$. |
| `ic_inferior_kg_ha` | `puntaje_p10` | `Float` | Percentil 10 de la simulación Monte Carlo. |
| `ic_superior_kg_ha` | `puntaje_p90` | `Float` | Percentil 90 de la simulación Monte Carlo. |
| `probabilidad_exito_pct` | `robustez` | `String(50)` | Calificación cualitativa (*"Estable"*, *"Consistente"*). |

Tanto la lectura en `obtener_evaluacion_por_id` como la persistencia en `_ejecutar_evaluacion_interna` fueron actualizadas acordemente.

---

### 2.5. Bloqueo, Timeout y Filtro Anti-Prescripción en `GeminiService`
**Archivo modificado:** `app/services/gemini_service.py`

* **Reducción de Timeout a 3.0 Segundos (`RNF08`):**
  Tanto `_invocar_gemini` como `_invocar_gemini_async` pasaron de un timeout de 6.0s a 3.0s (`httpx.Client(timeout=3.0)` / `httpx.AsyncClient(timeout=3.0)`).
* **Bloqueo Total con Fallback Determinista (`RN-IA-09`):**
  Se envolvieron las llamadas de generación en bloques `try / except Exception`. Si la API de Gemini falla por saturación de cuota (HTTP 429), latencia de red o timeout, el servicio devuelve inmediatamente las plantillas agronómicas deterministas de respaldo, asegurando que la API de NasKob jamás responda con error 500 ni se bloquee.
* **Filtro de Vocabulario Prohibido (`RN-TAR-07` / `RN-IA-04`):**
  Se incorporó el método `_sanitizar_texto_ia(texto: str)` que sustituye cualquier término prescriptivo o de certeza predictiva por redacción condicional agronómica:
  * `"garantiza"` / `"garantizará"` $\rightarrow$ `"podría favorecer"`
  * `"producirá"` $\rightarrow$ `"podría generar"`
  * `"asegura"` / `"asegurará"` $\rightarrow$ `"favorece"`
  * `"rendirá"` $\rightarrow$ `"se proyecta"`
  * `"debes sembrar"` $\rightarrow$ `"se sugiere evaluar"`

---

## 3. Pruebas Automatizadas Agregadas

**Archivo modificado:** `tests/test_evaluacion_contrato_3_4.py`

Se añadieron cuatro pruebas unitarias y de integración específicas para blindar estas correcciones:

1. **`test_evaluacion_sin_declaracion_directa`:**
   Verifica que `POST /v1/parcelas/{id}/evaluaciones` funcione con éxito (201 Created) sin enviar `declaracion_directa`, comprobando la correcta reconstrucción de `considerar_riesgo` y `prioridad_principal`.
2. **`test_ciclo_base_escenario_a_rotacion`:**
   Envía una rotación con los ciclos desordenados (`ciclo: 3`, `ciclo: 1`, `ciclo: 2`) y valida que el Escenario A seleccione estrictamente el cultivo del Ciclo 1 como continuidad (`secuencia_cultivos == [c1, c2, c3, c1]`).
3. **`test_escenario_orm_sin_columnas_prohibidas`:**
   Inspecciona introspectivamente las columnas de `EscenarioORM.__table__.columns` verificando la total ausencia de `rendimiento_esperado_kg_ha`, `probabilidad_exito_pct`, etc., y la presencia de `puntaje_mediana`, `puntaje_p10`, `puntaje_p90` y `robustez`.
4. **`test_gemini_service_sanitizacion_y_fallback`:**
   Verifica que el sanitizador reemplace los términos prohibidos y que ante una clave inválida o corte de red se generen tarjetas de fallback válidas y libres de vocabulario prescriptivo.

---

## 4. Resultados de la Suite de Pruebas

La ejecución de `pytest -v` en la rama `feature/evaluation` arrojó un resultado satisfactorio del 100%:

```text
============================= test session starts ==============================
rootdir: /home/emma/Proyectos/naskov-api
configfile: pytest.ini
collected 14 items

tests/test_api_errores.py::test_errores_rfc_9457 PASSED                  [  7%]
tests/test_auth_sesiones.py::test_flujo_completo_auth_y_sesiones PASSED  [ 14%]
tests/test_domain_calculos.py::test_cultivos_catalogo_m1 PASSED          [ 21%]
tests/test_domain_calculos.py::test_matriz_ponderaciones_suman_uno PASSED [ 28%]
tests/test_domain_calculos.py::test_calculo_criterios_individuales PASSED [ 35%]
tests/test_domain_calculos.py::test_rotacion_diversidad_suelo PASSED     [ 42%]
tests/test_domain_calculos.py::test_simulacion_monte_carlo PASSED        [ 50%]
tests/test_domain_calculos.py::test_ensamblar_tarjeta_5_partes PASSED    [ 57%]
tests/test_evaluacion_contrato_3_4.py::test_flujo_completo_contrato_3_4 PASSED [ 64%]
tests/test_evaluacion_contrato_3_4.py::test_evaluacion_sin_declaracion_directa PASSED [ 71%]
tests/test_evaluacion_contrato_3_4.py::test_ciclo_base_escenario_a_rotacion PASSED [ 78%]
tests/test_evaluacion_contrato_3_4.py::test_escenario_orm_sin_columnas_prohibidas PASSED [ 85%]
tests/test_evaluacion_contrato_3_4.py::test_gemini_service_sanitizacion_y_fallback PASSED [ 92%]
tests/test_parcela_crud.py::test_flujo_crud_parcela_y_declaracion PASSED [100%]

============================= 14 passed in 15.98s ==============================
```
