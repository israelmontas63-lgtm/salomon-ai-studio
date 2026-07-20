# -*- coding: utf-8 -*-
"""
State lock del Botón Central (IA) — jerarquía pedida por Israel.

Patrón canónico (espejo del pseudocódigo de control):

    app_state = {"is_ai_active": False}
    handle_central_button_click()  → activa lock → call_salomon_brain() → libera
    handle_camera_or_other_functions() → bloquea si is_ai_active

La exclusividad de UI también vive en static/js/ai_state_lock.js.
Backend: FastAPI (no Flask).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

# Definición del estado global de la aplicación
app_state: dict[str, Any] = {
    "is_ai_active": False,
    "reason": "",
    "updated_at": None,
    "session_id": None,
    "last_result": None,
}


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_ai_active() -> bool:
    return bool(app_state.get("is_ai_active"))


def activar(*, reason: str = "smart_button", session_id: str | None = None) -> dict[str, Any]:
    """Activa exclusividad: bloquea otras funciones."""
    app_state["is_ai_active"] = True
    app_state["reason"] = reason or "smart_button"
    app_state["session_id"] = session_id
    app_state["updated_at"] = _utc()
    return estado()


def liberar(*, reason: str = "done") -> dict[str, Any]:
    """Restaura funciones secundarias."""
    app_state["is_ai_active"] = False
    app_state["reason"] = reason or "done"
    app_state["updated_at"] = _utc()
    return estado()


def estado() -> dict[str, Any]:
    return {
        "ok": True,
        "is_ai_active": bool(app_state["is_ai_active"]),
        "reason": app_state.get("reason") or "",
        "session_id": app_state.get("session_id"),
        "updated_at": app_state.get("updated_at"),
        "prioridad": "smart_button",
        "mensaje": (
            "Modo IA activado. Otras funciones desactivadas."
            if app_state["is_ai_active"]
            else "Modo IA desactivado. Funciones restauradas."
        ),
        "endpoints": {
            "cerebro_directo": "/api/ai-process",
            "central_button": "/api/ai/central-button",
            "chat": "/api/chat",
            "lock": "/api/ai/lock",
        },
    }


def call_salomon_brain(
    mensaje: str,
    *,
    session_id: str | None = None,
    imagen_base64: str | None = None,
    imagen_mime: str = "image/png",
    lat: float | None = None,
    lon: float | None = None,
    obtener_sesion: Callable[[str | None], tuple[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Conexión directa al cerebro de Salomón (sin middleware de cámara/menús).
    """
    from mente.conexion import procesar_unificado

    if obtener_sesion is None:
        raise RuntimeError("obtener_sesion requerida para call_salomon_brain")

    sid, salomon = obtener_sesion(session_id)
    respuesta = procesar_unificado(
        mensaje,
        session_id=sid,
        salomon=salomon,
        lat=lat,
        lon=lon,
        imagen_base64=imagen_base64,
        imagen_mime=imagen_mime or "image/png",
        autonomo=False,
    )
    pack = {
        "texto": getattr(respuesta, "texto", "") or "",
        "exito": bool(getattr(respuesta, "exito", True)),
        "session_id": sid,
        "metadata": getattr(respuesta, "metadata", None) or {},
        "audio_base64": getattr(respuesta, "audio_base64", None),
        "audio_mime": getattr(respuesta, "audio_mime", None) or "audio/mpeg",
        "tts_disponible": bool(getattr(respuesta, "tts_disponible", False)),
        "via": "call_salomon_brain",
    }
    app_state["last_result"] = {
        "exito": pack["exito"],
        "session_id": sid,
        "chars": len(pack["texto"]),
        "at": _utc(),
    }
    return pack


def handle_central_button_click(
    mensaje: str = "",
    *,
    session_id: str | None = None,
    imagen_base64: str | None = None,
    imagen_mime: str = "image/png",
    lat: float | None = None,
    lon: float | None = None,
    obtener_sesion: Callable[[str | None], tuple[str, Any]] | None = None,
    only_activate: bool = False,
) -> dict[str, Any]:
    """
    Lógica para el botón central (IA).

    1) is_ai_active = True (bloquea otras funciones)
    2) call_salomon_brain() si hay mensaje
    3) finally → is_ai_active = False
    """
    # Prioridad: cualquier cámara/menú secundario queda rechazado por la capa de control.
    activar(reason="central_button", session_id=session_id)
    result: dict[str, Any] = {
        "ok": True,
        "modo": "ia_activa",
        "mensaje": "Modo IA activado. Otras funciones desactivadas.",
        "is_ai_active": True,
    }
    try:
        if only_activate or not (mensaje or "").strip():
            # Solo señal de activación (el cliente mantiene el lock hasta el cierre)
            return {**result, **estado(), "brain": None}
        # Conexión directa al motor — sin middleware de cámara/menús.
        brain = call_salomon_brain(
            mensaje.strip(),
            session_id=session_id,
            imagen_base64=imagen_base64,
            imagen_mime=imagen_mime,
            lat=lat,
            lon=lon,
            obtener_sesion=obtener_sesion,
        )
        result["brain"] = brain
        result["ok"] = bool(brain.get("exito"))
        return result
    except Exception as exc:
        # Seguridad: el error no deja el sistema trabado en IA
        result["ok"] = False
        result["error"] = f"{type(exc).__name__}:{exc}"
        result["brain"] = None
        result["mensaje"] = "Error en el cerebro; restaurando funciones."
        return result
    finally:
        # try...finally fundamental: desbloquea aunque falle el procesamiento.
        if not only_activate:
            liberar(reason="central_button_done")
            result["is_ai_active"] = False
            result["restaurado"] = True
            result["mensaje_cierre"] = "Modo IA desactivado. Funciones restauradas."


def handle_camera_or_other_functions(accion: str = "camera") -> dict[str, Any]:
    """
    Ejemplo para cualquier otra función de la UI.
    Capa de control: impide activación si la IA está trabajando.
    """
    if app_state["is_ai_active"]:
        return {
            "ok": False,
            "blocked": True,
            "accion": accion,
            "mensaje": "Acción bloqueada: la IA está en uso.",
            "is_ai_active": True,
        }
    return {
        "ok": True,
        "blocked": False,
        "accion": accion,
        "mensaje": "Ejecutando función secundaria...",
        "is_ai_active": False,
    }


# Alias legacy usados por app.py / JS sync
_STATE = app_state
