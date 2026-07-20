# -*- coding: utf-8 -*-
"""
Capa visual pura (botones, contenedores, barras) — sin motor de análisis.
Solo portero de exclusividad UI ↔ AppState.
"""

from __future__ import annotations

from typing import Any


def assert_vision_ui_gate(action_id: str = "vision_capture") -> dict[str, Any]:
    """
    Auditoría de capa UI. No ejecuta cámara aquí (eso es capture_layer / JS).
    Si AI_PROCESSING, reporta bloqueo de funciones secundarias.
    """
    from cognicion.core_control import get_system_state, request_ui_action

    state = get_system_state()
    # El puente al cerebro usa trigger_ai_core (exclusivo).
    # Las acciones secundarias de UI (abrir menús, flip, etc.) sí se bloquean.
    if action_id in ("camera", "flip", "settings", "aa_input"):
        return request_ui_action(action_id)
    return {
        "ok": True,
        "layer": "ui_layer",
        "action_id": action_id,
        "app_state": state,
        "note": "UI layer audit only — analysis/brain live elsewhere",
    }


def ui_layer_status() -> dict[str, Any]:
    from cognicion.core_control import get_system_state

    return {
        "layer": "ui_layer",
        "path": "views/ui_layer/",
        "role": "botones_contenedores_barras",
        "mixes_with_analysis": False,
        "app_state": get_system_state(),
    }
