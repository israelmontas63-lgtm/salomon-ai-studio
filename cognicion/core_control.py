# -*- coding: utf-8 -*-
"""
[FILE: core_control] — Capas de control del Botón Central (Salomón AI).

    trigger_ai_core(data_payload)  → canal rápido al cerebro
    request_ui_action(action_id)   → portero (cámara/menús) bloqueado en AI_PROCESSING

Backend: FastAPI.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable


class AppState(Enum):
    IDLE = 0
    AI_PROCESSING = 1
    UI_LOCKED = 2


# Estado centralizado del cerebro Salomón
_system_state: dict[str, Any] = {"status": AppState.IDLE, "last_block": None}


def get_system_state() -> dict[str, Any]:
    st = _system_state["status"]
    return {
        "ok": True,
        "status": st.name if isinstance(st, AppState) else str(st),
        "status_code": int(st.value) if isinstance(st, AppState) else -1,
        "is_ai_processing": st == AppState.AI_PROCESSING,
        "last_block": _system_state.get("last_block"),
    }


def execute_brain_sync(
    data_payload: dict[str, Any] | str,
    *,
    obtener_sesion: Callable[[str | None], tuple[str, Any]] | None = None,
) -> dict[str, Any]:
    """[CORE LOGIC] Conexión directa al motor (sin middleware de cámara/menús)."""
    from cognicion.ai_lock import execute_salomon_brain_process

    if isinstance(data_payload, str):
        payload = {"mensaje": data_payload}
    else:
        payload = dict(data_payload or {})

    return execute_salomon_brain_process(
        str(payload.get("mensaje") or ""),
        session_id=payload.get("session_id"),
        imagen_base64=payload.get("imagen_base64"),
        imagen_mime=str(payload.get("imagen_mime") or "image/png"),
        lat=payload.get("lat"),
        lon=payload.get("lon"),
        obtener_sesion=obtener_sesion,
    )


def trigger_ai_core(
    data_payload: dict[str, Any] | str | None = None,
    *,
    obtener_sesion: Callable[[str | None], tuple[str, Any]] | None = None,
    only_activate: bool = False,
) -> dict[str, Any]:
    """
    Acción directa: el Botón Central toma control total.
    Obligatorio desde el smart-button (no otro middleware).
    """
    from cognicion import ai_lock

    _system_state["status"] = AppState.AI_PROCESSING
    # Espejo en app_state legacy (ui_layer_manager / JS)
    ai_lock.app_state["is_ai_active"] = True
    ai_lock.app_state["reason"] = "trigger_ai_core"

    payload = data_payload if data_payload is not None else {}
    msg = ""
    if isinstance(payload, str):
        msg = payload.strip()
    elif isinstance(payload, dict):
        msg = str(payload.get("mensaje") or "").strip()

    result: dict[str, Any] = {
        "ok": True,
        "via": "trigger_ai_core",
        "status": "AI_PROCESSING",
        "modo": "ia_activa",
        "mensaje": "Modo IA activado. Otras funciones desactivadas.",
        "is_ai_active": True,
    }
    try:
        # only_activate / mensaje vacío: deja AI_PROCESSING (mic / armado)
        if only_activate or not msg:
            return {**result, **get_system_state(), "brain": None}

        brain = execute_brain_sync(payload, obtener_sesion=obtener_sesion)
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
        # Liberar salvo only_activate (el cliente llama release al terminar mic/voz)
        if not only_activate:
            _system_state["status"] = AppState.IDLE
            ai_lock.app_state["is_ai_active"] = False
            ai_lock.app_state["reason"] = "trigger_ai_core_done"
            result["status"] = "IDLE"
            result["is_ai_active"] = False
            result["restaurado"] = True
            result["mensaje_cierre"] = "Modo IA desactivado. Funciones restauradas."


def request_ui_action(action_id: str) -> dict[str, Any]:
    """
    Capa de Auditoría Técnica / ui_layer_manager.
    Si status == AI_PROCESSING → cámara y menús no reciben la orden.
    """
    from cognicion import ai_lock

    name = (action_id or "secondary").strip() or "secondary"
    processing = (
        _system_state["status"] == AppState.AI_PROCESSING
        or bool(ai_lock.app_state.get("is_ai_active"))
    )
    if processing:
        block = {
            "status": "BLOCKED",
            "reason": "AI_PRIORITY_ACTIVE",
            "ok": False,
            "allowed": False,
            "blocked": True,
            "action_id": name,
            "mensaje": f"Acción {name} bloqueada por prioridad de IA.",
        }
        _system_state["last_block"] = block
        return block

    return {
        "status": "OK",
        "ok": True,
        "allowed": True,
        "blocked": False,
        "action_id": name,
        "mensaje": f"Ejecutando función secundaria: {name}",
    }


def execute_action(action_id: str) -> dict[str, Any]:
    """Hook de feature secundaria (el hardware real vive en el cliente)."""
    gate = request_ui_action(action_id)
    if gate.get("blocked"):
        return gate
    return {
        **gate,
        "executed": True,
        "mensaje": f"Feature lista: {action_id}",
    }
