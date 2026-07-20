# -*- coding: utf-8 -*-
"""
[FILE: core_standard_back_button.py] — Botón Back estándar (top-left).
Capa UI_Navigation_Header. No toca SalomonBrain.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StandardBackButtonEngine:
    def __init__(self) -> None:
        self.target_layer = "UI_Navigation_Header"
        self.standard_position = "Top-Left Corner"
        self.color_scheme = {
            "border": "Gold accent (#D4AF37)",
            "background": "Deep black / semi-transparent dark overlay",
            "icon": "Clean minimalist back arrow (<)",
        }

    def generate_back_button_spec(self) -> str:
        spec = {
            "component": "Standard_Back_Button",
            "position": self.standard_position,
            "styling": self.color_scheme,
            "layer_isolation": "Strictly confined to UI view layer, preserving SalomonBrain core.",
            "assets": {
                "css": "static/css/back_button.css",
                "js": "static/js/back_button.js",
                "id": "btn-back",
            },
            "deployment": "Auto-commit and push to Render production.",
        }
        return json.dumps(spec, indent=2)

    def verify(self) -> dict:
        html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
        js = ROOT / "static" / "js" / "back_button.js"
        css = ROOT / "static" / "css" / "back_button.css"
        return {
            "ok": 'id="btn-back"' in html and js.is_file() and css.is_file(),
            "position": self.standard_position,
        }


if __name__ == "__main__":
    engine = StandardBackButtonEngine()
    print(engine.generate_back_button_spec())
    print(engine.verify())
