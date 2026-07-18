# -*- coding: utf-8 -*-
"""
Parámetros de voz — puerto de entrada de Salomón (STT / TTS / mic).
Vinculados al núcleo; no dependen de búsquedas externas.
"""

from __future__ import annotations

import os
from typing import Any

# Puerto de entrada de audio (cliente + API)
MIC_ALWAYS_READY = os.getenv("MIC_ALWAYS_READY", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
STT_LANG = (os.getenv("STT_LANG", "es-ES") or "es-ES").strip()
STT_INTERIM = os.getenv("STT_INTERIM", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
# 1 toque = dictado → input; 2 toques = conversación → /api/chat
VOICE_GESTURE_PROTOCOL = "tap1_dictado_tap2_ia"
VOICE_PORT = "salomon_input_audio"
TTS_VIA = "api/tts"  # Cartesia Sonic vía backend
CHAT_VIA = "api/chat"

# Remap hardware si el botón no abre el device
HARDWARE_REMAP_ON_FAIL = True


def voice_parameters() -> dict[str, Any]:
    return {
        "port": VOICE_PORT,
        "mic_always_ready": MIC_ALWAYS_READY,
        "stt_lang": STT_LANG,
        "stt_interim": STT_INTERIM,
        "gesture_protocol": VOICE_GESTURE_PROTOCOL,
        "tts_endpoint": TTS_VIA,
        "chat_endpoint": CHAT_VIA,
        "hardware_remap_on_fail": HARDWARE_REMAP_ON_FAIL,
        "sincronizado": True,
        "nucleo": "SalomonAI.procesar_entrada + SpeechRecognition + /api/tts",
    }


def voice_status() -> dict[str, Any]:
    p = voice_parameters()
    return {
        "sincronizado": bool(p["sincronizado"] and p["mic_always_ready"]),
        "parametros": p,
    }
