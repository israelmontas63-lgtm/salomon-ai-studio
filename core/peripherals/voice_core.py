# -*- coding: utf-8 -*-
"""VoiceCore (server mirror) — parámetros de filtro de voz humana."""

from __future__ import annotations

from typing import Any

HP_HZ = 300
LP_HZ = 3400
SENSITIVITY = 0.8


class VoiceCore:
    _noise_gate = False

    @classmethod
    def enableNoiseGate(cls, on: bool = True) -> bool:
        cls._noise_gate = bool(on)
        return cls._noise_gate

    @classmethod
    def estado(cls) -> dict[str, Any]:
        return {
            "noise_gate": cls._noise_gate,
            "band_hz": [HP_HZ, LP_HZ],
            "sensitivity": SENSITIVITY,
            "adaptive_suppression": True,
            "port": "salomon_input_audio",
            "sincronizado": True,
        }
