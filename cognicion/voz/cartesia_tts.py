# -*- coding: utf-8 -*-
"""
Cartesia Sonic-3.5 — TTS de baja latencia (WebSocket).

Claves solo desde entorno: CARTESIA_API_KEY, CARTESIA_VOICE_ID.
Fallos de red/servicio → resultado suave (no tumba el núcleo).
"""

from __future__ import annotations

import array
import base64
import io
import os
import threading
import wave
from dataclasses import dataclass
from typing import Any

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


CARTESIA_MODEL_ID = _env("CARTESIA_MODEL_ID", "sonic-3.5") or "sonic-3.5"
CARTESIA_SAMPLE_RATE = int(_env("CARTESIA_SAMPLE_RATE", "44100") or "44100")
CARTESIA_LANGUAGE = _env("CARTESIA_LANGUAGE", "es") or "es"


@dataclass
class ResultadoTTS:
    audio_base64: str | None = None
    audio_mime: str = "audio/wav"
    tts_disponible: bool = False
    error: str | None = None
    motor: str = "cartesia-sonic-3.5"

    def to_dict(self) -> dict[str, Any]:
        return {
            "audio_base64": self.audio_base64,
            "audio_mime": self.audio_mime,
            "tts_disponible": self.tts_disponible,
            "error": self.error,
            "motor": self.motor,
        }


def _api_key() -> str:
    return _env("CARTESIA_API_KEY")


def _voice_id() -> str:
    return _env("CARTESIA_VOICE_ID")


def _cliente():
    """Cliente lazy — nunca loguea la API key."""
    global _client
    key = _api_key()
    if not key:
        return None
    if _client is None:
        from cartesia import Cartesia

        _client = Cartesia(api_key=key)
    return _client


def _pcm_f32le_a_wav(pcm: bytes, sample_rate: int = 44100) -> bytes:
    """Convierte PCM float32 LE → WAV PCM s16le (reproducible en navegador)."""
    if not pcm:
        return b""
    floats = array.array("f")
    floats.frombytes(pcm)
    if floats.itemsize * len(floats) != len(pcm):
        # padding residual
        usable = (len(pcm) // 4) * 4
        floats = array.array("f")
        floats.frombytes(pcm[:usable])
    samples = array.array("h")
    for f in floats:
        v = max(-1.0, min(1.0, float(f)))
        samples.append(int(v * 32767.0))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples.tobytes())
    return buf.getvalue()


def _sintetizar_websocket(texto: str) -> ResultadoTTS:
    client = _cliente()
    voice = _voice_id()
    if client is None:
        return ResultadoTTS(tts_disponible=False, error="cartesia_api_key_faltante")
    if not voice:
        return ResultadoTTS(tts_disponible=False, error="cartesia_voice_id_faltante")

    chunks: list[bytes] = []
    try:
        with client.tts.websocket_connect() as connection:
            ctx_kwargs: dict[str, Any] = {
                "model_id": CARTESIA_MODEL_ID,
                "voice": {"mode": "id", "id": voice},
                "output_format": {
                    "container": "raw",
                    "encoding": "pcm_f32le",
                    "sample_rate": CARTESIA_SAMPLE_RATE,
                },
            }
            # Idioma si el SDK lo acepta
            try:
                ctx = connection.context(**ctx_kwargs, language=CARTESIA_LANGUAGE)
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
                        # algunos SDKs entregan base64
                        try:
                            chunks.append(base64.b64decode(audio))
                        except Exception:
                            pass
                elif rtype == "done":
                    break
    except Exception as exc:
        # Silencioso para el usuario final: no tumba el chat
        return ResultadoTTS(
            tts_disponible=False,
            error=f"cartesia_ws_{type(exc).__name__}",
        )

    pcm = b"".join(chunks)
    if not pcm:
        return ResultadoTTS(tts_disponible=False, error="cartesia_audio_vacio")

    try:
        wav = _pcm_f32le_a_wav(pcm, CARTESIA_SAMPLE_RATE)
    except Exception as exc:
        return ResultadoTTS(
            tts_disponible=False,
            error=f"cartesia_wav_{type(exc).__name__}",
        )

    if not wav:
        return ResultadoTTS(tts_disponible=False, error="cartesia_wav_vacio")

    return ResultadoTTS(
        audio_base64=base64.b64encode(wav).decode("ascii"),
        audio_mime="audio/wav",
        tts_disponible=True,
    )


def _sintetizar_bytes_fallback(texto: str) -> ResultadoTTS:
    """Respaldo REST/bytes si el WebSocket falla momentáneamente."""
    client = _cliente()
    voice = _voice_id()
    if client is None or not voice:
        return ResultadoTTS(tts_disponible=False, error="cartesia_no_configurado")
    try:
        # API v3: generate → bytes/iter
        gen = getattr(client.tts, "bytes", None) or getattr(client.tts, "generate", None)
        if gen is None:
            return ResultadoTTS(tts_disponible=False, error="cartesia_sdk_sin_generate")
        kwargs = {
            "model_id": CARTESIA_MODEL_ID,
            "transcript": texto,
            "voice": {"mode": "id", "id": voice},
            "output_format": {
                "container": "wav",
                "encoding": "pcm_s16le",
                "sample_rate": CARTESIA_SAMPLE_RATE,
            },
        }
        try:
            out = gen(**kwargs, language=CARTESIA_LANGUAGE)
        except TypeError:
            out = gen(**kwargs)

        audio = b""
        if isinstance(out, (bytes, bytearray)):
            audio = bytes(out)
        elif hasattr(out, "audio") and out.audio:
            audio = bytes(out.audio) if isinstance(out.audio, (bytes, bytearray)) else b""
        else:
            # iterable de chunks
            try:
                parts = []
                for part in out:
                    if isinstance(part, (bytes, bytearray)):
                        parts.append(bytes(part))
                    elif hasattr(part, "audio") and part.audio:
                        parts.append(bytes(part.audio))
                audio = b"".join(parts)
            except TypeError:
                audio = b""

        if not audio:
            return ResultadoTTS(tts_disponible=False, error="cartesia_fallback_vacio")
        return ResultadoTTS(
            audio_base64=base64.b64encode(audio).decode("ascii"),
            audio_mime="audio/wav",
            tts_disponible=True,
        )
    except Exception as exc:
        return ResultadoTTS(
            tts_disponible=False,
            error=f"cartesia_fallback_{type(exc).__name__}",
        )


def hablar_salomon(texto: str) -> ResultadoTTS:
    """
    Flujo de audio de alta fidelidad (Sonic-3.5 WebSocket).
    Compatible con la firma pedida en el protocolo de migración.
    """
    contenido = (texto or "").strip()
    if not contenido:
        return ResultadoTTS(tts_disponible=False, error="texto_vacio")

    # Límite seguro para un turno de chat
    if len(contenido) > 4500:
        contenido = contenido[:4500]

    with _tts_lock:
        res = _sintetizar_websocket(contenido)
        if res.tts_disponible and res.audio_base64:
            return res
        # Caída momentánea del WS → intento bytes sin romper el sistema
        fb = _sintetizar_bytes_fallback(contenido)
        if fb.tts_disponible:
            fb.error = res.error  # conserva causa WS para telemetría
            return fb
        # Ambos fallaron: soft-fail
        return ResultadoTTS(
            tts_disponible=False,
            error=res.error or fb.error or "cartesia_indisponible",
        )


def texto_a_voz_cartesia(texto: str) -> ResultadoTTS:
    """Alias estable para cerebro / API."""
    return hablar_salomon(texto)


def cartesia_configurado() -> bool:
    return bool(_api_key() and _voice_id())
