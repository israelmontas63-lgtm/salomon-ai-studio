# -*- coding: utf-8 -*-
"""
[FILE: fix_jilo_camera_overlap.py] — Jilo (flip) sobre esquina superior derecha de cámara.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def calculate_jilo_overlay_position() -> str:
    overlay_specs = {
        "target_element": "Jilo_Button",
        "anchor_element": "Camera_Button",
        "layout_type": "absolute_positioning_overlap",
        "computed_offsets": {
            "top_offset_px": -12,
            "right_offset_px": -8,
            "z_index": 10,
        },
        "action": (
            "Force Jilo to stack directly over the top-right quadrant "
            "of the camera button without side-by-side spacing."
        ),
        "css": {
            "position": "absolute",
            "top": "-12px",
            "right": "-8px",
            "z-index": 10,
        },
    }
    return json.dumps(overlay_specs, indent=2)


def verify_css_applied() -> dict:
    overlay = (ROOT / "static" / "css" / "camera_overlay.css").read_text(encoding="utf-8")
    full = (ROOT / "static" / "css" / "camera_full.css").read_text(encoding="utf-8")
    ok = (
        "top: -12px" in overlay
        and "right: -8px" in overlay
        and "position: absolute" in overlay
        and "top: -12px" in full
        and "right: -8px" in full
    )
    return {"ok": ok, "files": ["camera_overlay.css", "camera_full.css"]}


if __name__ == "__main__":
    print(calculate_jilo_overlay_position())
    print(verify_css_applied())
