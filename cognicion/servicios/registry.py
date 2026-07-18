# -*- coding: utf-8 -*-
"""
ServiceRegistry — rota / selecciona proveedor por tarea y entrega el cliente.
"""

from __future__ import annotations

from typing import Any

from config.providers import (
    ProviderConfigError,
    Servicio,
    cadena_nombres,
    seleccionar,
    validar_entorno,
)
from cognicion.registro import evento, obtener_logger
from cognicion.servicios.clientes import (
    ClienteNoDisponible,
    obtener_cliente,
)

_log = obtener_logger("servicios.registry")
_REGISTRY: "ServiceRegistry | None" = None


class ServiceRegistry:
    """Fachada única para Salomón: LLM / media / STT / TTS / embeddings / SBI."""

    def __init__(self) -> None:
        self._ultimo: dict[str, str] = {}

    def validar(self, *, strict: bool | None = None) -> dict[str, Any]:
        return validar_entorno(strict=strict)

    def activo(self, servicio: Servicio | str) -> str | None:
        slot = seleccionar(servicio)
        return slot.nombre if slot else None

    def cliente_para(self, servicio: Servicio | str) -> Any:
        """
        Abre el cliente del primer proveedor disponible en la cadena.
        Si falla el SDK, intenta el siguiente eslabón.
        """
        if isinstance(servicio, str):
            servicio = Servicio(servicio.strip().lower())

        # LLM: reutilizar cognicion.llm (misma rotación gemini→groq→openai)
        if servicio == Servicio.LLM:
            from cognicion.llm import obtener_proveedor

            prov = obtener_proveedor()
            self._ultimo["llm"] = prov.nombre
            # Cliente crudo si hay factory; si no, el propio provider
            try:
                return obtener_cliente(prov.nombre)
            except ClienteNoDisponible:
                return prov

        errores: list[str] = []
        for nombre in cadena_nombres(servicio):
            try:
                client = obtener_cliente(nombre)
                self._ultimo[servicio.value] = nombre
                evento(_log, "proveedor_seleccionado", servicio=servicio.value, nombre=nombre)
                return client
            except Exception as exc:
                errores.append(f"{nombre}: {exc}")
                continue

        raise ClienteNoDisponible(
            f"Ningún proveedor para {servicio.value}. "
            + ("; ".join(errores) if errores else "sin claves")
        )

    def stt(self, audio: bytes, *, mime: str = "audio/wav") -> dict[str, Any]:
        """Voz → texto (Deepgram)."""
        client = self.cliente_para(Servicio.STT)
        if hasattr(client, "transcribe"):
            return client.transcribe(audio, mime=mime)
        # SDK oficial Deepgram — rutas varían por versión; fallback HTTP si falla
        try:
            response = client.listen.v1.media.transcribe_file(request=audio)
            return response.to_dict() if hasattr(response, "to_dict") else {"raw": str(response)}
        except Exception as exc_sdk:
            try:
                from deepgram import PrerecordedOptions

                opts = PrerecordedOptions(model="nova-2", language="es", smart_format=True)
                payload = {"buffer": audio}
                res = client.listen.prerecorded.v("1").transcribe_file(payload, opts)
                return res.to_dict() if hasattr(res, "to_dict") else {"raw": str(res)}
            except Exception:
                from cognicion.servicios.clientes import _DeepgramHttp
                from settings import DEEPGRAM_API_KEY

                evento(_log, "deepgram_sdk_fallback_http", error=type(exc_sdk).__name__)
                return _DeepgramHttp(DEEPGRAM_API_KEY).transcribe(audio, mime=mime)

    def tts(self, texto: str, voice_id: str | None = None) -> bytes:
        """Texto → voz (ElevenLabs; Cartesia no se fuerza aquí)."""
        client = self.cliente_para(Servicio.TTS)
        if hasattr(client, "tts"):
            return client.tts(texto, voice_id=voice_id)
        from settings import ELEVENLABS_MODEL_ID, ELEVENLABS_VOICE_ID

        vid = voice_id or ELEVENLABS_VOICE_ID
        if not vid:
            raise ClienteNoDisponible("ELEVENLABS_VOICE_ID requerida para TTS")
        # SDK elevenlabs
        audio = client.text_to_speech.convert(
            voice_id=vid,
            text=texto,
            model_id=ELEVENLABS_MODEL_ID,
        )
        if isinstance(audio, (bytes, bytearray)):
            return bytes(audio)
        chunks = []
        for chunk in audio:
            if isinstance(chunk, (bytes, bytearray)):
                chunks.append(bytes(chunk))
        return b"".join(chunks)

    def embeddings(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """Embeddings Cohere para RAG."""
        client = self.cliente_para(Servicio.EMBEDDINGS)
        if hasattr(client, "embed") and type(client).__name__ == "_CohereHttp":
            data = client.embed(texts, model=model)
            return data.get("embeddings") or []
        from settings import COHERE_EMBED_MODEL

        try:
            resp = client.embed(
                texts=texts,
                model=model or COHERE_EMBED_MODEL,
                input_type="search_document",
            )
            if hasattr(resp, "embeddings"):
                emb = resp.embeddings
                return list(emb) if not isinstance(emb, list) else emb
            if isinstance(resp, dict):
                return resp.get("embeddings") or []
        except TypeError:
            resp = client.embed(texts=texts, model=model or COHERE_EMBED_MODEL)
            return list(getattr(resp, "embeddings", []) or [])
        return []

    def media_run(
        self,
        *,
        fal_model: str | None = None,
        fal_args: dict[str, Any] | None = None,
        replicate_model: str | None = None,
        replicate_input: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Imagen/video: intenta Fal, luego Replicate."""
        ultimo_error: Exception | None = None
        if fal_model:
            try:
                client = obtener_cliente("fal")
                self._ultimo["media"] = "fal"
                if hasattr(client, "run") and type(client).__name__ == "_FalHttp":
                    return {"provider": "fal", "result": client.run(fal_model, fal_args or {})}
                # fal_client.subscribe / run
                result = client.subscribe(fal_model, arguments=fal_args or {})
                return {"provider": "fal", "result": result}
            except Exception as exc:
                ultimo_error = exc
                evento(_log, "media_fal_fallo", error=type(exc).__name__)

        if replicate_model:
            try:
                client = obtener_cliente("replicate")
                self._ultimo["media"] = "replicate"
                if hasattr(client, "run") and type(client).__name__ == "_ReplicateHttp":
                    out = client.run(replicate_model, replicate_input or {})
                    return {"provider": "replicate", "result": out}
                out = client.run(replicate_model, input=replicate_input or {})
                return {"provider": "replicate", "result": out}
            except Exception as exc:
                ultimo_error = exc
                evento(_log, "media_replicate_fallo", error=type(exc).__name__)

        raise ClienteNoDisponible(
            f"Media no disponible: {ultimo_error or 'sin FAL_KEY/REPLICATE_API_TOKEN'}"
        )

    def sbi_activo(self) -> dict[str, Any]:
        """Flags de agentes biométricos (SBI_ENABLED / SBI_MODE)."""
        import settings as S

        mode = (S.SBI_MODE or "soft").strip().lower()
        enabled = bool(S.SBI_ENABLED) and mode != "off"
        return {
            "enabled": enabled,
            "mode": mode if S.SBI_ENABLED else "off",
            "agents_gated": enabled and mode == "strict",
            "soft_verify": enabled and mode == "soft",
        }

    def estado(self) -> dict[str, Any]:
        base = self.validar(strict=False)
        base["ultimo_seleccionado"] = dict(self._ultimo)
        base["sbi_runtime"] = self.sbi_activo()
        return base


def obtener_registry() -> ServiceRegistry:
    """Compat: delega al ServiceManager (única instancia neuronal)."""
    from cognicion.servicios.manager import obtener_manager

    return obtener_manager()


def boot_proveedores(*, strict: bool | None = None) -> dict[str, Any]:
    """Llamar al startup: valida y registra estado (no tumba Free Tier si strict=False)."""
    from cognicion.servicios.manager import obtener_manager

    reg = obtener_manager()
    try:
        reporte = reg.validar(strict=strict)
    except ProviderConfigError as exc:
        evento(_log, "proveedores_strict_fail", error=str(exc))
        raise
    infra = reg.infraestructura_lista()
    if reporte.get("errores"):
        evento(_log, "proveedores_advertencia", errores=reporte["errores"])
    else:
        evento(
            _log,
            "proveedores_ok",
            activo=reporte.get("activo"),
            sbi=reporte.get("sbi"),
            modo=infra.get("modo"),
        )
    evento(
        _log,
        "despliegue_neuronal",
        ok=infra.get("ok"),
        modo=infra.get("modo"),
        mensaje=infra.get("mensaje"),
    )
    return {**reporte, "infraestructura": infra}
