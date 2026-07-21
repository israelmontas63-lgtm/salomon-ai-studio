# -*- coding: utf-8 -*-
"""
[FILE: core_salomon_neural_isolation_and_voice_vision_bridge.py]
Aislamiento neuronal + puente voz-visión en tiempo real.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class SalomonNeuralIsolationAndBridge:
    def __init__(self) -> None:
        self.module = "SalomonNeuralIsolationAndBridge"
        self.status = "MODULAR_CONTRACTS_AND_VOICE_VISION_ACTIVE"

    def _read(self, rel: str) -> str:
        path = ROOT / rel
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    def run_isolation_guard(self) -> dict[str, Any]:
        from cognicion.capas_inteligencia.layer_contracts import verify_contracts
        from cognicion.capas_inteligencia.neural_core_bridge import harmonize_all_layers

        contracts = verify_contracts()
        bridges = harmonize_all_layers()
        ok = bool(contracts.get("ok")) and bool(bridges.get("sealed"))
        return {
            "ok": ok,
            "blocked": not ok,
            "contracts": contracts,
            "bridges": {
                "sealed": bridges.get("sealed"),
                "core_links": bridges.get("core_links"),
            },
        }

    def audit_voice_vision_bridge(self) -> dict[str, Any]:
        ve = self._read("static/js/vision_engine.js")
        trigger = self._read("cognicion/core_vision_mode_trigger.py")
        checks = [
            ("standby_mode", "standby" in ve and "analyticalStreaming" in ve),
            ("engage_api", "engageAnalyticalStreaming" in ve),
            ("disengage_api", "disengageVisualMode" in ve),
            ("no_auto_brain_on_capture", "sendFrameToBrain" not in ve.split("camera-capture")[1][:400] if "camera-capture" in ve else False),
            ("ver_frente_cmd", "ver_frente" in ve and "es_comando_ver_frente" in trigger),
            ("desactivar_cmd", "desactivar_visual" in ve and "es_comando_desactivar_visual" in trigger),
            ("session_sync", "setSessionId" in self._read("static/js/ai_state_lock.js")),
        ]
        # Soft check: capture handler must not call sendFrameToBrain
        cap_idx = ve.find("salomon:camera-capture")
        if cap_idx >= 0:
            chunk = ve[cap_idx : cap_idx + 500]
            checks[3] = ("no_auto_brain_on_capture", "sendFrameToBrain" not in chunk)

        results = [{"check": n, "ok": ok} for n, ok in checks]
        for c in results:
            print(f"  [{'OK' if c['ok'] else 'FAIL'}] VV.{c['check']}")
        return {"ok": all(c["ok"] for c in results), "checks": results}

    def compile_architectural_spec(self) -> str:
        print(
            "[COMPILANDO ARQUITECTURA DE AISLAMIENTO NEURONAL Y PUENTE MULTIMODAL - SALOMON AI]"
        )
        iso = self.run_isolation_guard()
        print("--- Aislamiento de capas ---")
        print(f"  contracts={iso['contracts'].get('ok')} bridges={iso['bridges'].get('sealed')}")
        print("--- Puente voz-vision ---")
        vv = self.audit_voice_vision_bridge()
        complete = bool(iso.get("ok")) and bool(vv.get("ok"))
        spec = {
            "action": (
                "Deploy strict layer-isolation contracts to prevent regression, "
                "alongside voice-triggered continuous vision streaming."
            ),
            "module": self.module,
            "status": self.status if complete else "ARCHITECTURE_INCOMPLETE",
            "components": [
                "Layer Isolation & Regression Guardrails",
                "Voice-Triggered Vision (Streaming Active / Standby)",
                "Session State & Persistent Data Protection",
            ],
            "isolation": iso,
            "voice_vision": vv,
            "complete": complete,
            "guard_script": "scripts/check_layer_isolation.py",
            "deployment": (
                "Auto-commit, git push to Render production, PWA update, "
                "and settings badge active."
            ),
        }
        print(json.dumps({"status": spec["status"], "complete": complete}, indent=2))
        return json.dumps(spec, indent=2, ensure_ascii=True)

    def run(self) -> dict[str, Any]:
        return json.loads(self.compile_architectural_spec())


def run_neural_isolation_bridge() -> dict[str, Any]:
    return SalomonNeuralIsolationAndBridge().run()


if __name__ == "__main__":
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    report = run_neural_isolation_bridge()
    sys.exit(0 if report.get("complete") else 1)
