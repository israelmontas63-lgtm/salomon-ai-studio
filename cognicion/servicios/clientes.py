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


def cliente_deepseek() -> Any:
    """OpenAI-compatible apuntando a DeepSeek (razonamiento / lógica)."""
    from settings import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

    if not DEEPSEEK_API_KEY:
        raise ClienteNoDisponible("DEEPSEEK_API_KEY no configurada")

    def _build():
        from openai import OpenAI

        base = (DEEPSEEK_BASE_URL or "").strip() or "https://api.deepseek.com"
        return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=base)

    return _cache_get("deepseek", _build)


def cliente_openrouter() -> Any:
    from settings import OPENROUTER_API_KEY, OPENROUTER_BASE_URL

    if not OPENROUTER_API_KEY:
        raise ClienteNoDisponible("OPENROUTER_API_KEY no configurada")

    def _build():
        from openai import OpenAI

        base = (OPENROUTER_BASE_URL or "").strip() or "https://openrouter.ai/api/v1"
        return OpenAI(api_key=OPENROUTER_API_KEY, base_url=base)

    return _cache_get("openrouter", _build)


def cliente_cerebras() -> Any:
    from settings import CEREBRAS_API_KEY, CEREBRAS_BASE_URL

    if not CEREBRAS_API_KEY:
        raise ClienteNoDisponible("CEREBRAS_API_KEY no configurada")

    def _build():
        from openai import OpenAI

        base = (CEREBRAS_BASE_URL or "").strip() or "https://api.cerebras.ai/v1"
        return OpenAI(api_key=CEREBRAS_API_KEY, base_url=base)

    return _cache_get("cerebras", _build)


def cliente_mistral() -> Any:
    from settings import MISTRAL_API_KEY, MISTRAL_BASE_URL

    if not MISTRAL_API_KEY:
        raise ClienteNoDisponible("MISTRAL_API_KEY no configurada")

    def _build():
        from openai import OpenAI

        base = (MISTRAL_BASE_URL or "").strip() or "https://api.mistral.ai/v1"
        return OpenAI(api_key=MISTRAL_API_KEY, base_url=base)

    return _cache_get("mistral", _build)


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


# Adam (premade) — case-sensitive; typos en Render suelen romper TTS.
ELEVENLABS_VOICE_ADAM = "pNInz6obpgDQGcFmaJgB"
_VOICE_RESUELTA: str | None = None


def resolver_elevenlabs_voice_id(
    api_key: str, preferida: str | None = None, *, force: bool = False
) -> str:
    """Si el Voice ID de env está mal tipado, corrige mayúsculas o usa Adam."""
    global _VOICE_RESUELTA
    import httpx
    from settings import ELEVENLABS_VOICE_ID

    if _VOICE_RESUELTA and not force:
        return _VOICE_RESUELTA

    candidatas: list[str] = []
    for v in (preferida, ELEVENLABS_VOICE_ID, ELEVENLABS_VOICE_ADAM):
        v = (v or "").strip()
        if v and v not in candidatas:
            candidatas.append(v)

    try:
        r = httpx.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": api_key, "Accept": "application/json"},
            timeout=30.0,
        )
        if r.status_code == 200:
            voces = (r.json() or {}).get("voices") or []
            ids = [str(v.get("voice_id") or "") for v in voces if v.get("voice_id")]
            lower_map = {i.lower(): i for i in ids}
            for c in candidatas:
                if c in ids:
                    _VOICE_RESUELTA = c
                    return c
                if c.lower() in lower_map:
                    _VOICE_RESUELTA = lower_map[c.lower()]
                    _log.info(
                        "elevenlabs_voice_id_corregido de=%s a=%s",
                        c,
                        _VOICE_RESUELTA,
                    )
                    return _VOICE_RESUELTA
            for v in voces:
                nombre = (v.get("name") or "").lower()
                if "adam" in nombre and v.get("voice_id"):
                    _VOICE_RESUELTA = str(v["voice_id"])
                    return _VOICE_RESUELTA
            if ids:
                _VOICE_RESUELTA = ids[0]
                return _VOICE_RESUELTA
    except Exception as exc:
        _log.info("elevenlabs_voices_lookup_fail error=%s", type(exc).__name__)

    if candidatas:
        _VOICE_RESUELTA = candidatas[0]
        return _VOICE_RESUELTA
    raise ClienteNoDisponible("ELEVENLABS_VOICE_ID no configurada")


class _ElevenLabsHttp:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def tts(self, texto: str, voice_id: str | None = None) -> bytes:
        import httpx
        from settings import ELEVENLABS_MODEL_ID

        vid = resolver_elevenlabs_voice_id(self.api_key, voice_id)
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
            vid = resolver_elevenlabs_voice_id(self.api_key, None, force=True)
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
        import time

        import httpx

        # Fal autentica con "Key <id:secret>" — nunca Bearer (provoca 401).
        headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }
        # Payload limpio: el modelo vive en la URL, no en el body.
        args = dict(arguments or {})
        args.pop("model", None)
        args.pop("quality", None)
        url = f"https://fal.run/{model_id.lstrip('/')}"
        last_exc: Exception | None = None
        for attempt, delay in enumerate((0.0, 1.2, 2.8, 6.0)):
            if delay:
                time.sleep(delay)
            try:
                r = httpx.post(url, headers=headers, json=args, timeout=180.0)
                if r.status_code in (429, 500, 502, 503, 504):
                    last_exc = httpx.HTTPStatusError(
                        f"fal_http_{r.status_code}",
                        request=r.request,
                        response=r,
                    )
                    continue
                if r.status_code >= 400:
                    # Propagar cuerpo (saldo/auth) para clasificar Error 23/44, no 49
                    detail = (r.text or "")[:400]
                    raise httpx.HTTPStatusError(
                        f"fal_http_{r.status_code}:{detail}",
                        request=r.request,
                        response=r,
                    )
                return r.json()
            except httpx.HTTPStatusError:
                raise
            except Exception as exc:
                last_exc = exc
                if attempt >= 3:
                    break
        if last_exc:
            raise last_exc
        raise RuntimeError("fal_sin_respuesta")


class _ReplicateHttp:
    def __init__(self, api_token: str) -> None:
        self.api_token = api_token

    def run(self, model: str, input_data: dict[str, Any]) -> Any:
        import time

        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Prefer": "wait",
        }
        # Preferir endpoint owner/name (modelos tipo black-forest-labs/flux-schnell)
        model_path = (model or "").strip().lstrip("/")
        if ":" in model_path and "/" not in model_path.split(":", 1)[0]:
            # version hash legado
            endpoints = [
                (
                    "https://api.replicate.com/v1/predictions",
                    {"version": model_path, "input": input_data or {}},
                )
            ]
        else:
            owner_name = model_path.split(":")[0]
            endpoints = [
                (
                    f"https://api.replicate.com/v1/models/{owner_name}/predictions",
                    {"input": input_data or {}},
                ),
                (
                    "https://api.replicate.com/v1/predictions",
                    {"version": model_path, "input": input_data or {}},
                ),
            ]

        last_err: Exception | None = None
        for url, payload in endpoints:
            for delay in (0.0, 1.5, 3.5):
                if delay:
                    time.sleep(delay)
                try:
                    r = httpx.post(url, headers=headers, json=payload, timeout=180.0)
                    if r.status_code in (429, 500, 502, 503, 504):
                        last_err = httpx.HTTPStatusError(
                            f"replicate_http_{r.status_code}",
                            request=r.request,
                            response=r,
                        )
                        continue
                    if r.status_code >= 400:
                        detail = (r.text or "")[:400]
                        raise httpx.HTTPStatusError(
                            f"replicate_http_{r.status_code}:{detail}",
                            request=r.request,
                            response=r,
                        )
                    data = r.json()
                    for _ in range(40):
                        if data.get("status") in ("succeeded", "failed", "canceled"):
                            break
                        get_url = (data.get("urls") or {}).get("get")
                        if not get_url:
                            break
                        time.sleep(1.0)
                        data = httpx.get(
                            get_url,
                            headers={"Authorization": f"Bearer {self.api_token}"},
                            timeout=60.0,
                        ).json()
                    if data.get("status") == "failed":
                        raise RuntimeError(
                            f"replicate_failed:{data.get('error') or data}"
                        )
                    return data.get("output", data)
                except httpx.HTTPStatusError as exc:
                    # 402/401/403: no reintentar en bucle
                    code = getattr(exc.response, "status_code", 0) or 0
                    if code in (401, 402, 403, 404, 422):
                        raise
                    last_err = exc
                except Exception as exc:
                    last_err = exc
        if last_err:
            raise last_err
        raise RuntimeError("replicate_sin_respuesta")


FACTORY: dict[str, Callable[[], Any]] = {
    "gemini": cliente_gemini,
    "deepseek": cliente_deepseek,
    "openrouter": cliente_openrouter,
    "cerebras": cliente_cerebras,
    "mistral": cliente_mistral,
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
