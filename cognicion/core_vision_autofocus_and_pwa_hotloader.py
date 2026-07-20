# -*- coding: utf-8 -*-
"""
[FILE: core_vision_autofocus_and_pwa_hotloader.py]
Motor de Enfoque Automático/Macro-Micro y Hot-Loader PWA (Salomón AI).
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# micro = detalle cercano (letra) | macro = objeto lejano (roca allá)
_RE_MICRO = re.compile(
    r"(?i)\b("
    r"micro|"
    r"letra|texto|detalle|peque[nñ]o|"
    r"cerca|aqu[ií]\s+mismo|ah[ií]\s+mismo|"
    r"zoom\s+cerca|enfoque\s+cerca|macro\s+cerca"
    r")\b"
)
_RE_MACRO = re.compile(
    r"(?i)\b("
    r"macro|"
    r"lejos|all[aá]|aquella|aquel|"
    r"roca|monta[nñ]a|horizonte|"
    r"objeto\s+lejano|enfoque\s+lejano|"
    r"zoom\s+lejos|distant"
    r")\b"
)


class VisionAutofocusAndPWAUpdater:
    def __init__(self) -> None:
        self.module = "VisionAutofocusAndPWAUpdater"
        self.target_platform = "PWA Web/Mobile"

    def compile_master_spec(self) -> str:
        spec = {
            "vision_autofocus": {
                "modes": ["macro", "micro", "distant_object_zoom"],
                "trigger_sources": ["verbal_command", "automatic_screen_detection"],
                "action": (
                    "Dynamic focal length and zoom adjustment for fine text "
                    "or distant objects."
                ),
                "mapping": {
                    "micro": "close_detail_near_focus_zoom",
                    "macro": "distant_object_digital_zoom",
                },
            },
            "pwa_hot_loader_and_notification": {
                "update_pipeline": (
                    "Automatic background package fetch from deployment directory"
                ),
                "package_markers": ["/api/version", "/version.json"],
                "notification_trigger": (
                    "Instant badge alert next to settings gear ('la tuerquita')"
                ),
                "execution": "Zero friction, auto-pull on every successful deployment.",
            },
            "assets": {
                "camera": "static/js/camera_logic.js",
                "vision": "static/js/vision_engine.js",
                "update": "static/js/update_manager.js",
                "badge": "static/js/realtime_notification_badge.js",
                "sw": "static/js/service-worker.js",
            },
            "deployment": "Auto-commit and push to Render production.",
        }
        return json.dumps(spec, indent=2)

    def infer_focus_mode(self, mensaje: str) -> str | None:
        return infer_focus_mode(mensaje)

    def verify(self) -> dict[str, Any]:
        cam = (ROOT / "static" / "js" / "camera_logic.js").read_text(encoding="utf-8")
        upd = (ROOT / "static" / "js" / "update_manager.js").read_text(encoding="utf-8")
        return {
            "ok": "setZoom" in cam and "hotPatch" in upd and "deploy-notify" in upd,
            "module": self.module,
            "platform": self.target_platform,
        }


def infer_focus_mode(mensaje: str) -> str | None:
    """Devuelve 'micro' | 'macro' | None según el texto."""
    t = mensaje or ""
    micro = bool(_RE_MICRO.search(t))
    macro = bool(_RE_MACRO.search(t))
    if micro and not macro:
        return "micro"
    if macro and not micro:
        return "macro"
    if micro and macro:
        # Prioridad: “letra/cerca” gana si ambos
        if re.search(r"(?i)\b(letra|texto|cerca|ah[ií]\s+mismo)\b", t):
            return "micro"
        return "macro"
    return None


def obtener_autofocus_engine() -> VisionAutofocusAndPWAUpdater:
    return VisionAutofocusAndPWAUpdater()


if __name__ == "__main__":
    engine = VisionAutofocusAndPWAUpdater()
    print(engine.compile_master_spec())
    print(engine.verify())
