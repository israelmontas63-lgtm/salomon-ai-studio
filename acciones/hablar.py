"""
Primera acción real: hablar con ElevenLabs (motor principal).

Delega en cerebro.texto_a_voz. La reproducción y limpieza automática
están en acciones.reproducir.hablar_y_reproducir.
"""

from __future__ import annotations

from typing import Any

from cerebro import texto_a_voz


def hablar(texto: str) -> dict[str, Any]:
    """
    Sintetiza `texto` con la voz local configurada en Salomón.

    Returns:
        dict serializable para la API:
        audio_base64, audio_mime, tts_disponible, exito, error
    """
    resultado = texto_a_voz(texto)
    return {
        "exito": bool(resultado.tts_disponible and resultado.audio_base64),
        "audio_base64": resultado.audio_base64,
        "audio_mime": resultado.audio_mime or "audio/mpeg",
        "tts_disponible": resultado.tts_disponible,
        "error": resultado.error,
        "motor": "elevenlabs",
    }
