# -*- coding: utf-8 -*-
"""
ServiceManager — única ruta neuronal de ejecución (modo producción).

Todas las llamadas a LLM / voz / media / embeddings / web pasan por aquí.
No hay simulaciones: si la clave existe en Render, se usa el proveedor real.
"""

from __future__ import annotations

import base64
import uuid
from pathlib import Path
from typing import Any

from config.providers import Servicio, seleccionar
from cognicion.registro import evento, obtener_logger
from cognicion.servicios.clientes import ClienteNoDisponible, obtener_cliente
from cognicion.servicios.registry import ServiceRegistry
from cognicion.voz.tipos import ResultadoTTS
from settings import DATA_DIR

_log = obtener_logger("servicios.manager")
_MANAGER: "ServiceManager | None" = None

_DIR_GEN = DATA_DIR / "media" / "generadas"
_DIR_GEN.mkdir(parents=True, exist_ok=True)

# Modelos canónicos Render (Fal / Replicate)
FAL_IMAGE_MODEL = "fal-ai/flux/dev"
FAL_VIDEO_MODEL = "fal-ai/minimax/video-01"
REPLICATE_IMAGE_MODEL = "black-forest-labs/flux-schnell"


class ServiceManager(ServiceRegistry):
    """Motor principal: una conexión por proveedor, fallback automático."""

    version = "1.0.0-neural"
    modo = "ejecucion"

    def modo_ejecucion(self) -> bool:
        from settings import MODO_EJECUCION

        return bool(MODO_EJECUCION)

    def infraestructura_lista(self) -> dict[str, Any]:
        """Confirmación de despliegue neuronal."""
        st = self.estado()
        sbi = self.sbi_activo()
        llm = self.activo(Servicio.LLM)
        return {
            "ok": bool(llm) and self.modo_ejecucion(),
            "modo": "ejecucion" if self.modo_ejecucion() else "prueba",
            "version": self.version,
            "llm": llm,
            "tts": self.activo(Servicio.TTS),
            "stt": self.activo(Servicio.STT),
            "media": self.activo(Servicio.MEDIA),
            "embeddings": self.activo(Servicio.EMBEDDINGS),
            "sbi": sbi,
            "web_agentes": bool(sbi.get("enabled")) and self.modo_ejecucion(),
            "activo": st.get("activo"),
            "mensaje": (
                "Infraestructura consolidada — Salomón listo para peticiones reales"
                if llm and self.modo_ejecucion()
                else "Falta clave LLM o MODO_EJECUCION=false"
            ),
        }

    # ── Razonamiento (Gemini → Groq → OpenAI) ───────────────────────────────

    def razonar(
        self,
        mensaje: str,
        historial: list[dict] | None = None,
        system_instruction: str = "",
    ) -> str:
        """Única ruta LLM — fallback automático en cognicion.llm."""
        from cognicion.llm import chat_con_historial

        self._ultimo["llm"] = self.activo(Servicio.LLM) or "local"
        return chat_con_historial(
            mensaje,
            historial or [],
            system_instruction or "Eres Salomón AI, asistente de Israel Monta.",
        )

    # ── Voz: habla (ElevenLabs → Cartesia) ──────────────────────────────────

    def hablar(self, texto: str) -> ResultadoTTS:
        """TTS real — sin simulaciones."""
        t = (texto or "").strip()
        if not t:
            return ResultadoTTS(tts_disponible=False, error="texto_vacio", motor="none")

        # 1) ElevenLabs
        slot = seleccionar(Servicio.TTS)
        ultimo_error = ""
        if slot and slot.nombre == "elevenlabs":
            try:
                from settings import ELEVENLABS_VOICE_ID

                # Si falta Voice ID, tts() resuelve Adam vía catálogo ElevenLabs.
                if not (ELEVENLABS_VOICE_ID or "").strip():
                    evento(_log, "tts_voice_id_ausente_usando_resolver")
                audio = self.tts(t)
                self._ultimo["tts"] = "elevenlabs"
                evento(_log, "tts_ok", motor="elevenlabs", bytes=len(audio))
                return ResultadoTTS(
                    audio_base64=base64.b64encode(audio).decode("ascii"),
                    audio_mime="audio/mpeg",
                    tts_disponible=True,
                    motor="elevenlabs",
                )
            except Exception as exc:
                ultimo_error = str(exc) or type(exc).__name__
                evento(
                    _log,
                    "tts_elevenlabs_fail",
                    error=type(exc).__name__,
                    detalle=ultimo_error[:200],
                )

        # 2) Cartesia (respaldo real si hay clave)
        try:
            from cognicion.voz.cartesia_tts import hablar_salomon

            res = hablar_salomon(t)
            if res.tts_disponible:
                self._ultimo["tts"] = "cartesia"
                return res
            if res.error:
                ultimo_error = ultimo_error or str(res.error)
            if slot is None or slot.nombre != "elevenlabs":
                return res
        except Exception as exc:
            ultimo_error = ultimo_error or (str(exc) or type(exc).__name__)
            evento(_log, "tts_cartesia_fail", error=type(exc).__name__)

        return ResultadoTTS(
            tts_disponible=False,
            error=ultimo_error or "tts_sin_proveedor",
            motor="none",
        )

    # ── Voz: escucha (Deepgram) ─────────────────────────────────────────────

    def escuchar(self, audio: bytes, *, mime: str = "audio/wav") -> dict[str, Any]:
        """STT real Deepgram — única ruta servidor."""
        if not audio:
            return {"ok": False, "error": "audio_vacio", "texto": ""}
        try:
            raw = self.stt(audio, mime=mime)
            texto = _extraer_texto_deepgram(raw)
            self._ultimo["stt"] = "deepgram"
            evento(_log, "stt_ok", motor="deepgram", chars=len(texto))
            return {"ok": bool(texto), "texto": texto, "motor": "deepgram", "raw": raw}
        except Exception as exc:
            evento(_log, "stt_fail", error=type(exc).__name__)
            return {"ok": False, "error": type(exc).__name__, "texto": "", "motor": "deepgram"}

    # ── Media (Fal → Replicate) ─────────────────────────────────────────────

    def generar_activo(
        self,
        prompt: str,
        *,
        video: bool = False,
    ) -> dict[str, Any]:
        """Generación real de imagen/video — sin placeholder."""
        p = (prompt or "").strip()
        if not p:
            return {"exito": False, "error": "prompt_vacio"}

        if video:
            try:
                pack = self.media_run(
                    fal_model=FAL_VIDEO_MODEL,
                    fal_args={"prompt": p},
                    replicate_model=None,
                    replicate_input=None,
                )
                return _normalizar_media(pack, tipo="video")
            except Exception as exc:
                return {"exito": False, "error": type(exc).__name__, "motor": "fal/replicate"}

        try:
            pack = self.media_run(
                fal_model=FAL_IMAGE_MODEL,
                fal_args={"prompt": p, "image_size": "landscape_4_3"},
                replicate_model=REPLICATE_IMAGE_MODEL,
                replicate_input={"prompt": p},
            )
            return _normalizar_media(pack, tipo="imagen")
        except Exception as exc:
            evento(_log, "media_fail", error=type(exc).__name__)
            return {
                "exito": False,
                "error": type(exc).__name__,
                "motor": self.activo(Servicio.MEDIA) or "none",
                "aviso": "FAL_KEY / REPLICATE_API_TOKEN requeridas para media real",
            }

    # ── Memoria (Cohere embeddings) ─────────────────────────────────────────

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self.embeddings(texts)

    def cohere_disponible(self) -> bool:
        return self.activo(Servicio.EMBEDDINGS) == "cohere"

    # ── Web → agentes (Tavily / DDG vía ruta única) ──────────────────────────

    def buscar_web(self, consulta: str, *, origen: str = "agente") -> dict[str, Any]:
        """
        Flujo directo web → agentes.
        Autorizado si SBI activo + modo ejecución, o pedido explícito del usuario.
        """
        from config.memory_cortex import pedido_busqueda_explicito, web_agentes_autorizados
        from cognicion.busqueda.agente import responder_con_busqueda

        q = (consulta or "").strip()
        if not q:
            return {"ok": False, "error": "consulta_vacia"}

        if not (
            pedido_busqueda_explicito(q)
            or (origen == "agente" and web_agentes_autorizados())
            or web_agentes_autorizados()
        ):
            return {
                "ok": False,
                "error": "web_no_autorizada",
                "detalle": "Requiere SBI_ENABLED + MODO_EJECUCION o «Busca en la web sobre…»",
            }

        pack = responder_con_busqueda(q)
        self._ultimo["web"] = str(pack.get("motor") or "busqueda")
        evento(_log, "web_ok", motor=self._ultimo["web"], origen=origen)
        return {
            "ok": bool(pack.get("exito")),
            "texto": pack.get("texto") or "",
            "motor": pack.get("motor"),
            "origen": origen,
            "pack": pack,
        }

    def estado(self) -> dict[str, Any]:
        base = super().estado()
        base["modo_ejecucion"] = self.modo_ejecucion()
        base["infraestructura"] = {
            "version": self.version,
            "lista": bool(self.activo(Servicio.LLM)),
        }
        return base


def _extraer_texto_deepgram(raw: dict[str, Any]) -> str:
    try:
        alts = (
            raw.get("results", {})
            .get("channels", [{}])[0]
            .get("alternatives", [{}])
        )
        if alts:
            return (alts[0].get("transcript") or "").strip()
    except Exception:
        pass
    # SDK shapes
    try:
        return str(raw.get("transcript") or raw.get("text") or "").strip()
    except Exception:
        return ""


def _normalizar_media(pack: dict[str, Any], *, tipo: str) -> dict[str, Any]:
    """Convierte salida Fal/Replicate en activo local persistido."""
    provider = pack.get("provider") or "media"
    result = pack.get("result")
    url = _encontrar_url(result)
    if not url:
        return {
            "exito": False,
            "error": "sin_url_en_respuesta",
            "motor": provider,
            "raw": result if isinstance(result, (dict, list, str)) else str(type(result)),
        }

    try:
        import httpx

        r = httpx.get(url, timeout=120.0, follow_redirects=True)
        r.raise_for_status()
        data = r.content
        ext = "mp4" if tipo == "video" else "png"
        if "jpeg" in (r.headers.get("content-type") or "") or url.endswith(".jpg"):
            ext = "jpg"
        elif url.endswith(".webp"):
            ext = "webp"
        elif url.endswith(".mp4"):
            ext = "mp4"
        nombre = f"{provider}_{uuid.uuid4().hex[:12]}.{ext}"
        path = _DIR_GEN / nombre
        path.write_bytes(data)
        return {
            "exito": True,
            "motor": provider,
            "ruta": str(path),
            "url_relativa": f"/media/generadas/{nombre}",
            "imagen_base64": base64.b64encode(data).decode("ascii") if tipo == "imagen" else None,
            "mime": r.headers.get("content-type") or ("video/mp4" if tipo == "video" else "image/png"),
            "url_origen": url,
            "calidad": "pro_ultra",
        }
    except Exception as exc:
        return {
            "exito": True,
            "motor": provider,
            "url_origen": url,
            "aviso": f"descarga_parcial:{type(exc).__name__}",
            "calidad": "pro_ultra",
        }


def _encontrar_url(result: Any) -> str | None:
    if result is None:
        return None
    if isinstance(result, str) and result.startswith("http"):
        return result
    if isinstance(result, list):
        for item in result:
            u = _encontrar_url(item)
            if u:
                return u
        return None
    if isinstance(result, dict):
        for key in ("url", "image_url", "video_url", "output", "images"):
            if key in result:
                u = _encontrar_url(result[key])
                if u:
                    return u
        # fal flux: {"images": [{"url": "..."}]}
        imgs = result.get("images")
        if isinstance(imgs, list) and imgs:
            return _encontrar_url(imgs[0])
    return None


def obtener_manager() -> ServiceManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = ServiceManager()
    return _MANAGER


# Alias de compatibilidad — una sola instancia
def obtener_registry() -> ServiceManager:
    return obtener_manager()
