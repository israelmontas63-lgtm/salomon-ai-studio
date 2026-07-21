"""
Acción hablar — fachada TTS unificada para mente/PWA.

Delega en cerebro.texto_a_voz → ServiceManager.hablar
(ElevenLabs → Cartesia; misma cadena que /api/tts).
"""

from __future__ import annotations

from typing import Any

from cerebro import texto_a_voz


def hablar(texto: str) -> dict[str, Any]:
    """
    Sintetiza `texto` vía cadena TTS de providers (ElevenLabs → Cartesia).

    Returns:
        dict serializable para la API:
        audio_base64, audio_mime, tts_disponible, exito, error, motor
    """
    resultado = texto_a_voz(texto)
    motor = getattr(resultado, "motor", None) or "tts"
    return {
        "exito": bool(resultado.tts_disponible and resultado.audio_base64),
        "audio_base64": resultado.audio_base64,
        "audio_mime": resultado.audio_mime or "audio/mpeg",
        "tts_disponible": resultado.tts_disponible,
        "error": resultado.error,
        "motor": motor,
    }
