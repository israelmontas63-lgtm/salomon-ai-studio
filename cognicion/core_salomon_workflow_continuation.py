# -*- coding: utf-8 -*-
"""
[FILE: core_salomon_workflow_continuation.py]
Motor de Continuidad y Siguiente Capa (Salomón AI).
Valida componentes locked y avanza la capa de visión voz↔ojos.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class SalomonWorkflowContinuation:
    def __init__(self) -> None:
        self.module = "SalomonWorkflowContinuation"
        self.status = "READY_FOR_NEXT_LAYER"
        self.next_layer = "vision_voice_bridge_macro_micro"

    def _read(self, rel: str) -> str:
        path = ROOT / rel
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    def verify_locked_components(self) -> dict[str, Any]:
        """Componentes locked: seamless button + PWA hot-loader/badge."""
        btn = self._read("static/js/components/SmartButton.js")
        css = self._read("static/css/boton.css")
        upd = self._read("static/js/update_manager.js")
        badge = self._read("static/js/realtime_notification_badge.js")

        seamless_ok = (
            "HOLD_MS" in btn
            and "500" in btn
            and "DICTATION" in btn
            and "CONVERSATIONAL" in btn
            and "neutralize" in btn
            and "is-seamless" in css
        )
        pwa_ok = (
            "hotPatch" in upd
            and "deploy-notify" in upd
            and "SalomonDeployBadge" in badge
            and "deploy-badge" in badge
        )
        return {
            "seamless_smart_button": seamless_ok,
            "pwa_hotloader_badge": pwa_ok,
            "ok": seamless_ok and pwa_ok,
        }

    def verify_next_layer(self) -> dict[str, Any]:
        """Siguiente capa: puente voz→visión (autofocus + frame + TTS bridge)."""
        lock_js = self._read("static/js/ai_state_lock.js")
        vision_js = self._read("static/js/vision_engine.js")
        cam_js = self._read("static/js/camera_logic.js")

        voice_bridge = (
            "prepareVisionPayload" in lock_js
            or "handleChatCommand" in lock_js
            or "autoFocusFromText" in lock_js
        )
        tts_bridge = "audio_base64" in vision_js and "new Audio" in vision_js
        zoom_class = "is-zoom-micro" in cam_js and "focusMode" in cam_js
        parse_tight = "enfoque micro" in vision_js or "\\bmicro\\b" in vision_js

        return {
            "layer": self.next_layer,
            "voice_vision_bridge": voice_bridge,
            "vision_tts_playback": tts_bridge,
            "zoom_class_by_mode": zoom_class,
            "ok": voice_bridge and tts_bridge,
            "parse_commands": parse_tight,
        }

    def compile_continuation_spec(self) -> str:
        locked = self.verify_locked_components()
        nxt = self.verify_next_layer()
        status = (
            "STABLE_NEXT_LAYER_READY"
            if locked.get("ok")
            else "LOCKED_COMPONENTS_UNSTABLE"
        )
        spec = {
            "action": (
                "Proceed to the next development layer while keeping existing "
                "components stable."
            ),
            "status": status,
            "components_locked": [
                "Seamless Smart Action Button (Tap / Long Press / Neutralizer)",
                "PWA Hot-Loader & Settings Gear Badge Notification",
            ],
            "locked_verification": locked,
            "next_layer": {
                "id": self.next_layer,
                "focus": "Vision macro/micro voice bridge + TTS on brain-bridge",
                "verification": nxt,
            },
            "deployment": (
                "Auto-commit, git push to Render production, and hot-patch PWA."
            ),
        }
        return json.dumps(spec, indent=2)

    def run(self) -> dict[str, Any]:
        return json.loads(self.compile_continuation_spec())


def run_workflow_continuation() -> dict[str, Any]:
    return SalomonWorkflowContinuation().run()


if __name__ == "__main__":
    workflow = SalomonWorkflowContinuation()
    print("[INICIANDO SIGUIENTE FASE DE DESARROLLO DE SALOMON AI]")
    print(workflow.compile_continuation_spec())
