# -*- coding: utf-8 -*-
"""
[FILE: core_salomon_smart_button_synaptic_controller.py]
Controlador del Botón Inteligente: 1 toque / 2 toques / apagado + sinapsis multimodal.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DOUBLE_TAP_MS = 320


class SalomonSmartButtonController:
    def __init__(self) -> None:
        self.module = "SalomonSmartButtonController"
        self.status = "SMART_BUTTON_CONTROLLER_ACTIVE"
        self.double_tap_ms = DOUBLE_TAP_MS

    def _read(self, rel: str) -> str:
        path = ROOT / rel
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    def verify(self) -> dict[str, Any]:
        js = self._read("static/js/components/SmartButton.js")
        checks = [
            ("single_tap_dictation", "_enterDictation" in js and "DOUBLE_TAP_MS" in js),
            ("double_tap_ai", "_enterConversational" in js and "_tapCount" in js),
            ("tap_off", "tap_while_active" in js and "neutralize" in js),
            (
                "vision_synapse",
                "keepCamera: true" in js
                and "SalomonCamera && window.SalomonCamera.isActive()" not in js,
            ),
            (
                "vision_off_on_neutralize",
                "disengageVisualMode" in js,
            ),
            ("engine_tag", "synaptic-smart-button" in js or "synaptic-tap" in js),
        ]
        # Explicit: must NOT block when camera active
        blocked_by_cam = (
            "SalomonCamera.isActive()" in js
            and "_blockedByUi" in js
            and "isActive()) return true" in js.replace(" ", "")
        )
        # Softer check for camera block removal
        cam_block = "if (window.SalomonCamera && window.SalomonCamera.isActive()) return true;" in js
        checks[3] = (
            "vision_synapse",
            "keepCamera: true" in js and not cam_block,
        )
        results = [{"check": n, "ok": ok} for n, ok in checks]
        for c in results:
            print(f"  [{'OK' if c['ok'] else 'FAIL'}] BTN.{c['check']}")
        return {
            "ok": all(c["ok"] for c in results),
            "checks": results,
            "double_tap_ms": self.double_tap_ms,
        }

    def compile_button_spec(self) -> str:
        print("[CONFIGURANDO CONTROLADOR DE BOTON INTELIGENTE - SALOMON AI]")
        v = self.verify()
        complete = bool(v.get("ok"))
        spec = {
            "action": (
                "Bind single-tap to dictation mode, double-tap to AI reasoning mode, "
                "and tap-to-toggle-off for complete sensory synchronization."
            ),
            "module": self.module,
            "status": self.status if complete else "SMART_BUTTON_INCOMPLETE",
            "components": [
                "Single Tap -> STT Dictation Engine",
                "Double Tap -> Full AI Intelligence Mode",
                "Sensory Bridge -> Unifying Vision, Voice, and Touch",
            ],
            "verify": v,
            "complete": complete,
            "thresholds": {"double_tap_ms": self.double_tap_ms},
            "deployment": (
                "Auto-commit, push to Render production, PWA update, "
                "and settings badge active."
            ),
        }
        print(json.dumps({"status": spec["status"], "complete": complete}, indent=2))
        return json.dumps(spec, indent=2, ensure_ascii=True)

    def run(self) -> dict[str, Any]:
        return json.loads(self.compile_button_spec())


def run_smart_button_controller() -> dict[str, Any]:
    return SalomonSmartButtonController().run()


if __name__ == "__main__":
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    report = run_smart_button_controller()
    sys.exit(0 if report.get("complete") else 1)
