# -*- coding: utf-8 -*-
"""
State lock del Botón Central (IA) — espejo servidor.

La exclusividad real vive en el cliente (static/js/ai_state_lock.js).
Aquí se registra prioridad / telemetría para el cerebro FastAPI.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_STATE: dict[str, Any] = {
    "is_ai_active": False,
    "reason": "",
    "updated_at": None,
    "session_id": None,
}


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def activar(*, reason: str = "smart_button", session_id: str | None = None) -> dict[str, Any]:
    _STATE["is_ai_active"] = True
    _STATE["reason"] = reason or "smart_button"
    _STATE["session_id"] = session_id
    _STATE["updated_at"] = _utc()
    return estado()


def liberar(*, reason: str = "done") -> dict[str, Any]:
    _STATE["is_ai_active"] = False
    _STATE["reason"] = reason or "done"
    _STATE["updated_at"] = _utc()
    return estado()


def estado() -> dict[str, Any]:
    return {
        "ok": True,
        "is_ai_active": bool(_STATE["is_ai_active"]),
        "reason": _STATE.get("reason") or "",
        "session_id": _STATE.get("session_id"),
        "updated_at": _STATE.get("updated_at"),
        "prioridad": "smart_button",
        "mensaje": (
            "IA activa — capas secundarias deben ignorar entrada"
            if _STATE["is_ai_active"]
            else "IA inactiva — cámara y menús disponibles"
        ),
        "endpoints": {
            "cerebro_directo": "/api/ai-process",
            "chat": "/api/chat",
            "lock": "/api/ai/lock",
        },
    }


def is_ai_active() -> bool:
    return bool(_STATE["is_ai_active"])
