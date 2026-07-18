"""
Orquestador de voz — puente activo hacia Cartesia Sonic-3.5.
Mantiene el flujo de salida de audio operativo y verificable.
"""

from __future__ import annotations

from typing import Any

from cerebro import ResultadoTTS, texto_a_voz
from cognicion.voz.cartesia_tts import cartesia_configurado
from settings import CARTESIA_API_KEY, CARTESIA_MODEL_ID, CARTESIA_VOICE_ID, TTS_ASYNC


def voz_configurada() -> bool:
    return cartesia_configurado()


def emitir_voz(texto: str) -> ResultadoTTS:
    """Genera audio WAV a partir de texto. No tumba el chat si falla."""
    t = (texto or "").strip()
    if not t:
        return ResultadoTTS(tts_disponible=False, error="texto_vacio")
    if TTS_ASYNC:
        return ResultadoTTS(tts_disponible=False, error="tts_async_pendiente")
    try:
        return texto_a_voz(t)
    except Exception as exc:
        return ResultadoTTS(
            tts_disponible=False,
            error=f"voz_{type(exc).__name__}",
        )


def estado_voz() -> dict[str, Any]:
    return {
        "modulo": "voice-orchestrator",
        "version": "3.5",
        "flujo_salida_activo": True,
        "motor": "cartesia-sonic-3.5",
        "modelo": CARTESIA_MODEL_ID,
        "cartesia_key": bool((CARTESIA_API_KEY or "").strip()),
        "cartesia_voice": bool((CARTESIA_VOICE_ID or "").strip()),
        "tts_async": TTS_ASYNC,
        "audio_mime_default": "audio/wav",
    }


if __name__ == "__main__":
    import json

    print(json.dumps(estado_voz(), ensure_ascii=False, indent=2))
