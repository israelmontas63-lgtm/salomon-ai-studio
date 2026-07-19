# -*- coding: utf-8 -*-
"""Plugin periférico audio (STT/TTS) — Level 9."""

from __future__ import annotations

from typing import Any

_ACTIVO = False
_ESTADO: dict[str, Any] = {}


def activar(app: Any = None) -> bool:
    global _ACTIVO, _ESTADO
    from config.providers import Servicio, seleccionar

    stt = seleccionar(Servicio.STT)
    tts = seleccionar(Servicio.TTS)
    _ESTADO = {
        "stt": stt.nombre if stt else None,
        "tts": tts.nombre if tts else None,
        "stt_listo": bool(stt),
        "tts_listo": bool(tts),
    }
    # Al menos uno de los dos para marcar periférica audio operativa
    _ACTIVO = bool(stt or tts)
    return _ACTIVO


def desactivar() -> None:
    global _ACTIVO
    _ACTIVO = False


def estado() -> dict[str, Any]:
    return {"plugin": "audio_stack", "activo": _ACTIVO, **_ESTADO}
