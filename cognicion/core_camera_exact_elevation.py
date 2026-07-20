# -*- coding: utf-8 -*-
"""
[FILE: core_camera_exact_elevation.py] — Elevación exacta 5 mm (~19px) del botón cámara.
Capa: UI_Navigation_View solamente.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CameraExactElevationEngine:
    def __init__(self) -> None:
        self.target_layer = "UI_Navigation_View"
        self.elevation_metric_mm = 5

    def get_elevation_calculation(self) -> str:
        elevation_spec = {
            "component": "Camera_Button",
            "action": "shift_position_upwards",
            "offset_value_mm": 5,
            "approx_pixels_conversion": "19px",
            "layer_isolation": (
                "Strictly confined to view layer, zero impact on SalomonBrain core."
            ),
            "css": "static/css/camera_toggle_ui.css",
            "transform": "translateY(-19px)",
        }
        return json.dumps(elevation_spec, indent=2)

    def verify(self) -> dict:
        css = (ROOT / "static" / "css" / "camera_toggle_ui.css").read_text(encoding="utf-8")
        return {"ok": "translateY(-19px)" in css, "mm": self.elevation_metric_mm}


if __name__ == "__main__":
    engine = CameraExactElevationEngine()
    print(engine.get_elevation_calculation())
    print(engine.verify())
