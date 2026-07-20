# -*- coding: utf-8 -*-
"""
brain_bridge — canal rápido captura → núcleo (trigger_ai_core).
Exclusividad: AI_PROCESSING bloquea hardware secundario.
"""

from __future__ import annotations

from typing import Any, Callable


def send_visual_to_core(
    *,
    mensaje: str,
    imagen_base64: str,
    imagen_mime: str = "image/jpeg",
    session_id: str | None = None,
    obtener_sesion: Callable[[str | None], tuple[str, Any]] | None = None,
    via_central_button: bool = True,
) -> dict[str, Any]:
    """
    Conexión directa al cerebro. Preferente: trigger_ai_core (exclusividad).
    Fallback: execute_salomon_brain_process.
    """
    payload = {
        "mensaje": mensaje or "Analiza esta captura.",
        "imagen_base64": imagen_base64,
        "imagen_mime": imagen_mime or "image/jpeg",
        "session_id": session_id,
    }

    if via_central_button:
        from cognicion.core_control import trigger_ai_core

        pack = trigger_ai_core(
            payload,
            obtener_sesion=obtener_sesion,
            only_activate=False,
        )
        brain = pack.get("brain") or {}
        return {
            "ok": bool(pack.get("ok") and (brain.get("exito") if brain else pack.get("ok"))),
            "exito": bool(brain.get("exito")) if brain else bool(pack.get("ok")),
            "texto": brain.get("texto") if brain else None,
            "session_id": brain.get("session_id") if brain else session_id,
            "audio_base64": brain.get("audio_base64") if brain else None,
            "audio_mime": brain.get("audio_mime") if brain else None,
            "tts_disponible": brain.get("tts_disponible") if brain else None,
            "metadata": brain.get("metadata") if brain else {},
            "via": "trigger_ai_core",
            "layer": "brain_bridge",
            "pack": pack,
        }

    from cognicion.ai_lock import execute_salomon_brain_process

    brain = execute_salomon_brain_process(
        str(payload["mensaje"]),
        session_id=session_id,
        imagen_base64=imagen_base64,
        imagen_mime=imagen_mime,
        obtener_sesion=obtener_sesion,
    )
    return {
        "ok": bool(brain.get("exito")),
        "exito": bool(brain.get("exito")),
        "texto": brain.get("texto"),
        "session_id": brain.get("session_id"),
        "audio_base64": brain.get("audio_base64"),
        "audio_mime": brain.get("audio_mime"),
        "tts_disponible": brain.get("tts_disponible"),
        "metadata": brain.get("metadata") or {},
        "via": "execute_salomon_brain_process",
        "layer": "brain_bridge",
        "pack": {"brain": brain},
    }


def bridge_status() -> dict[str, Any]:
    return {
        "layer": "brain_bridge",
        "path": "core/brain_connector/",
        "role": "canal_rapido_nucleo",
        "middleware": False,
        "exclusivity": "AI_PROCESSING blocks secondary UI",
    }
