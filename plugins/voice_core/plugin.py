# -*- coding: utf-8 -*-
"""Plugin periférico VoiceCore — Level 9 hot-plug."""

from __future__ import annotations

from typing import Any

_ACTIVO = False


def activar(app: Any = None) -> bool:
    global _ACTIVO
    from core.peripherals.voice_core import VoiceCore

    VoiceCore.enableNoiseGate(True)
    _ACTIVO = True
    return True


def desactivar() -> None:
    global _ACTIVO
    from core.peripherals.voice_core import VoiceCore

    VoiceCore.enableNoiseGate(False)
    _ACTIVO = False


def estado() -> dict[str, Any]:
    from core.peripherals.voice_core import VoiceCore

    return {"plugin": "voice_core", "activo": _ACTIVO, **VoiceCore.estado()}
