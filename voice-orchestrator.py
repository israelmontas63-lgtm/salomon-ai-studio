"""
Orquestador de voz — puente activo hacia el TTS de Salomón (ElevenLabs).
Mantiene el flujo de salida de audio operativo y verificable.
"""

from __future__ import annotations

from typing import Any

from cerebro import ResultadoTTS, texto_a_voz
from settings import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, TTS_ASYNC


def voz_configurada() -> bool:
    return bool((ELEVENLABS_API_KEY or "").strip() and (ELEVENLABS_VOICE_ID or "").strip())


def emitir_voz(texto: str) -> ResultadoTTS:
    """Genera audio MPEG a partir de texto. No tumba el chat si falla."""
    t = (texto or "").strip()
    if not t:
        return ResultadoTTS(tts_disponible=False, error="texto_vacio")
    if TTS_ASYNC:
        # El cliente (bridge) debe completar con /api/tts
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
        "version": "1.3",
        "flujo_salida_activo": True,
        "elevenlabs_key": bool((ELEVENLABS_API_KEY or "").strip()),
        "elevenlabs_voice": bool((ELEVENLABS_VOICE_ID or "").strip()),
        "tts_async": TTS_ASYNC,
        "audio_mime_default": "audio/mpeg",
    }


if __name__ == "__main__":
    import json

    print(json.dumps(estado_voz(), ensure_ascii=False, indent=2))
