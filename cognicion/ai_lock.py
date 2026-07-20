# -*- coding: utf-8 -*-
"""
Estado global de exclusividad del botón central (IA).

Patrón canónico (Israel):

    app_state = {"is_ai_active": False}

    handle_central_button_click():
        app_state["is_ai_active"] = True
        try:
            return execute_salomon_brain_process(...)
        finally:
            app_state["is_ai_active"] = False

    ui_layer_manager(function_name):
        if app_state["is_ai_active"]: return False  # bloquea cámara/menús
        execute_standard_feature(...)
        return True

Backend: FastAPI. UI espejo: static/js/ai_state_lock.js
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

# Estado global para manejar la exclusividad
app_state: dict[str, Any] = {
    "is_ai_active": False,
    "reason": "",
    "updated_at": None,
    "session_id": None,
    "last_result": None,
    "last_blocked": None,
}


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_ai_active() -> bool:
    return bool(app_state.get("is_ai_active"))


def activar(*, reason: str = "smart_button", session_id: str | None = None) -> dict[str, Any]:
    app_state["is_ai_active"] = True
    app_state["reason"] = reason or "smart_button"
    app_state["session_id"] = session_id
    app_state["updated_at"] = _utc()
    try:
        from cognicion.core_control import AppState, _system_state

        _system_state["status"] = AppState.AI_PROCESSING
    except Exception:
        pass
    return estado()


def liberar(*, reason: str = "done") -> dict[str, Any]:
    app_state["is_ai_active"] = False
    app_state["reason"] = reason or "done"
    app_state["updated_at"] = _utc()
    try:
        from cognicion.core_control import AppState, _system_state

        _system_state["status"] = AppState.IDLE
    except Exception:
        pass
    return estado()


def estado() -> dict[str, Any]:
    return {
        "ok": True,
        "is_ai_active": bool(app_state["is_ai_active"]),
        "reason": app_state.get("reason") or "",
        "session_id": app_state.get("session_id"),
        "updated_at": app_state.get("updated_at"),
        "last_blocked": app_state.get("last_blocked"),
        "prioridad": "smart_button",
        "mensaje": (
            "Modo IA activado. Otras funciones desactivadas."
            if app_state["is_ai_active"]
            else "Modo IA desactivado. Funciones restauradas."
        ),
        "endpoints": {
            "central_button": "/api/ai/central-button",
            "secondary": "/api/ai/secondary",
            "lock": "/api/ai/lock",
            "cerebro_directo": "/api/ai-process",
        },
    }


def execute_salomon_brain_process(
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
    Conexión directa al núcleo (Cerebro de Salomón).
    Omite middleware secundario (cámara/menús) para respuesta directa.
    """
    from mente.conexion import procesar_unificado

    if obtener_sesion is None:
        raise RuntimeError("obtener_sesion requerida para execute_salomon_brain_process")

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
        "via": "execute_salomon_brain_process",
    }
    app_state["last_result"] = {
        "exito": pack["exito"],
        "session_id": sid,
        "chars": len(pack["texto"]),
        "at": _utc(),
    }
    return pack


# Alias histórico
call_salomon_brain = execute_salomon_brain_process


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
    Manejo prioritario del botón central hacia el cerebro de Salomón.

    Prioridad absoluta: is_ai_active=True → ui_layer_manager bloquea el resto.
    Seguridad: finally siempre libera el bloqueo (salvo only_activate).
    """
    # Activar bloqueo de capas: ninguna otra función podrá ejecutarse
    app_state["is_ai_active"] = True
    app_state["reason"] = "central_button"
    app_state["session_id"] = session_id
    app_state["updated_at"] = _utc()

    result: dict[str, Any] = {
        "ok": True,
        "modo": "ia_activa",
        "mensaje": "Modo IA activado. Otras funciones desactivadas.",
        "is_ai_active": True,
    }
    try:
        if only_activate or not (mensaje or "").strip():
            return {**result, **estado(), "brain": None}

        # Conexión directa al núcleo — sin middleware secundario
        brain = execute_salomon_brain_process(
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
        result["ok"] = False
        result["error"] = f"{type(exc).__name__}:{exc}"
        result["brain"] = None
        result["mensaje"] = "Error en el cerebro; restaurando funciones."
        return result
    finally:
        # Liberar el bloqueo una vez completada la tarea (aunque falle)
        if not only_activate:
            app_state["is_ai_active"] = False
            app_state["reason"] = "central_button_done"
            app_state["updated_at"] = _utc()
            result["is_ai_active"] = False
            result["restaurado"] = True
            result["mensaje_cierre"] = "Modo IA desactivado. Funciones restauradas."


def ui_layer_manager(function_name: str = "camera") -> dict[str, Any]:
    """
    Capa de control para funciones secundarias (Cámara, Menús, etc.).

    Si la IA está activa → bloquea cualquier otra entrada (return False semántico).
    """
    name = (function_name or "secondary").strip() or "secondary"
    if app_state["is_ai_active"]:
        app_state["last_blocked"] = {"function": name, "at": _utc()}
        return {
            "ok": False,
            "allowed": False,
            "blocked": True,
            "accion": name,
            "function_name": name,
            "mensaje": f"Acción {name} bloqueada por prioridad de IA.",
            "is_ai_active": True,
        }

    # Ejecución normal si el botón central no está en uso
    return {
        "ok": True,
        "allowed": True,
        "blocked": False,
        "accion": name,
        "function_name": name,
        "mensaje": f"Ejecutando función secundaria: {name}",
        "is_ai_active": False,
    }


def execute_standard_feature(function_name: str) -> dict[str, Any]:
    """Hook de feature secundaria (la UI real ejecuta el hardware en el cliente)."""
    return {
        "ok": True,
        "executed": True,
        "function_name": function_name,
        "mensaje": f"Feature lista: {function_name}",
    }


def handle_camera_or_other_functions(accion: str = "camera") -> dict[str, Any]:
    """Alias → ui_layer_manager (compatibilidad)."""
    gate = ui_layer_manager(accion)
    if gate.get("allowed"):
        feat = execute_standard_feature(accion)
        return {**gate, **feat}
    return gate


# Alias legacy
_STATE = app_state
