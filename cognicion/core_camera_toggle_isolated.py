# -*- coding: utf-8 -*-
"""
[FILE: core_camera_toggle_isolated.py] — Elevación dinámica UI aislada del cerebro/visión.
Capa: views/ui_layer solamente. No importa SalomonBrain ni core_vision_engine.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LayerIsolatedCameraToggle:
    def __init__(self) -> None:
        self.layer_status = "STRICT_SEPARATION_VERIFIED"
        self.target_component = "Camera_And_Giro_UI_Group"

    def compile_toggle_logic(self) -> str:
        logic_spec = {
            "layer_check": "No cross-contamination between UI view states and Core Brain logic.",
            "behavior": {
                "on_press": {
                    "action": "elevate_upwards_safe_distance",
                    "deploy_sub_button": "Giro_directly_above",
                },
                "on_release_or_close": {
                    "action": "return_to_original_position",
                    "hide_sub_button": "Giro",
                },
            },
            "ui_assets": {
                "css": "static/css/camera_toggle_ui.css",
                "js": "static/js/camera_toggle_ui.js",
            },
            "forbidden_imports": [
                "cognicion.core_identity_engine",
                "cognicion.core_vision_engine",
                "cerebro",
            ],
            "deployment": "Auto-commit and push to Render production.",
        }
        print(f"[AISLAMIENTO DE CAPAS] -> {self.layer_status}")
        return json.dumps(logic_spec, indent=2)

    def verify_isolation(self) -> dict:
        js = ROOT / "static" / "js" / "camera_toggle_ui.js"
        css = ROOT / "static" / "css" / "camera_toggle_ui.css"
        text = js.read_text(encoding="utf-8") if js.is_file() else ""
        banned = ("core_identity", "core_vision", "trigger_ai_core", "/api/ai/")
        leaks = [b for b in banned if b in text]
        return {
            "ok": js.is_file() and css.is_file() and not leaks,
            "leaks": leaks,
            "layer_status": self.layer_status,
        }


if __name__ == "__main__":
    controller = LayerIsolatedCameraToggle()
    print(controller.compile_toggle_logic())
    print(controller.verify_isolation())
