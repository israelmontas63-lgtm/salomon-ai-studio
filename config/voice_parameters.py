# -*- coding: utf-8 -*-
"""
Parámetros de voz — puerto de entrada PWA (STT / TTS / mic).

Runtime web: SpeechRecognition + getUserMedia + único backend TTS `/api/tts`
(ElevenLabs → Cartesia vía config.providers). No asume app nativa ni remap ciego.
"""

from __future__ import annotations

import os
from typing import Any

# Puerto de entrada de audio (cliente PWA + API)
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
# 1 toque = dictado; 2 toques = conversación → /api/chat
VOICE_GESTURE_PROTOCOL = "tap1_dictado_tap2_ia"
VOICE_PORT = "salomon_input_audio"
TTS_VIA = "api/tts"  # Única ruta HTTP → ServiceManager (ElevenLabs → Cartesia)
CHAT_VIA = "api/chat"
RUNTIME = "pwa"  # Progressive Web App — no nativo

# Códigos claros para el cliente PWA (sin HARDWARE_REMAP_ON_FAIL)
MEDIA_ERRORS = (
    "NotAllowedError",
    "NotFoundError",
    "NotReadableError",
    "OverconstrainedError",
    "SecurityError",
    "AbortError",
)


def _tts_from_providers() -> dict[str, Any]:
    """Alinea el puerto de voz con la cadena TTS de providers.py."""
    try:
        from config.providers import Servicio, cadena_nombres, seleccionar

        slot = seleccionar(Servicio.TTS)
        chain = cadena_nombres(Servicio.TTS)
        return {
            "tts_provider_activo": slot.nombre if slot else None,
            "tts_cadena": chain,
            "tts_unificado": True,
            "tts_endpoint": TTS_VIA,
        }
    except Exception as exc:
        return {
            "tts_provider_activo": None,
            "tts_cadena": [],
            "tts_unificado": False,
            "tts_endpoint": TTS_VIA,
            "tts_sync_error": type(exc).__name__,
        }


def classify_media_error(err: Any) -> dict[str, Any]:
    """Excepción explícita para bloqueos de mic/audio en el navegador PWA."""
    name = ""
    message = ""
    if isinstance(err, dict):
        name = str(err.get("name") or err.get("code") or "")
        message = str(err.get("message") or err.get("detalle") or "")
    elif isinstance(err, BaseException):
        name = type(err).__name__
        message = str(err) or name
    else:
        name = str(getattr(err, "name", "") or "")
        message = str(err or "")

    name_l = (name or "").strip()
    known = name_l in MEDIA_ERRORS
    return {
        "ok": False,
        "error": name_l or "MediaError",
        "message": message[:400],
        "known_browser_block": known,
        "remap": False,  # prohibido remap ciego
        "hint": (
            "El navegador bloqueó el micrófono o el puerto de audio. "
            "Revisa permisos del sitio, foco de la pestaña y Service Worker."
            if known or "permission" in message.lower()
            else "Fallo de medios en PWA — ver consola [SalomonVoicePort]."
        ),
        "runtime": RUNTIME,
    }


def voice_parameters() -> dict[str, Any]:
    tts = _tts_from_providers()
    return {
        "port": VOICE_PORT,
        "runtime": RUNTIME,
        "mic_always_ready": MIC_ALWAYS_READY,
        "stt_lang": STT_LANG,
        "stt_interim": STT_INTERIM,
        "gesture_protocol": VOICE_GESTURE_PROTOCOL,
        "tts_endpoint": TTS_VIA,
        "chat_endpoint": CHAT_VIA,
        "hardware_remap_on_fail": False,
        "media_errors": list(MEDIA_ERRORS),
        "sincronizado": True,
        "nucleo": (
            "PWA: SpeechRecognition + /api/tts (ElevenLabs→Cartesia) "
            "+ SalomonAI.procesar_entrada"
        ),
        **tts,
    }


def voice_status() -> dict[str, Any]:
    p = voice_parameters()
    return {
        "sincronizado": bool(
            p.get("sincronizado")
            and p.get("mic_always_ready")
            and p.get("tts_unificado")
        ),
        "parametros": p,
    }
