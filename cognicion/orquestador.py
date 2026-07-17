"""
Orquestador cognitivo — kernel de coordinación de pilares cognitivos.
Clasifica intención, activa skills y enriquece el mensaje antes del LLM.
"""

from __future__ import annotations

from typing import Any, Protocol

from cognicion.agente.autonomo import AgenteAutonomo, ResultadoAgente, debe_ejecutar_agente
from cognicion.aprendizaje import ResultadoAprendizaje, procesar_turno
from cognicion.autocorreccion.ciclo import (
    analizar_error_consola,
    es_mensaje_de_error,
    preparar_contexto_autocorreccion,
)
from cognicion.conectores import consultar_conectores
from cognicion.busqueda import necesita_busqueda_web, responder_con_busqueda
from cognicion.memoria.gestor import GestorMemoria
from cognicion.memoria.memory_controller import MemoryController
from cognicion.memoria.vectorial import obtener_memoria
from settings import BUSQUEDA_WEB_AUTO
from cognicion.razonamiento.cadena import (
    aplicar_cadena_de_pensamiento,
)
from cognicion.razonamiento.empatia import bloque_empatia
from cognicion.codigo.motor_universal import bloque_motor_codigo
from cognicion.multimodal import es_generacion_visual
from cognicion.vision.busqueda_visual import es_busqueda_visual, recuperar_o_generar
from cognicion.razonamiento.intencion import (
    Intencion,
    clasificar_intencion,
    planificar,
)
from cognicion.registro import evento, obtener_logger
from cognicion.skills import ejecutar_hook, listar_skills, skills_para_intencion
from cognicion.nucleo import obtener_nucleo
from cognicion.vision.analizador import analizar_imagen

_log = obtener_logger("orquestador")


class OrquestadorCognitivo(Protocol):
    """Contrato del orquestador — permite sustituir implementación."""

    session_id: str

    def ejecutar_agente(
        self,
        tarea: str,
        error_consola: str | None = None,
        autonomo: bool = False,
    ) -> ResultadoAgente: ...

    def enriquecer_mensaje(
        self,
        entrada: str,
        lat: float | None = None,
        lon: float | None = None,
        imagen_base64: str | None = None,
        imagen_mime: str = "image/png",
        error_consola: str | None = None,
        contexto_agente: str | None = None,
        autonomo: bool = False,
    ) -> tuple[str, dict[str, Any]]: ...

    def registrar_turno(self, usuario: str, asistente: str) -> None: ...

    def aprender_turno(
        self,
        usuario: str,
        asistente: str,
        metadata_turno: dict[str, Any] | None = None,
    ) -> ResultadoAprendizaje: ...


class MotorCognicion:
    """Coordina los pilares cognitivos de Salomón."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._gestor = GestorMemoria(session_id, obtener_memoria())
        self._memory = MemoryController(session_id)
        self._agente = AgenteAutonomo()
        self._ultima_intencion: Intencion = Intencion.CHAT
        self._ultimo_plan: dict[str, Any] = {}

    @property
    def memoria(self):
        """Compatibilidad — expone la memoria vectorial subyacente."""
        return self._gestor.vectorial

    @property
    def gestor(self) -> GestorMemoria:
        return self._gestor

    @property
    def memory(self) -> MemoryController:
        return self._memory

    def ejecutar_agente(
        self,
        tarea: str,
        error_consola: str | None = None,
        autonomo: bool = False,
    ) -> ResultadoAgente:
        """Ejecuta el agente autónomo si las condiciones lo permiten."""
        if not debe_ejecutar_agente(tarea, error_consola, autonomo):
            return ResultadoAgente(ejecutado=False, exito=False)

        return self._agente.corregir(tarea, error=error_consola)

    def enriquecer_mensaje(
        self,
        entrada: str,
        lat: float | None = None,
        lon: float | None = None,
        imagen_base64: str | None = None,
        imagen_mime: str = "image/png",
        error_consola: str | None = None,
        contexto_agente: str | None = None,
        autonomo: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        """
        Clasifica intención, planifica y aplica RAG, conectores, visión,
        auto-corrección y razonamiento según corresponda.
        """
        intencion = clasificar_intencion(
            entrada,
            error_consola=error_consola,
            imagen_base64=imagen_base64,
            autonomo=autonomo,
        )
        plan = planificar(intencion)
        self._ultima_intencion = intencion
        evento(
            _log,
            "enriquecer",
            session=self.session_id,
            intencion=intencion.value,
            skills=[s.id for s in skills_para_intencion(intencion)],
        )
        obtener_nucleo().eventos.emitir(
            "turno:enriquecer",
            session_id=self.session_id,
            intencion=intencion.value,
            skills=[s.id for s in skills_para_intencion(intencion)],
        )

        bloques: list[str] = []
        meta: dict[str, Any] = {
            "cognicion": {
                "memoria_activa": self._gestor.activa,
                "intencion": intencion.value,
                "skills_activas": [s.id for s in skills_para_intencion(intencion)],
                "skills_registradas": [s.id for s in listar_skills()],
                "modelo_prioridad": plan.prioridad_modelo,
            }
        }
        self._ultimo_plan = meta["cognicion"]

        if plan.usar_rag:
            # Memoria unificada (inmediata + personal + RAG + JSON de sesión)
            ctx_mem, meta_mem = self._memory.contexto_para_turno(entrada)
            if ctx_mem:
                bloques.append(ctx_mem)
                meta["cognicion"]["rag_usado"] = True
                meta["cognicion"]["memoria"] = meta_mem
                meta["cognicion"]["memory_controller"] = True
            else:
                rag, meta_memoria = self._gestor.contexto_rag(entrada)
                if rag:
                    bloques.append(rag)
                    meta["cognicion"]["rag_usado"] = True
                    meta["cognicion"]["memoria"] = meta_memoria

        # Búsqueda web en el camino de /api/chat (agente externo)
        if BUSQUEDA_WEB_AUTO and necesita_busqueda_web(entrada):
            try:
                pack = responder_con_busqueda(entrada)
                busq = pack.get("busqueda") or {}
                texto_busq = (pack.get("texto") or "").strip()
                if texto_busq:
                    bloques.append(
                        "[Búsqueda web en vivo]\n"
                        f"{texto_busq[:2200]}\n"
                        "Instrucción: Usa estos hechos actuales en tu respuesta. "
                        "Cita el origen de forma natural si aplica."
                    )
                    meta["busqueda_web_agente"] = True
                    meta["busqueda_consultada"] = True
                    meta["busqueda_motor"] = pack.get("motor") or busq.get("motor")
                    meta["cognicion"]["busqueda_web"] = {
                        "ok": bool(pack.get("exito")),
                        "motor": pack.get("motor") or busq.get("motor"),
                    }
            except Exception as exc:
                meta["cognicion"]["busqueda_web_error"] = type(exc).__name__

        _, resultados = consultar_conectores(entrada, lat=lat, lon=lon)
        for resultado in resultados:
            bloques.append(resultado.contexto)
            if resultado.nombre == "clima":
                meta["clima_consultado"] = True
            if resultado.nombre == "wikipedia":
                meta["wikipedia_consultado"] = True
            if resultado.nombre == "wikidata":
                meta["wikidata_consultado"] = True
            if resultado.nombre == "busqueda":
                meta["busqueda_consultada"] = True
            if resultado.nombre == "noticias":
                meta["noticias_consultadas"] = True
            meta.update(resultado.metadata)

        mensaje_trabajo = entrada

        if plan.usar_vision and imagen_base64:
            vision = analizar_imagen(
                imagen_base64,
                mime_type=imagen_mime,
                contexto_usuario=entrada,
            )
            if vision.exito:
                bloques.append(vision.contexto)
                meta["cognicion"]["vision_usado"] = True
            else:
                bloques.append(
                    "[Análisis visual no disponible] "
                    "Informa al usuario que no se pudo analizar la imagen."
                )
                meta["cognicion"]["vision_error"] = vision.error

        error_texto = (error_consola or "").strip()
        if plan.usar_autocorreccion:
            if not error_texto and es_mensaje_de_error(entrada):
                error_texto = entrada
            if error_texto:
                bloques.append(preparar_contexto_autocorreccion(error_texto))
                meta["cognicion"]["autocorreccion"] = True
                meta["cognicion"]["error_analisis"] = analizar_error_consola(error_texto)

        if contexto_agente:
            bloques.append(contexto_agente)
            meta["cognicion"]["agente_autonomo"] = True

        # Empatía cognitiva (siempre — ajusta tono del turno)
        emp_bloque, emp_meta = bloque_empatia(entrada)
        bloques.append(emp_bloque)
        meta["cognicion"]["empatia"] = emp_meta

        # Multimodal Core — búsqueda / generación visual (sin tocar CameraEngine)
        if es_busqueda_visual(entrada):
            try:
                vis = recuperar_o_generar(entrada)
                meta["cognicion"]["multimodal"] = {
                    "accion": vis.get("accion"),
                    "exito": vis.get("exito"),
                    "latencia_ms": vis.get("latencia_ms") or (vis.get("generacion") or {}).get("latencia_ms"),
                    "progreso_requerido": vis.get("progreso_requerido")
                    or (vis.get("generacion") or {}).get("progreso_requerido"),
                }
                if vis.get("accion") == "recuperado" and (vis.get("mejor") or {}).get("url"):
                    m = vis["mejor"]
                    bloques.append(
                        "[Agente de Recuperación Visual]\n"
                        f"Consulta: {vis.get('consulta')}\n"
                        f"Mejor opción HD: {m.get('titulo')} — {m.get('url')}\n"
                        f"Snippet: {m.get('snippet')}\n"
                        "Presenta esta imagen a Israel con enlace y breve justificación."
                    )
                elif vis.get("generacion"):
                    gen = vis["generacion"]
                    res = gen.get("resultado") or {}
                    url = res.get("url_relativa") or ""
                    bloques.append(
                        "[Multimodal Core — Generación HD]\n"
                        f"No hubo match visual perfecto; generé material HD.\n"
                        f"Motor: {res.get('motor')} · URL: {url}\n"
                        "Describe el resultado y comparte la URL relativa al usuario."
                    )
                    meta["cognicion"]["media_url"] = url
                    meta["cognicion"]["prompt_enhancer"] = gen.get("prompt_enhancer")
            except Exception as exc:
                meta["cognicion"]["multimodal_error"] = type(exc).__name__
        elif es_generacion_visual(entrada):
            try:
                from cognicion.media.media_engine import bridge_colsub_media

                hint = "video_gen" if "video" in entrada.lower() else "imagen_hd"
                gen = bridge_colsub_media(entrada, hint=hint)
                res = gen.get("resultado") or {}
                url = res.get("url_relativa") or ""
                meta["cognicion"]["multimodal"] = {
                    "accion": "generado",
                    "exito": gen.get("exito"),
                    "tarea": gen.get("tarea"),
                    "latencia_ms": gen.get("latencia_ms"),
                    "progreso_requerido": gen.get("progreso_requerido"),
                    "motor": res.get("motor"),
                }
                meta["cognicion"]["media_url"] = url
                meta["cognicion"]["prompt_enhancer"] = {
                    "activo": gen.get("prompt_enhancer"),
                    "motor": gen.get("motor_enhancer"),
                    "original": gen.get("prompt_original"),
                }
                bloques.append(
                    "[Multimodal Core — HD Generator]\n"
                    f"Prompt Enhancer: {gen.get('motor_enhancer')}\n"
                    f"Motor: {res.get('motor')} · calidad: {res.get('calidad')}\n"
                    f"Activo: {url or '(pendiente / async)'}\n"
                    f"Latencia: {gen.get('latencia_ms')}ms · "
                    f"progreso_ui={gen.get('progreso_requerido')}\n"
                    "Informa a Israel el resultado con el enlace y confirma que "
                    "el material se creó dentro de Salomón Viviente."
                )
            except Exception as exc:
                meta["cognicion"]["multimodal_error"] = type(exc).__name__

        # Universal Code Engine (matemática sandbox + prompt de ingeniería)
        uce = bloque_motor_codigo(entrada)
        meta["cognicion"]["universal_code_engine"] = uce.to_dict()
        if uce.bloque_contexto:
            bloques.append(uce.bloque_contexto)

        usar_cot = plan.usar_razonamiento or (
            uce.activo and uce.tipo in {"ingenieria", "matematica"}
        )
        if usar_cot:
            mensaje_trabajo = aplicar_cadena_de_pensamiento(
                entrada,
                tono_bloque=emp_bloque,
            )
            meta["cognicion"]["razonamiento_cot"] = True
            meta["cognicion"]["cognitive_core"] = {
                "version": "60.0.0",
                "ciclo": ["analisis", "planificacion", "ejecucion", "verificacion"],
            }

        hooks_ejecutados: list[str] = []
        for skill in skills_para_intencion(intencion):
            extra = ejecutar_hook(
                skill.id,
                entrada=entrada,
                session_id=self.session_id,
                intencion=intencion.value,
            )
            if extra and isinstance(extra, str):
                bloques.append(extra)
                hooks_ejecutados.append(skill.id)
        if hooks_ejecutados:
            meta["cognicion"]["hooks_ejecutados"] = hooks_ejecutados

        if bloques:
            mensaje_final = "\n\n".join(bloques) + f"\n\nPregunta del usuario: {mensaje_trabajo}"
        else:
            mensaje_final = mensaje_trabajo

        return mensaje_final, meta

    def registrar_turno(self, usuario: str, asistente: str) -> None:
        """Persiste el turno en memoria (vectorial + JSON de sesión)."""
        try:
            self._memory.recordar_turno(usuario, asistente)
        except Exception:
            self._gestor.guardar_turno(usuario, asistente)

    def aprender_turno(
        self,
        usuario: str,
        asistente: str,
        metadata_turno: dict[str, Any] | None = None,
    ) -> ResultadoAprendizaje:
        """Reflexión post-turno — actualiza memoria de aprendizaje."""
        return procesar_turno(
            self.session_id,
            usuario,
            asistente,
            self._gestor,
            metadata_turno=metadata_turno,
        )
