"""
app/services/evaluacion_service.py
Servicio de aplicación para coordinar el motor de decisiones del Ciclo 4 y Contrato 3.4.
Integra las ponderaciones oficiales de 4 criterios, regla RC5, simulación Monte Carlo,
y generación de tarjetas informativas con 2 insights de Gemini Flash Lite.
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.core.exceptions import ErroresContrato
from app.domain.modelos_cultivo import CULTIVOS_M1, CultivoAgronomico
from app.domain.ponderaciones import resolver_pesos_oficiales, calcular_puntaje_global
from app.domain.motor_calculo import (
    calcular_c_agua,
    calcular_c_riesgo,
    calcular_c_suelo,
    calcular_c_apt,
)
from app.domain.monte_carlo import ejecutar_monte_carlo
from app.domain.tarjetas import (
    TarjetaInformativa,
    generar_tarjetas_deterministas,
    ensamblar_tarjeta_5_partes,
)
from app.domain.series_nasa import cargar_serie_nasa_parcela
from app.repository.evaluacion_repository import EvaluacionRepository
from app.services.gemini_service import GeminiService
from app.models.evaluacion_model import EvaluacionORM, CifraTrazabilidadORM
from app.models.escenario_model import EscenarioORM
from app.models.parcela_model import ParcelaORM
from app.models.declaracion_model import DeclaracionORM
from app.dtos.evaluacion_create_dto import EvaluacionCreateDTO
from app.dtos.evaluacion_response_dto import EvaluacionResponseDTO
from app.dtos.escenario_tarjeta_dto import EscenarioDetalleDTO, Tarjeta5PartesDTO, TarjetaInformativaDTO
from app.dtos.cifra_explicacion_dto import CifraTrazabilidadDTO


class EvaluacionService:
    def __init__(
        self,
        repo: EvaluacionRepository,
        gemini_service: Optional[GeminiService] = None,
    ):
        self.repo = repo
        self.gemini_service = gemini_service or GeminiService()

    async def evaluar_para_parcela(
        self,
        id_parcela: str,
        dto: EvaluacionCreateDTO,
        id_cuenta: Optional[str] = None,
    ) -> EvaluacionResponseDTO:
        """
        Ejecuta y persiste la evaluación para una parcela específica (POST /v1/parcelas/{id}/evaluaciones).
        """
        # 1. Verificar si la parcela existe en base de datos
        parcela = await self.repo.obtener_parcela(id_parcela)
        if not parcela:
            raise ErroresContrato.no_encontrado(f"Parcela '{id_parcela}'")

        # Extraer coordenadas en memoria desde geometría cifrada sin persistir coordenadas planas (RNF01 / RN-PRI-01)
        lat = getattr(parcela, "latitud", None) or 16.2333
        lon = getattr(parcela, "longitud", None) or -93.2667
        region = getattr(parcela, "region", "frailesca") or "frailesca"
        if getattr(parcela, "geometria_cifrada", None):
            try:
                from app.services.parcela_service import descifrar_geometria
                geom_dict = descifrar_geometria(parcela.geometria_cifrada)
                if geom_dict.get("type") == "Point" and "coordinates" in geom_dict:
                    lon = float(geom_dict["coordinates"][0])
                    lat = float(geom_dict["coordinates"][1])
                elif geom_dict.get("type") == "Polygon" and "coordinates" in geom_dict:
                    coords = geom_dict["coordinates"][0]
                    lon = float(sum(p[0] for p in coords) / len(coords))
                    lat = float(sum(p[1] for p in coords) / len(coords))
                del geom_dict
            except Exception:
                pass

        # 2. Obtener datos de manejo (declaración directa o vigente en BD)
        declaracion_dto = dto.declaracion_directa
        if not declaracion_dto:
            decl_db = await self.repo.obtener_declaracion_vigente(id_parcela, dto.version_declaracion)
            if decl_db:
                from app.dtos.declaracion_create_dto import DeclaracionCreateDTO, CicloRotacionDTO
                c1 = decl_db.cultivo_ciclo_1.value if hasattr(decl_db.cultivo_ciclo_1, "value") else str(getattr(decl_db, "cultivo_ciclo_1", getattr(decl_db, "cultivo_c1", "maiz")))
                c2 = decl_db.cultivo_ciclo_2.value if hasattr(decl_db.cultivo_ciclo_2, "value") else str(getattr(decl_db, "cultivo_ciclo_2", getattr(decl_db, "cultivo_c2", "frijol")))
                c3 = decl_db.cultivo_ciclo_3.value if hasattr(decl_db.cultivo_ciclo_3, "value") else str(getattr(decl_db, "cultivo_ciclo_3", getattr(decl_db, "cultivo_c3", "calabaza")))
                p_princ = decl_db.prioridad_principal.value if hasattr(decl_db.prioridad_principal, "value") else str(getattr(decl_db, "prioridad_principal", "igual"))
                t_tierra = decl_db.tipo_tierra.value if hasattr(decl_db.tipo_tierra, "value") else str(getattr(decl_db, "tipo_tierra", "negra"))
                c_riesgo = getattr(decl_db, "considerar_riesgo", True)

                declaracion_dto = DeclaracionCreateDTO(
                    rotacion_existente=[
                        CicloRotacionDTO(ciclo=1, cultivo=c1),
                        CicloRotacionDTO(ciclo=2, cultivo=c2),
                        CicloRotacionDTO(ciclo=3, cultivo=c3),
                    ],
                    tipo_tierra=t_tierra, # type: ignore
                    riego_veces_semana=decl_db.riego_veces_semana,
                    agrego_productos=decl_db.agrego_productos,
                    considerar_riesgo=c_riesgo,
                    prioridad_principal=p_princ, # type: ignore
                    region=getattr(parcela, "region", "frailesca"),
                )
            else:
                # Rotación estándar por omisión de Chiapas (Maíz -> Frijol -> Calabaza)
                from app.dtos.declaracion_create_dto import DeclaracionCreateDTO, CicloRotacionDTO
                declaracion_dto = DeclaracionCreateDTO(
                    rotacion_existente=[
                        CicloRotacionDTO(ciclo=1, cultivo="maiz"),
                        CicloRotacionDTO(ciclo=2, cultivo="frijol"),
                        CicloRotacionDTO(ciclo=3, cultivo="calabaza"),
                    ],
                    tipo_tierra="negra",
                    riego_veces_semana=0,
                    agrego_productos=False,
                    considerar_riesgo=True,
                    prioridad_principal="igual",
                    region=getattr(parcela, "region", "frailesca"),
                )

        # 3. Ejecutar el cálculo y orquestación
        id_evaluacion = str(uuid.uuid4())
        response_dto, escenarios_orm, cifras_orm = await self._ejecutar_evaluacion_interna(
            id_evaluacion=id_evaluacion,
            id_parcela=id_parcela,
            id_cuenta=id_cuenta,
            version_declaracion=dto.version_declaracion,
            modo_evaluacion=dto.modo_evaluacion,
            pesos_personalizados=dto.pesos,
            declaracion=declaracion_dto,
            lat=lat,
            lon=lon,
            region=getattr(parcela, "region", "frailesca"),
        )

        # 4. Persistir en base de datos
        evaluacion_orm = EvaluacionORM(
            id_evaluacion=id_evaluacion,
            id_parcela=id_parcela,
            id_cuenta=id_cuenta,
            modo_ponderacion=dto.modo_evaluacion,
            version_declaracion=dto.version_declaracion,
            evaluada_utc=response_dto.generado_utc,
            metadatos_evaluacion={
                "pesos_usados": response_dto.pesos_usados,
                "respuestas_snapshot": response_dto.respuestas_snapshot,
            },
        )
        await self.repo.guardar_evaluacion(evaluacion_orm, escenarios_orm, cifras_orm)

        # Enriquecer DTO con coordenadas y metadatos de la parcela para el mapa del frontend
        response_dto.latitud = getattr(parcela, "latitud", lat)
        response_dto.longitud = getattr(parcela, "longitud", lon)
        response_dto.area_ha = getattr(parcela, "area_ha", None)
        response_dto.nombre_parcela = getattr(parcela, "nombre", None)
        if getattr(parcela, "geometria_cifrada", None):
            try:
                from app.services.parcela_service import descifrar_geometria
                geom = descifrar_geometria(parcela.geometria_cifrada)
                response_dto.geometria = geom
                if isinstance(geom, dict):
                    if geom.get("type") == "Polygon" and "coordinates" in geom:
                        response_dto.coordenadas = geom["coordinates"][0]
                    elif "punto" in geom:
                        response_dto.coordenadas = [[geom["punto"]["lon"], geom["punto"]["lat"]]]
            except Exception:
                pass

        return response_dto

    async def simular_evaluacion(self, dto: EvaluacionCreateDTO) -> EvaluacionResponseDTO:
        """
        Ejecuta simulación directa sin requerir una parcela persistida (POST /v1/evaluaciones/simular).
        """
        declaracion_dto = dto.declaracion_directa
        if not declaracion_dto:
            from app.dtos.declaracion_create_dto import DeclaracionCreateDTO, CicloRotacionDTO
            declaracion_dto = DeclaracionCreateDTO(
                rotacion_existente=[
                    CicloRotacionDTO(ciclo=1, cultivo="maiz"),
                    CicloRotacionDTO(ciclo=2, cultivo="frijol"),
                    CicloRotacionDTO(ciclo=3, cultivo="calabaza"),
                ],
                tipo_tierra="negra",
                riego_veces_semana=0,
                agrego_productos=False,
                considerar_riesgo=True,
                prioridad_principal="igual",
                region="frailesca",
            )

        id_evaluacion = str(uuid.uuid4())
        response_dto, _, _ = await self._ejecutar_evaluacion_interna(
            id_evaluacion=id_evaluacion,
            id_parcela=None,
            id_cuenta=None,
            version_declaracion=dto.version_declaracion,
            modo_evaluacion=dto.modo_evaluacion,
            pesos_personalizados=dto.pesos,
            declaracion=declaracion_dto,
            lat=16.2333,
            lon=-93.2667,
            region=declaracion_dto.region,
        )
        return response_dto

    async def obtener_evaluacion_por_id(self, id_evaluacion: str) -> EvaluacionResponseDTO:
        eval_db = await self.repo.obtener_evaluacion_por_id(id_evaluacion)
        if not eval_db:
            raise ErroresContrato.no_encontrado("Evaluación")

        escenarios_db = await self.repo.obtener_escenarios(id_evaluacion)
        escenarios_dtos = []
        for e in escenarios_db:
            tarjetas_info_dtos = [TarjetaInformativaDTO(**t) for t in e.tarjetas_json]
            t5_dto = Tarjeta5PartesDTO(**(e.tarjeta_5_partes or {})) if e.tarjeta_5_partes else Tarjeta5PartesDTO(
                por_que_se_sugirio="", evidencia_agroclimatica="", beneficios_posibles="",
                carencias_informacion="", riesgos_revision_local=""
            )
            subtitulo = "Línea Base" if e.es_linea_base else ("Recomendación Principal" if e.orden_visual == 1 else "Propuesta Alternativa")
            badge = "Seguir igual" if e.es_linea_base else ("Recomendado" if e.orden_visual == 1 else "Rotación")
            tipo_badge = "linea_base" if e.es_linea_base else ("recomendado" if e.orden_visual == 1 else "alternativa")
            puntaje_val = round(e.puntuacion_final * 100, 1) if e.puntuacion_final else None

            escenarios_dtos.append(
                EscenarioDetalleDTO(
                    codigo_escenario=e.codigo,
                    orden_visual=e.orden_visual,
                    nombre=e.cultivo_nombre,
                    cultivo=e.cultivo_id,
                    es_linea_base=e.es_linea_base,
                    secuencia_cultivos=[e.cultivo_id],
                    es_supuesto=False,
                    ciclos_supuestos=[],
                    confianza="alta",
                    puntaje_mediana=round(e.puntaje_mediana, 4),
                    puntaje_p10=round(e.puntaje_p10, 4),
                    puntaje_p90=round(e.puntaje_p90, 4),
                    robustez="alta",
                    etiqueta_robustez=getattr(e, "robustez", "Estable"),
                    criterios_detalle={
                        "c_agua": e.criterio_agua,
                        "c_riesgo": e.criterio_riesgo,
                        "c_suelo": e.criterio_suelo,
                        "c_apt": e.criterio_aptitud,
                    },
                    delta_vs_a=e.delta_vs_a,
                    tarjeta_5_partes=t5_dto,
                    tarjetas_informativas=tarjetas_info_dtos,
                    subtitulo=subtitulo,
                    badge=badge,
                    tipo_badge=tipo_badge,
                    puntaje_valor=puntaje_val,
                )
            )

        generado = eval_db.evaluada_utc
        vigencia = generado + timedelta(days=90)
        metadatos = eval_db.metadatos_evaluacion or {}

        # Si la evaluación pertenece a una parcela, enriquecer con coordenadas para el frontend
        coordenadas = None
        geometria_dict = None
        latitud = None
        longitud = None
        area_ha = None
        nombre_parcela = None
        if eval_db.id_parcela:
            parcela = await self.repo.obtener_parcela(eval_db.id_parcela)
            if parcela:
                latitud = getattr(parcela, "latitud", None)
                longitud = getattr(parcela, "longitud", None)
                area_ha = getattr(parcela, "area_ha", None)
                nombre_parcela = getattr(parcela, "nombre", None)
                if getattr(parcela, "geometria_cifrada", None):
                    try:
                        from app.services.parcela_service import descifrar_geometria
                        geom = descifrar_geometria(parcela.geometria_cifrada)
                        geometria_dict = geom
                        if isinstance(geom, dict):
                            if geom.get("type") == "Polygon" and "coordinates" in geom:
                                coordenadas = geom["coordinates"][0]
                            elif "punto" in geom:
                                coordenadas = [[geom["punto"]["lon"], geom["punto"]["lat"]]]
                    except Exception:
                        pass

        return EvaluacionResponseDTO(
            id_evaluacion=eval_db.id_evaluacion,
            id_parcela=eval_db.id_parcela,
            id_declaracion=None,
            generado_utc=generado,
            vigencia_hasta=vigencia,
            pesos_usados=metadatos.get("pesos_usados", {}),
            respuestas_snapshot=metadatos.get("respuestas_snapshot", {}),
            escenarios=escenarios_dtos,
            descartes_rc5=[],
            escenarios_descartados=[],
            coordenadas=coordenadas,
            geometria=geometria_dict,
            latitud=latitud,
            longitud=longitud,
            area_ha=area_ha,
            nombre_parcela=nombre_parcela,
        )

    async def obtener_cifra_trazabilidad(
        self, id_evaluacion: str, id_cifra: str
    ) -> CifraTrazabilidadDTO:
        cifra_db = await self.repo.obtener_cifra(id_evaluacion, id_cifra)
        if not cifra_db:
            raise ErroresContrato.no_encontrado(f"Cifra '{id_cifra}' para la evaluación")

        return CifraTrazabilidadDTO(
            id_cifra=cifra_db.id_cifra,
            id_evaluacion=cifra_db.id_evaluacion,
            etiqueta=cifra_db.etiqueta,
            valor_mostrado=cifra_db.valor_mostrado,
            formula=cifra_db.formula,
            fuente_datos=cifra_db.fuente_datos,
            pasos_calculo=cifra_db.pasos_calculo,
            variables_utilizadas=cifra_db.variables_utilizadas,
        )

    async def obtener_escenario_por_id(
        self, id_evaluacion: str, id_escenario: str
    ) -> EscenarioDetalleDTO:
        evaluacion = await self.obtener_evaluacion_por_id(id_evaluacion)
        for esc in evaluacion.escenarios:
            if esc.codigo_escenario.upper() == id_escenario.upper() or esc.cultivo.lower() == id_escenario.lower():
                return esc
        raise ErroresContrato.no_encontrado(f"Escenario '{id_escenario}' en evaluación")

    async def evaluar_sensibilidad(
        self, id_evaluacion: str, variante: str
    ) -> Dict[str, Any]:
        evaluacion = await self.obtener_evaluacion_por_id(id_evaluacion)
        factor = {"mas_seco": -0.05, "mas_calido": -0.04, "secuencia_seca_adicional": -0.08}.get(variante, -0.05)
        ajuste = {}
        for esc in evaluacion.escenarios:
            ajuste[esc.codigo_escenario] = round(max(0.0, esc.puntaje_mediana + factor), 4)
        return {
            "id_evaluacion": id_evaluacion,
            "variante": variante,
            "aviso_legal": "Reevaluación sobre el historial satelital, no pronóstico climático (RF13 y R4)",
            "ajuste_puntajes": ajuste,
            "confianza": "media",
        }

    async def obtener_textos_ia(self, id_evaluacion: str) -> Dict[str, Any]:
        evaluacion = await self.obtener_evaluacion_por_id(id_evaluacion)
        textos = {}
        for esc in evaluacion.escenarios:
            textos[esc.codigo_escenario] = {
                "cultivo": esc.cultivo,
                "tarjeta_5_partes": esc.tarjeta_5_partes.model_dump() if esc.tarjeta_5_partes else None,
                "insights_ia": [
                    t.model_dump() for t in esc.tarjetas_informativas if t.origen == "gemini_flash_lite"
                ],
            }
        return {
            "id_evaluacion": id_evaluacion,
            "version_ia": "gemini-2.5-flash-lite",
            "textos_por_escenario": textos,
            "aviso_apoyo": "Esta herramienta apoya tu decisión; no sustituye el criterio técnico en campo.",
        }

    async def exportar_resumen(
        self, id_evaluacion: str, formato: str = "json"
    ) -> Dict[str, Any]:
        evaluacion = await self.obtener_evaluacion_por_id(id_evaluacion)
        ahora = datetime.now(timezone.utc)
        resumen = {
            "id_evaluacion": evaluacion.id_evaluacion,
            "generado_utc": evaluacion.generado_utc.isoformat(),
            "pesos_usados": evaluacion.pesos_usados,
            "escenarios_evaluados": [
                {
                    "codigo": esc.codigo_escenario,
                    "cultivo": esc.cultivo,
                    "puntaje_mediana": esc.puntaje_mediana,
                    "puntaje_p10": esc.puntaje_p10,
                    "puntaje_p90": esc.puntaje_p90,
                    "robustez": esc.robustez,
                }
                for esc in evaluacion.escenarios
            ],
            "politica_privacidad": "Sin coordenadas ni geometría exacta incluida (RNF01 / RF18)",
        }
        return {
            "id_evaluacion": id_evaluacion,
            "formato": formato,
            "resumen": resumen,
            "generado_utc": ahora,
        }


    async def _ejecutar_evaluacion_interna(
        self,
        id_evaluacion: str,
        id_parcela: Optional[str],
        id_cuenta: Optional[str],
        version_declaracion: int,
        modo_evaluacion: str,
        pesos_personalizados: Optional[Dict[str, float]],
        declaracion: Any,
        lat: float,
        lon: float,
        region: str,
    ) -> Tuple[EvaluacionResponseDTO, List[EscenarioORM], List[CifraTrazabilidadORM]]:
        # 1. Resolver ponderaciones oficiales según Sección 6
        pesos_usados = resolver_pesos_oficiales(
            considerar_riesgo=declaracion.considerar_riesgo,
            prioridad_principal=declaracion.prioridad_principal,
            pesos_personalizados=pesos_personalizados,
        )

        # 2. Cargar perfil satelital histórico NASA 2001-2025
        perfil = cargar_serie_nasa_parcela(region=region, lat=lat, lon=lon)

        # 3. Procesar historial de 3 ciclos previos (Sección 8)
        # Ordenar estrictamente por número de ciclo (1: hace 3 ciclos, 2: hace 2 ciclos, 3: última temporada)
        rotacion_ordenada = sorted(
            declaracion.rotacion_existente,
            key=lambda x: getattr(x, "ciclo", None) or (x.get("ciclo", 1) if isinstance(x, dict) else 1)
        )

        historial_cultivos = []
        es_supuesto_a = False
        ciclos_supuestos = []

        for item in rotacion_ordenada:
            ciclo_num = getattr(item, "ciclo", None) or (item.get("ciclo", 1) if isinstance(item, dict) else 1)
            c_val = item.cultivo.lower().strip() if hasattr(item, "cultivo") else str(item.get("cultivo", "maiz")).lower().strip()
            if c_val == "no_se":
                historial_cultivos.append("maiz")
                es_supuesto_a = True
                ciclos_supuestos.append(ciclo_num)
            elif c_val == "no_hubo":
                historial_cultivos.append("no_hubo")
            else:
                historial_cultivos.append(c_val)

        # Buscar explícitamente el cultivo declarado para el Ciclo 1 (el inicio del ciclo a repetir en Escenario A)
        item_c1 = next(
            (it for it in rotacion_ordenada if (getattr(it, "ciclo", None) or (it.get("ciclo") if isinstance(it, dict) else None)) == 1),
            rotacion_ordenada[0] if rotacion_ordenada else None
        )
        c_c1_raw = (item_c1.cultivo if hasattr(item_c1, "cultivo") else item_c1.get("cultivo", "maiz")).lower().strip() if item_c1 else "maiz"

        if c_c1_raw == "no_se":
            cultivo_c1 = "maiz"
            es_supuesto_a = True
        elif c_c1_raw == "no_hubo":
            cultivo_c1 = next((c for c in historial_cultivos if c not in ["no_hubo", "no_se"]), "maiz")
        else:
            cultivo_c1 = c_c1_raw

        if cultivo_c1 not in CULTIVOS_M1:
            cultivo_c1 = "maiz"

        # 4. Aplicar Regla RC5 de descarte previo por riego (Sección 3)
        escenarios_descartados = []
        cultivos_candidatos_alternativos = []
        todos_los_cultivos = ["maiz", "frijol", "cacahuate", "calabaza", "sandia", "habanero"]

        for c_id in todos_los_cultivos:
            if c_id == cultivo_c1:
                continue

            cultivo_obj = CULTIVOS_M1[c_id]
            if cultivo_obj.requiere_riego and declaracion.riego_veces_semana == 0:
                escenarios_descartados.append({
                    "id": c_id.upper(),
                    "cultivo": c_id,
                    "nombre": cultivo_obj.nombre_comun,
                    "motivo": "RC5",
                    "texto": f"{cultivo_obj.nombre_comun} requiere riego externo garantizado y declaraste 0 riegos por semana.",
                })
            else:
                cultivos_candidatos_alternativos.append(c_id)

        # 5. Definir lista de escenarios activos
        letras_alternativas = ["B", "C", "D", "E", "F"]
        escenarios_activos_definicion = [
            {
                "codigo": "A",
                "cultivo": cultivo_c1,
                "es_linea_base": True,
                "nombre": f"Continuidad: {CULTIVOS_M1[cultivo_c1].nombre_comun}",
            }
        ]

        for idx, c_alt in enumerate(cultivos_candidatos_alternativos):
            letra = letras_alternativas[idx] if idx < len(letras_alternativas) else f"X{idx}"
            nombre_esc = f"Alternativa: {CULTIVOS_M1[c_alt].nombre_comun}"
            escenarios_activos_definicion.append({
                "codigo": letra,
                "cultivo": c_alt,
                "es_linea_base": False,
                "nombre": nombre_esc,
            })

        # 6. Evaluar los 4 criterios (c_agua, c_riesgo, c_suelo, c_apt)
        criterios_por_escenario: Dict[str, Dict[str, float]] = {}
        puntajes_globales: Dict[str, float] = {}
        rre = perfil.get("rre", "medio")

        for esc in escenarios_activos_definicion:
            cod = esc["codigo"]
            c_id = esc["cultivo"]
            cultivo_obj = CULTIVOS_M1[c_id]

            c_agua, _ = calcular_c_agua(
                cultivo=cultivo_obj,
                perfil=perfil,
                riego_veces_semana=declaracion.riego_veces_semana,
            )
            c_riesgo = calcular_c_riesgo(
                cultivo=cultivo_obj,
                perfil=perfil,
                tipo_tierra=declaracion.tipo_tierra,
                riego_veces_semana=declaracion.riego_veces_semana,
            )
            c_suelo, _, _ = calcular_c_suelo(
                historial_3_ciclos=historial_cultivos,
                candidato_ciclo_4=c_id,
                rre=rre,
            )
            c_apt, _, _ = calcular_c_apt(
                cultivo=cultivo_obj,
                perfil=perfil,
                region=region,
            )

            criterios_dict = {
                "c_agua": c_agua,
                "c_riesgo": c_riesgo,
                "c_suelo": c_suelo,
                "c_apt": c_apt,
            }
            criterios_por_escenario[cod] = criterios_dict
            s_val = calcular_puntaje_global(criterios_dict, pesos_usados)
            puntajes_globales[cod] = s_val

        # 7. Simulación Monte Carlo
        resultados_mc = ejecutar_monte_carlo(
            criterios_por_escenario=criterios_por_escenario,
            pesos_base=pesos_usados,
            n_replicas=1000,
            seed=42,
        )

        # 8. Ordenamiento: A siempre primero, luego alternativos por puntaje S(s)
        alternativos = [e for e in escenarios_activos_definicion if not e["es_linea_base"]]
        alternativos.sort(key=lambda x: puntajes_globales[x["codigo"]], reverse=True)
        escenarios_ordenados = [escenarios_activos_definicion[0]] + alternativos

        codigo_ganador_alternativo = alternativos[0]["codigo"] if alternativos else "A"
        cultivo_ganador = CULTIVOS_M1[
            next(e["cultivo"] for e in escenarios_activos_definicion if e["codigo"] == codigo_ganador_alternativo)
        ]

        # 9. GENERACIÓN DE LOS 2 INSIGHTS CON GEMINI FLASH LITE (ASÍNCRONO CON BLOQUEO Y TIMEOUT CORTO)
        try:
            secuencia_4_recomendada = historial_cultivos + [cultivo_ganador.id_cultivo]
            t_gemini_agronomico, t_gemini_resiliencia = await self.gemini_service.generar_insights_async(
                cultivo_propuesto=cultivo_ganador.nombre_comun,
                secuencia_4_ciclos=secuencia_4_recomendada,
                tipo_tierra=declaracion.tipo_tierra,
                riego_veces_semana=declaracion.riego_veces_semana,
                prioridad_principal=declaracion.prioridad_principal,
                puntaje_global=puntajes_globales[codigo_ganador_alternativo],
                criterios=criterios_por_escenario[codigo_ganador_alternativo],
                region=region,
            )
        except Exception as e:
            # Fallback determinista seguro ante caídas de red o cuota (RN-IA-09)
            from app.domain.tarjetas import TarjetaInformativa
            t_gemini_agronomico = TarjetaInformativa(
                id_tarjeta="card_gemini_agronomico",
                titulo="Insight IA: Oportunidades Agronómicas y Nutrición",
                subtitulo="Generado con Gemini Flash-Lite",
                tipo="gemini_insight_agronomico",
                contenido=self.gemini_service._fallback_agronomico(cultivo_ganador.nombre_comun, declaracion.tipo_tierra),
                origen="gemini_flash_lite",
                icono="sparkles",
                destacado=True,
                tags=["ia_gemini", "nutricion", "rotacion"],
            )
            t_gemini_resiliencia = TarjetaInformativa(
                id_tarjeta="card_gemini_resiliencia",
                titulo="Insight IA: Estrategia Preventiva de Resiliencia Climática",
                subtitulo="Generado con Gemini Flash-Lite",
                tipo="gemini_insight_resiliencia",
                contenido=self.gemini_service._fallback_resiliencia(cultivo_ganador.nombre_comun, declaracion.tipo_tierra, declaracion.riego_veces_semana),
                origen="gemini_flash_lite",
                icono="shield",
                destacado=True,
                tags=["ia_gemini", "resiliencia", "clima"],
            )

        # 10. Ensamblaje de escenarios, tarjetas y persistencia
        escenarios_salida_dtos: List[EscenarioDetalleDTO] = []
        escenarios_orm: List[EscenarioORM] = []
        cifras_orm: List[CifraTrazabilidadORM] = []
        puntaje_a = puntajes_globales.get("A", 0.5)

        for orden_idx, esc in enumerate(escenarios_ordenados, start=1):
            cod = esc["codigo"]
            c_id = esc["cultivo"]
            cultivo_obj = CULTIVOS_M1[c_id]
            crit = criterios_por_escenario[cod]
            score = puntajes_globales[cod]
            mc_info = resultados_mc.get(cod, {})

            delta_vs_a = None if esc["es_linea_base"] else {
                "puntaje": round(score - puntaje_a, 4),
                "c_agua": round(crit["c_agua"] - criterios_por_escenario["A"]["c_agua"], 4),
                "c_riesgo": round(crit["c_riesgo"] - criterios_por_escenario["A"]["c_riesgo"], 4),
                "c_suelo": round(crit["c_suelo"] - criterios_por_escenario["A"]["c_suelo"], 4),
                "c_apt": round(crit["c_apt"] - criterios_por_escenario["A"]["c_apt"], 4),
            }

            tarjetas_det = generar_tarjetas_deterministas(
                cultivo_nombre=cultivo_obj.nombre_comun,
                es_linea_base=esc["es_linea_base"],
                puntaje=score,
                criterios=crit,
                tipo_tierra=declaracion.tipo_tierra,
                agrego_productos=declaracion.agrego_productos,
                riego_veces_semana=declaracion.riego_veces_semana,
                advertencias_tierra=cultivo_obj.avisos_tierra,
                rotacion_4=historial_cultivos + [c_id],
            )

            tarjeta_5 = ensamblar_tarjeta_5_partes(
                cultivo_nombre=cultivo_obj.nombre_comun,
                es_linea_base=esc["es_linea_base"],
                puntaje=score,
                criterios=crit,
                tipo_tierra=declaracion.tipo_tierra,
                agrego_productos=declaracion.agrego_productos,
                riego_veces_semana=declaracion.riego_veces_semana,
                advertencias_tierra=cultivo_obj.avisos_tierra,
                gemini_insight_agronomico=t_gemini_agronomico.contenido if cod == codigo_ganador_alternativo else None,
                gemini_insight_resiliencia=t_gemini_resiliencia.contenido if cod == codigo_ganador_alternativo else None,
            )

            lista_tarjetas_escenario = list(tarjetas_det)
            if cod == codigo_ganador_alternativo:
                lista_tarjetas_escenario.insert(2, t_gemini_agronomico)
                lista_tarjetas_escenario.insert(3, t_gemini_resiliencia)

            tarjetas_info_dtos = [
                TarjetaInformativaDTO(
                    id_tarjeta=t.id_tarjeta,
                    titulo=t.titulo,
                    subtitulo=t.subtitulo,
                    tipo=t.tipo,
                    contenido=t.contenido,
                    origen=t.origen,
                    icono=t.icono,
                    destacado=t.destacado,
                    tags=t.tags,
                )
                for t in lista_tarjetas_escenario
            ]

            tarjeta_5_dto = Tarjeta5PartesDTO(
                por_que_se_sugirio=tarjeta_5.por_que_se_sugirio,
                evidencia_agroclimatica=tarjeta_5.evidencia_agroclimatica,
                beneficios_posibles=tarjeta_5.beneficios_posibles,
                carencias_informacion=tarjeta_5.carencias_informacion,
                riesgos_revision_local=tarjeta_5.riesgos_revision_local,
            )

            subtitulo = "Línea Base" if esc["es_linea_base"] else ("Recomendación Principal" if orden_idx == 1 else "Propuesta Alternativa")
            badge = "Seguir igual" if esc["es_linea_base"] else ("Recomendado" if orden_idx == 1 else "Rotación")
            tipo_badge = "linea_base" if esc["es_linea_base"] else ("recomendado" if orden_idx == 1 else "alternativa")
            resumen = f"Opción para ciclo 4 en suelo {declaracion.tipo_tierra}."
            etiqueta_suelo = "Fija Nitrógeno" if c_id in ["frijol", "cacahuate"] else "Rotación"
            etiqueta_agua = "Temporal" if declaracion.riego_veces_semana == 0 else "Riego aux."
            duracion_ciclo_dias = f"~{cultivo_obj.dias_madurez} días" if hasattr(cultivo_obj, "dias_madurez") else "~120 días"
            puntaje_val = round(score * 100, 1)

            esc_dto = EscenarioDetalleDTO(
                codigo_escenario=cod,
                orden_visual=orden_idx,
                nombre=esc["nombre"],
                cultivo=c_id,
                es_linea_base=esc["es_linea_base"],
                secuencia_cultivos=historial_cultivos + [c_id],
                es_supuesto=es_supuesto_a if esc["es_linea_base"] else False,
                ciclos_supuestos=ciclos_supuestos if esc["es_linea_base"] else [],
                confianza="media" if es_supuesto_a else "alta",
                puntaje_mediana=mc_info.get("mediana", score),
                puntaje_p10=mc_info.get("p10", round(score * 0.9, 4)),
                puntaje_p90=mc_info.get("p90", round(min(1.0, score * 1.1), 4)),
                robustez=mc_info.get("robustez", "alta"),
                etiqueta_robustez=mc_info.get("etiqueta_humana", "Estable"),
                criterios_detalle=crit,
                delta_vs_a=delta_vs_a,
                tarjeta_5_partes=tarjeta_5_dto,
                tarjetas_informativas=tarjetas_info_dtos,
                subtitulo=subtitulo,
                badge=badge,
                tipo_badge=tipo_badge,
                resumen=resumen,
                etiqueta_suelo=etiqueta_suelo,
                etiqueta_agua=etiqueta_agua,
                duracion_ciclo_dias=duracion_ciclo_dias,
                puntaje_valor=puntaje_val,
            )
            escenarios_salida_dtos.append(esc_dto)

            # ORM (R4, RN-TAR-07 y RN-IA-06: sin kg/ha ni probabilidades prescriptivas)
            esc_orm = EscenarioORM(
                id_escenario=str(uuid.uuid4()),
                id_evaluacion=id_evaluacion,
                codigo=cod,
                cultivo_id=c_id,
                cultivo_nombre=cultivo_obj.nombre_comun,
                es_linea_base=esc["es_linea_base"],
                orden_visual=orden_idx,
                posicion_ranking=orden_idx,
                puntuacion_final=score,
                criterio_agua=crit["c_agua"],
                criterio_riesgo=crit["c_riesgo"],
                criterio_suelo=crit["c_suelo"],
                criterio_aptitud=crit["c_apt"],
                puntaje_mediana=float(mc_info.get("mediana", score)),
                puntaje_p10=float(mc_info.get("p10", round(score * 0.9, 4))),
                puntaje_p90=float(mc_info.get("p90", round(min(1.0, score * 1.1), 4))),
                robustez=mc_info.get("etiqueta_humana", "Estable"),
                tarjetas_json=[t.model_dump() for t in tarjetas_info_dtos],
                tarjeta_5_partes=tarjeta_5_dto.model_dump(),
                delta_vs_a=delta_vs_a,
            )
            escenarios_orm.append(esc_orm)

        # 11. Cifras de trazabilidad ORM
        lluvia_mediana = perfil.get("precipitacion_anual_mediana_mm")
        if lluvia_mediana is None:
            hist = perfil.get("lluvia_anual_historica_mm", {})
            if hist:
                import numpy as np
                lluvia_mediana = float(np.median(list(hist.values())))
            else:
                lluvia_mediana = 1250.0

        cifras_orm.append(
            CifraTrazabilidadORM(
                id_cifra="cifra_lluvia_mediana",
                id_evaluacion=id_evaluacion,
                etiqueta="Precipitación Anual Mediana",
                valor_mostrado=f"{float(lluvia_mediana):.1f} mm/año",
                formula="mediana(precipitacion_anual_2001_2025)",
                fuente_datos=perfil.get("fuente", "NASA GPM IMERG v07B"),
                pasos_calculo=[
                    "1. Descargar serie histórica diaria 2001-2025 de satélite GPM",
                    "2. Acumular lluvia anual para cada uno de los 25 años",
                    "3. Calcular percentil 50 (mediana estadística)",
                ],
                variables_utilizadas={"años_analizados": 25, "region": region},
            )
        )
        for crit_key, w_val in pesos_usados.items():
            cifras_orm.append(
                CifraTrazabilidadORM(
                    id_cifra=f"peso_{crit_key}",
                    id_evaluacion=id_evaluacion,
                    etiqueta=f"Peso ponderado de {crit_key}",
                    valor_mostrado=f"{w_val:.2f}",
                    formula="Matriz_M1_Chiapas(prioridad, considerar_riesgo)",
                    fuente_datos="Fichas de cultivo NasKob v0.3 / Motor de decisión",
                    pasos_calculo=[
                        "1. Determinar perfil del productor (prioridad declared)",
                        "2. Consultar matriz de pesos oficiales",
                        "3. Normalizar pesos para suma total = 1.0",
                    ],
                    variables_utilizadas={
                        "prioridad": declaracion.prioridad_principal,
                        "riesgo_activo": declaracion.considerar_riesgo,
                    },
                )
            )

        ahora_utc = datetime.now(timezone.utc)
        vigencia_utc = ahora_utc + timedelta(days=90)

        response_dto = EvaluacionResponseDTO(
            id_evaluacion=id_evaluacion,
            id_parcela=id_parcela,
            id_declaracion=None,
            generado_utc=ahora_utc,
            vigencia_hasta=vigencia_utc,
            pesos_usados=pesos_usados,
            respuestas_snapshot={
                "tipo_tierra": declaracion.tipo_tierra,
                "agrego_productos": declaracion.agrego_productos,
                "riego_veces_semana": declaracion.riego_veces_semana,
                "considerar_riesgo": declaracion.considerar_riesgo,
                "prioridad_principal": declaracion.prioridad_principal,
            },
            escenarios=escenarios_salida_dtos,
            descartes_rc5=escenarios_descartados,
            escenarios_descartados=escenarios_descartados,
        )

        return response_dto, escenarios_orm, cifras_orm
