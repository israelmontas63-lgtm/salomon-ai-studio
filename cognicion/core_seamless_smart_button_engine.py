# -*- coding: utf-8 -*-
"""
[FILE: core_seamless_smart_button_engine.py]
Motor del Botón Inteligente — gestos sinápticos (1 toque / 2 toques / apagado).
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DOUBLE_TAP_MS = 320


class SeamlessSmartButtonEngine:
    def __init__(self) -> None:
        self.module = "SeamlessSmartButtonEngine"
        self.version = "2.0.0-synaptic"
        self.double_tap_ms = DOUBLE_TAP_MS

    def compile_production_spec(self) -> str:
        spec = {
            "component": "Salomon_Smart_Button_Synaptic",
            "version": self.version,
            "ux_standard": (
                "Zero-friction tap gestures: 1=dictation, 2=AI, tap-off=release."
            ),
            "interaction_matrix": {
                "single_tap": "Dictation / STT Mode",
                "double_tap": f"Full AI Mode (within {self.double_tap_ms}ms)",
                "neutralize_tap": "Stop mic + AI lock + vision streaming",
            },
            "safety_checks": "Strict state isolation; vision+voice synapse (no camera UI block).",
            "assets": {
                "js": "static/js/components/SmartButton.js",
                "css": "static/css/boton.css",
                "id": "smart-button",
                "controller": "cognicion/core_salomon_smart_button_synaptic_controller.py",
            },
            "thresholds": {"double_tap_ms": self.double_tap_ms},
            "deployment": (
                "Auto-deploy to Render + PWA hot-loader with settings badge notification."
            ),
        }
        return json.dumps(spec, indent=2)

    def verify(self) -> dict[str, Any]:
        js = (ROOT / "static" / "js" / "components" / "SmartButton.js").read_text(
            encoding="utf-8", errors="ignore"
        )
        css = (ROOT / "static" / "css" / "boton.css").read_text(
            encoding="utf-8", errors="ignore"
        )
        cam_block = (
            "if (window.SalomonCamera && window.SalomonCamera.isActive()) return true;"
            in js
        )
        ok = (
            "DOUBLE_TAP_MS" in js
            and "_tapCount" in js
            and "DICTATION" in js
            and "CONVERSATIONAL" in js
            and "neutralize" in js
            and "disengageVisualMode" in js
            and not cam_block
            and "is-seamless" in css
            and "100050" in css
        )
        return {
            "ok": ok,
            "module": self.module,
            "version": self.version,
            "double_tap_ms": self.double_tap_ms,
            "camera_ui_block_removed": not cam_block,
        }


if __name__ == "__main__":
    engine = SeamlessSmartButtonEngine()
    print(engine.compile_production_spec())
    print(engine.verify())
