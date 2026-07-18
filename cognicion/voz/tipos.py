# -*- coding: utf-8 -*-
"""Tipos ligeros de TTS — sin importar el SDK Cartesia (boot Free Tier)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
