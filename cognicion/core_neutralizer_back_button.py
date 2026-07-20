# -*- coding: utf-8 -*-
"""
[FILE: core_neutralizer_back_button.py] — Neutralizador Universal por Capas.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class UniversalNeutralizerBackButton:
    def __init__(self) -> None:
        self.component = "UniversalNeutralizerBackButton"
        self.designation = "Master Neutralizer Layer"

    def compile_neutralizer_logic(self) -> str:
        spec = {
            "component": self.component,
            "position": "Top-Left Corner (Absolute Top Layer / Max Z-Index)",
            "behavior": (
                "Acts as a neutralizer: pops the current active layer instantly "
                "regardless of where the user is (tools, camera, sub-views), "
                "returning to the stable previous state without resetting the core assistant."
            ),
            "z_index": 100010,
            "assets": {
                "js": "static/js/back_button.js",
                "css": "static/css/back_button.css",
                "id": "btn-back",
            },
            "deployment": "Auto-commit and push to Render production",
        }
        return json.dumps(spec, indent=2)

    def verify(self) -> dict:
        js = (ROOT / "static" / "js" / "back_button.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "css" / "back_button.css").read_text(encoding="utf-8")
        return {
            "ok": "neutralize" in js and "100010" in css,
            "designation": self.designation,
        }


if __name__ == "__main__":
    controller = UniversalNeutralizerBackButton()
    print(controller.compile_neutralizer_logic())
    print(controller.verify())
