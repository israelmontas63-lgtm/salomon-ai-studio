# -*- coding: utf-8 -*-
"""
Inicialización lazy de clientes oficiales / HTTP por proveedor.

No se instancian al import: cada factory abre el cliente solo si hay API key
y (cuando aplica) el SDK está instalado. Fallbacks HTTP vía httpx.
"""

from __future__ import annotations

from typing import Any, Callable

from cognicion.registro import obtener_logger

_log = obtener_logger("servicios.clientes")
_cache: dict[str, Any] = {}


class ClienteNoDisponible(RuntimeError):
    """SDK o API key ausente para el proveedor pedido."""


def _cache_get(clave: str, factory: Callable[[], Any]) -> Any:
    if clave not in _cache:
        _cache[clave] = factory()
    return _cache[clave]


def cliente_gemini() -> Any:
    """google.genai.Client — LLM primario."""
    from settings import GEMINI_API_KEY

    if not GEMINI_API_KEY:
        raise ClienteNoDisponible("GEMINI_API_KEY no configurada")

    def _build():
        from google import genai

        return genai.Client(api_key=GEMINI_API_KEY)

    return _cache_get("gemini", _build)


def cliente_openai() -> Any:
    """openai.OpenAI — LLM / respaldo."""
    from settings import OPENAI_API_KEY, OPENAI_BASE_URL

    if not OPENAI_API_KEY:
        raise ClienteNoDisponible("OPENAI_API_KEY no configurada")

    def _build():
        from openai import OpenAI

        kwargs: dict[str, str] = {"api_key": OPENAI_API_KEY}
        if OPENAI_BASE_URL:
            kwargs["base_url"] = OPENAI_BASE_URL
        return OpenAI(**kwargs)

    return _cache_get("openai", _build)


def cliente_groq() -> Any:
    """OpenAI-compatible apuntando a Groq."""
    from settings import GROQ_API_KEY

    if not GROQ_API_KEY:
        raise ClienteNoDisponible("GROQ_API_KEY no configurada")

    def _build():
        from openai import OpenAI

        return OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )

    return _cache_get("groq", _build)


def cliente_cohere() -> Any:
    """cohere.ClientV2 o wrapper httpx — embeddings / RAG."""
    from settings import COHERE_API_KEY

    if not COHERE_API_KEY:
        raise ClienteNoDisponible("COHERE_API_KEY no configurada")

    def _build():
        try:
            import cohere

            if hasattr(cohere, "ClientV2"):
                return cohere.ClientV2(api_key=COHERE_API_KEY)
            return cohere.Client(api_key=COHERE_API_KEY)
        except ImportError:
            _log.info("cohere SDK ausente — usando wrapper HTTP")
            return _CohereHttp(COHERE_API_KEY)

    return _cache_get("cohere", _build)


def cliente_deepgram() -> Any:
    """Deepgram SDK o wrapper HTTP — STT."""
    from settings import DEEPGRAM_API_KEY

    if not DEEPGRAM_API_KEY:
        raise ClienteNoDisponible("DEEPGRAM_API_KEY no configurada")

    def _build():
        try:
            from deepgram import DeepgramClient

            return DeepgramClient(DEEPGRAM_API_KEY)
        except ImportError:
            _log.info("deepgram-sdk ausente — usando wrapper HTTP")
            return _DeepgramHttp(DEEPGRAM_API_KEY)

    return _cache_get("deepgram", _build)


def cliente_elevenlabs() -> Any:
    """ElevenLabs SDK o wrapper HTTP — TTS."""
    from settings import ELEVENLABS_API_KEY

    if not ELEVENLABS_API_KEY:
        raise ClienteNoDisponible("ELEVENLABS_API_KEY no configurada")

    def _build():
        try:
            from elevenlabs.client import ElevenLabs

            return ElevenLabs(api_key=ELEVENLABS_API_KEY)
        except ImportError:
            try:
                from elevenlabs import ElevenLabs

                return ElevenLabs(api_key=ELEVENLABS_API_KEY)
            except ImportError:
                _log.info("elevenlabs SDK ausente — usando wrapper HTTP")
                return _ElevenLabsHttp(ELEVENLABS_API_KEY)

    return _cache_get("elevenlabs", _build)


def cliente_fal() -> Any:
    """fal_client configurado con FAL_KEY — imagen/video."""
    import os

    from settings import FAL_KEY

    if not FAL_KEY:
        raise ClienteNoDisponible("FAL_KEY no configurada")

    def _build():
        os.environ.setdefault("FAL_KEY", FAL_KEY)
        try:
            import fal_client

            return fal_client
        except ImportError:
            _log.info("fal-client ausente — usando wrapper HTTP")
            return _FalHttp(FAL_KEY)

    return _cache_get("fal", _build)


def cliente_replicate() -> Any:
    """replicate Client — imagen/video respaldo."""
    import os

    from settings import REPLICATE_API_TOKEN

    if not REPLICATE_API_TOKEN:
        raise ClienteNoDisponible("REPLICATE_API_TOKEN no configurada")

    def _build():
        os.environ.setdefault("REPLICATE_API_TOKEN", REPLICATE_API_TOKEN)
        try:
            import replicate

            return replicate.Client(api_token=REPLICATE_API_TOKEN)
        except ImportError:
            _log.info("replicate SDK ausente — usando wrapper HTTP")
            return _ReplicateHttp(REPLICATE_API_TOKEN)

    return _cache_get("replicate", _build)


# ── Wrappers HTTP mínimos (sin SDK) ─────────────────────────────────────────


class _CohereHttp:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def embed(self, texts: list[str], model: str | None = None) -> dict[str, Any]:
        import httpx
        from settings import COHERE_EMBED_MODEL

        r = httpx.post(
            "https://api.cohere.com/v1/embed",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "texts": texts,
                "model": model or COHERE_EMBED_MODEL,
                "input_type": "search_document",
            },
            timeout=60.0,
        )
        r.raise_for_status()
        return r.json()


class _DeepgramHttp:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def transcribe(self, audio: bytes, *, mime: str = "audio/wav") -> dict[str, Any]:
        import httpx
        from settings import DEEPGRAM_LANGUAGE, DEEPGRAM_MODEL

        r = httpx.post(
            f"https://api.deepgram.com/v1/listen?model={DEEPGRAM_MODEL}"
            f"&language={DEEPGRAM_LANGUAGE}&smart_format=true",
            headers={
                "Authorization": f"Token {self.api_key}",
                "Content-Type": mime,
            },
            content=audio,
            timeout=120.0,
        )
        r.raise_for_status()
        return r.json()


class _ElevenLabsHttp:
    # Adam (premade) — case-sensitive; typos en Render suelen romper TTS.
    VOICE_ADAM = "pNInz6obpgDQGcFmaJgB"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._voice_resuelta: str | None = None

    def _resolver_voice_id(self, preferida: str | None = None) -> str:
        """Si el Voice ID de env está mal tipado, usa Adam o la 1ª voz de la cuenta."""
        import httpx
        from settings import ELEVENLABS_VOICE_ID

        if self._voice_resuelta:
            return self._voice_resuelta

        candidatas: list[str] = []
        for v in (preferida, ELEVENLABS_VOICE_ID, self.VOICE_ADAM):
            v = (v or "").strip()
            if v and v not in candidatas:
                candidatas.append(v)

        # Corregir solo mayúsculas/minúsculas frente al catálogo de la cuenta
        try:
            r = httpx.get(
                "https://api.elevenlabs.io/v1/voices",
                headers={"xi-api-key": self.api_key, "Accept": "application/json"},
                timeout=30.0,
            )
            if r.status_code == 200:
                voces = (r.json() or {}).get("voices") or []
                ids = [str(v.get("voice_id") or "") for v in voces if v.get("voice_id")]
                lower_map = {i.lower(): i for i in ids}
                for c in candidatas:
                    if c in ids:
                        self._voice_resuelta = c
                        return c
                    if c.lower() in lower_map:
                        self._voice_resuelta = lower_map[c.lower()]
                        _log.info(
                            "elevenlabs_voice_id_corregido de=%s a=%s",
                            c,
                            self._voice_resuelta,
                        )
                        return self._voice_resuelta
                # Adam por nombre
                for v in voces:
                    nombre = (v.get("name") or "").lower()
                    if "adam" in nombre and v.get("voice_id"):
                        self._voice_resuelta = str(v["voice_id"])
                        return self._voice_resuelta
                if ids:
                    self._voice_resuelta = ids[0]
                    return self._voice_resuelta
        except Exception as exc:
            _log.info("elevenlabs_voices_lookup_fail error=%s", type(exc).__name__)

        if candidatas:
            self._voice_resuelta = candidatas[0]
            return self._voice_resuelta
        raise ClienteNoDisponible("ELEVENLABS_VOICE_ID no configurada")

    def tts(self, texto: str, voice_id: str | None = None) -> bytes:
        import httpx
        from settings import ELEVENLABS_MODEL_ID

        vid = self._resolver_voice_id(voice_id)
        r = httpx.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
            headers={
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json={
                "text": texto,
                "model_id": ELEVENLABS_MODEL_ID,
            },
            timeout=90.0,
        )
        if r.status_code == 404:
            # Invalidar caché y reintentar con catálogo vivo
            self._voice_resuelta = None
            vid = self._resolver_voice_id(None)
            r = httpx.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={
                    "text": texto,
                    "model_id": ELEVENLABS_MODEL_ID,
                },
                timeout=90.0,
            )
        r.raise_for_status()
        return r.content


class _FalHttp:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def run(self, model_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        import httpx

        r = httpx.post(
            f"https://fal.run/{model_id}",
            headers={
                "Authorization": f"Key {self.api_key}",
                "Content-Type": "application/json",
            },
            json=arguments,
            timeout=180.0,
        )
        r.raise_for_status()
        return r.json()


class _ReplicateHttp:
    def __init__(self, api_token: str) -> None:
        self.api_token = api_token

    def run(self, model: str, input_data: dict[str, Any]) -> Any:
        import httpx
        import time

        r = httpx.post(
            "https://api.replicate.com/v1/predictions",
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "Prefer": "wait",
            },
            json={"version": model, "input": input_data},
            timeout=180.0,
        )
        if r.status_code >= 400:
            # Algunos modelos usan owner/name en vez de version hash
            r = httpx.post(
                "https://api.replicate.com/v1/models/"
                + model.replace(":", "/predictions").split("/predictions")[0]
                + "/predictions",
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json",
                    "Prefer": "wait",
                },
                json={"input": input_data},
                timeout=180.0,
            )
        r.raise_for_status()
        data = r.json()
        # Prefer: wait puede devolver completed; si no, poll breve
        for _ in range(30):
            if data.get("status") in ("succeeded", "failed", "canceled"):
                break
            url = data.get("urls", {}).get("get")
            if not url:
                break
            time.sleep(1.0)
            data = httpx.get(
                url,
                headers={"Authorization": f"Bearer {self.api_token}"},
                timeout=60.0,
            ).json()
        return data.get("output", data)


FACTORY: dict[str, Callable[[], Any]] = {
    "gemini": cliente_gemini,
    "openai": cliente_openai,
    "groq": cliente_groq,
    "cohere": cliente_cohere,
    "deepgram": cliente_deepgram,
    "elevenlabs": cliente_elevenlabs,
    "fal": cliente_fal,
    "replicate": cliente_replicate,
}


def obtener_cliente(nombre: str) -> Any:
    factory = FACTORY.get((nombre or "").strip().lower())
    if not factory:
        raise ClienteNoDisponible(f"Proveedor desconocido: {nombre}")
    return factory()


def limpiar_cache_clientes() -> None:
    _cache.clear()
