"""
Acción hablar — Cartesia Sonic-3.5 (WebSocket, baja latencia).

Delega en cerebro.texto_a_voz → cognicion.voz.cartesia_tts.hablar_salomon.
"""

from __future__ import annotations

from typing import Any

from cerebro import texto_a_voz


def hablar(texto: str) -> dict[str, Any]:
    """
    Sintetiza `texto` con Cartesia Sonic-3.5.

    Returns:
        dict serializable para la API:
        audio_base64, audio_mime, tts_disponible, exito, error, motor
    """
    resultado = texto_a_voz(texto)
    return {
        "exito": bool(resultado.tts_disponible and resultado.audio_base64),
        "audio_base64": resultado.audio_base64,
        "audio_mime": resultado.audio_mime or "audio/wav",
        "tts_disponible": resultado.tts_disponible,
        "error": resultado.error,
        "motor": getattr(resultado, "motor", None) or "cartesia-sonic-3.5",
    }
