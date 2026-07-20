# -*- coding: utf-8 -*-
"""
[FILE: fix_giro_button_deployment.py] — Despliegue vertical del botón Giro.
Al tocar cámara: Giro aparece ~18px (5mm) encima, mismo eje X.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def get_vertical_deployment_instruction() -> str:
    deployment_spec = {
        "trigger": "on_camera_touch",
        "action": "deploy_giro_button_vertically",
        "offset_calculation": {
            "direction": "upwards",
            "distance_mm": 5,
            "approx_pixels": 18,
        },
        "z_index": 15,
        "css": {
            "position": "absolute",
            "left": "50%",
            "bottom": "calc(100% + 18px)",
            "transform": "translateX(-50%)",
            "z-index": 15,
        },
    }
    return json.dumps(deployment_spec, indent=2)


def verify_css() -> dict:
    overlay = (ROOT / "static" / "css" / "camera_overlay.css").read_text(encoding="utf-8")
    full = (ROOT / "static" / "css" / "camera_full.css").read_text(encoding="utf-8")
    ok = (
        "bottom: calc(100% + 18px)" in overlay
        and "left: 50%" in overlay
        and "z-index: 15" in overlay
        and "bottom: calc(100% + 18px)" in full
    )
    return {"ok": ok}


if __name__ == "__main__":
    print(get_vertical_deployment_instruction())
    print(verify_css())
