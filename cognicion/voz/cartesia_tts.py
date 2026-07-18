# -*- coding: utf-8 -*-
"""
Cartesia Sonic-3.5 — TTS de baja latencia (WebSocket).

Lazy-load: el SDK `cartesia` NO se importa al boot.
Tras cada síntesis se liberan cliente, buffers y se fuerza GC (Free Tier 512MB).
Calidad: model_id sonic-3.5, salida WAV HD 44.1 kHz.
"""

from __future__ import annotations

import array
import base64
import gc
import io
import os
import threading
import wave
from typing import Any

from cognicion.voz.tipos import ResultadoTTS

_tts_lock = threading.Lock()
_client = None


def _env(name: str, default: str = "") -> str:
    try:
        from settings import CARTESIA_API_KEY as _K
        from settings import CARTESIA_LANGUAGE as _L
        from settings import CARTESIA_MODEL_ID as _M
        from settings import CARTESIA_SAMPLE_RATE as _S
        from settings import CARTESIA_VOICE_ID as _V

        mapping = {
            "CARTESIA_API_KEY": _K,
            "CARTESIA_VOICE_ID": _V,
            "CARTESIA_MODEL_ID": _M,
            "CARTESIA_LANGUAGE": _L,
            "CARTESIA_SAMPLE_RATE": str(_S),
        }
        if name in mapping and mapping[name]:
            return str(mapping[name]).strip()
    except Exception:
        pass
    return (os.environ.get(name) or default).strip()


def _modelo() -> str:
    return _env("CARTESIA_MODEL_ID", "sonic-3.5") or "sonic-3.5"


def _sample_rate() -> int:
    return int(_env("CARTESIA_SAMPLE_RATE", "44100") or "44100")


def _language() -> str:
    return _env("CARTESIA_LANGUAGE", "es") or "es"


# Compat: nombres usados por telemetría / validate (sin forzar SDK)
CARTESIA_MODEL_ID = "sonic-3.5"
CARTESIA_SAMPLE_RATE = 44100
CARTESIA_LANGUAGE = "es"


def _api_key() -> str:
    return _env("CARTESIA_API_KEY")


def _voice_id() -> str:
    return _env("CARTESIA_VOICE_ID")


def _cliente():
    """Cliente lazy — solo en la primera síntesis del turno."""
    global _client
    key = _api_key()
    if not key:
        return None
    if _client is None:
        from cartesia import Cartesia  # import diferido (no al boot)

        _client = Cartesia(api_key=key)
    return _client


def _liberar_recursos(*buffers: Any) -> None:
    """Suelta cliente Cartesia + buffers grandes y pide GC (pasivo)."""
    global _client
    _client = None
    for buf in buffers:
        try:
            del buf
        except Exception:
            pass
    try:
        gc.collect()
    except Exception:
        pass


def _pcm_f32le_a_wav(pcm: bytes, sample_rate: int = 44100) -> bytes:
    """Convierte PCM float32 LE → WAV PCM s16le (reproducible en navegador)."""
    if not pcm:
        return b""
    usable = (len(pcm) // 4) * 4
    floats = array.array("f")
    floats.frombytes(pcm[:usable])
    # Liberar referencia al pcm crudo lo antes posible en el caller
    samples = array.array("h", (0 for _ in range(len(floats))))
    for i, f in enumerate(floats):
        v = max(-1.0, min(1.0, float(f)))
        samples[i] = int(v * 32767.0)
    del floats
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples.tobytes())
    del samples
    return buf.getvalue()


def _sintetizar_websocket(texto: str) -> ResultadoTTS:
    client = _cliente()
    voice = _voice_id()
    if client is None:
        return ResultadoTTS(tts_disponible=False, error="cartesia_api_key_faltante")
    if not voice:
        return ResultadoTTS(tts_disponible=False, error="cartesia_voice_id_faltante")

    model_id = _modelo()
    rate = _sample_rate()
    lang = _language()
    chunks: list[bytes] = []
    try:
        with client.tts.websocket_connect() as connection:
            ctx_kwargs: dict[str, Any] = {
                "model_id": model_id,
                "voice": {"mode": "id", "id": voice},
                "output_format": {
                    "container": "raw",
                    "encoding": "pcm_f32le",
                    "sample_rate": rate,
                },
            }
            try:
                ctx = connection.context(**ctx_kwargs, language=lang)
            except TypeError:
                ctx = connection.context(**ctx_kwargs)

            ctx.push(texto)
            ctx.no_more_inputs()

            for response in ctx.receive():
                rtype = getattr(response, "type", None)
                audio = getattr(response, "audio", None)
                if rtype == "chunk" and audio:
                    if isinstance(audio, (bytes, bytearray)):
                        chunks.append(bytes(audio))
                    else:
                        try:
                            chunks.append(base64.b64decode(audio))
                        except Exception:
                            pass
                elif rtype == "done":
                    break
    except Exception as exc:
        chunks.clear()
        return ResultadoTTS(
            tts_disponible=False,
            error=f"cartesia_ws_{type(exc).__name__}",
        )

    pcm = b"".join(chunks)
    chunks.clear()
    del chunks
    if not pcm:
        return ResultadoTTS(tts_disponible=False, error="cartesia_audio_vacio")

    try:
        wav = _pcm_f32le_a_wav(pcm, rate)
    except Exception as exc:
        del pcm
        return ResultadoTTS(
            tts_disponible=False,
            error=f"cartesia_wav_{type(exc).__name__}",
        )
    finally:
        try:
            del pcm
        except Exception:
            pass

    if not wav:
        return ResultadoTTS(tts_disponible=False, error="cartesia_wav_vacio")

    b64 = base64.b64encode(wav).decode("ascii")
    del wav
    return ResultadoTTS(
        audio_base64=b64,
        audio_mime="audio/wav",
        tts_disponible=True,
        motor=f"cartesia-{model_id}",
    )


def _sintetizar_bytes_fallback(texto: str) -> ResultadoTTS:
    """Respaldo REST/bytes si el WebSocket falla momentáneamente."""
    client = _cliente()
    voice = _voice_id()
    if client is None or not voice:
        return ResultadoTTS(tts_disponible=False, error="cartesia_no_configurado")
    model_id = _modelo()
    rate = _sample_rate()
    lang = _language()
    try:
        gen = getattr(client.tts, "bytes", None) or getattr(client.tts, "generate", None)
        if gen is None:
            return ResultadoTTS(tts_disponible=False, error="cartesia_sdk_sin_generate")
        kwargs = {
            "model_id": model_id,
            "transcript": texto,
            "voice": {"mode": "id", "id": voice},
            "output_format": {
                "container": "wav",
                "encoding": "pcm_s16le",
                "sample_rate": rate,
            },
        }
        try:
            out = gen(**kwargs, language=lang)
        except TypeError:
            out = gen(**kwargs)

        audio = b""
        if isinstance(out, (bytes, bytearray)):
            audio = bytes(out)
        elif hasattr(out, "audio") and out.audio:
            audio = bytes(out.audio) if isinstance(out.audio, (bytes, bytearray)) else b""
        else:
            try:
                parts: list[bytes] = []
                for part in out:
                    if isinstance(part, (bytes, bytearray)):
                        parts.append(bytes(part))
                    elif hasattr(part, "audio") and part.audio:
                        parts.append(bytes(part.audio))
                audio = b"".join(parts)
                parts.clear()
            except TypeError:
                audio = b""

        if not audio:
            return ResultadoTTS(tts_disponible=False, error="cartesia_fallback_vacio")
        b64 = base64.b64encode(audio).decode("ascii")
        del audio
        return ResultadoTTS(
            audio_base64=b64,
            audio_mime="audio/wav",
            tts_disponible=True,
            motor=f"cartesia-{model_id}",
        )
    except Exception as exc:
        return ResultadoTTS(
            tts_disponible=False,
            error=f"cartesia_fallback_{type(exc).__name__}",
        )


def hablar_salomon(texto: str) -> ResultadoTTS:
    """
    Flujo de audio de alta fidelidad (Sonic-3.5 WebSocket).
    SDK + cliente solo bajo demanda; libera RAM al terminar el turno.
    """
    contenido = (texto or "").strip()
    if not contenido:
        return ResultadoTTS(tts_disponible=False, error="texto_vacio")

    if len(contenido) > 4500:
        contenido = contenido[:4500]

    with _tts_lock:
        try:
            res = _sintetizar_websocket(contenido)
            if res.tts_disponible and res.audio_base64:
                return res
            fb = _sintetizar_bytes_fallback(contenido)
            if fb.tts_disponible:
                fb.error = res.error
                return fb
            return ResultadoTTS(
                tts_disponible=False,
                error=res.error or fb.error or "cartesia_indisponible",
            )
        finally:
            # Siempre soltar cliente/buffers tras el turno (wake Free Tier)
            _liberar_recursos()


def texto_a_voz_cartesia(texto: str) -> ResultadoTTS:
    """Alias estable para cerebro / API."""
    return hablar_salomon(texto)


def cartesia_configurado() -> bool:
    return bool(_api_key() and _voice_id())
