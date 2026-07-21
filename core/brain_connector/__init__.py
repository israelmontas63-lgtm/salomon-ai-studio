# -*- coding: utf-8 -*-
"""
Puente directo al núcleo de Salomón — sin middleware de cámara/menús.

Enlaces:
  · send_visual_to_core / bridge_status — visión → cerebro
  · trigger_ai_core — canal rápido UI → AppState / cognición
"""

from __future__ import annotations

from core.brain_connector.bridge import send_visual_to_core, bridge_status

try:
    from cognicion.core_control import trigger_ai_core
except Exception:  # fail-soft en boot parcial
    def trigger_ai_core(*_a, **_k):  # type: ignore[misc]
        return {"ok": False, "error": "trigger_ai_core_unavailable", "error_codigo": 25}


__all__ = ["send_visual_to_core", "bridge_status", "trigger_ai_core"]
