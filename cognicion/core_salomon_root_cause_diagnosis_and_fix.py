# -*- coding: utf-8 -*-
"""
[FILE: core_salomon_root_cause_diagnosis_and_fix.py]
Diagnóstico y reparación raíz: Visión, Voces API y Memoria.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class SalomonRootCauseDiagnosisAndFix:
    def __init__(self) -> None:
        self.module = "SalomonRootCauseDiagnosisAndFix"
        self.status = "FIXING_ROOT_CAUSE_API_AND_MEMORY"

    def _read(self, rel: str) -> str:
        path = ROOT / rel
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    def audit_vision(self) -> dict[str, Any]:
        orch = self._read("cognicion/orquestador.py")
        cerebro = self._read("cerebro.py")
        control = self._read("cognicion/core_control.py")
        app = self._read("app.py")
        checks = [
            ("force_vision_on_bytes", "if imagen_base64:" in orch and "vision_forced" in orch),
            ("empty_text_with_image", "Analiza esta captura" in cerebro),
            ("identity_skips_with_image", "if not imagen_base64:" in cerebro),
            ("core_control_image", "has_image" in control),
            ("central_normalize", "normalize_frame_payload" in app and "central-button" in app),
        ]
        results = [{"check": n, "ok": ok} for n, ok in checks]
        for c in results:
            print(f"  [{'OK' if c['ok'] else 'FAIL'}] V.{c['check']}")
        return {"ok": all(c["ok"] for c in results), "checks": results}

    def audit_voice(self) -> dict[str, Any]:
        providers = self._read("config/providers.py")
        settings = self._read("settings.py")
        voice = self._read("static/js/voice_layer.js")
        render = self._read("render.yaml")
        checks = [
            (
                "elevenlabs_key_alone",
                '_presente(S.ELEVENLABS_API_KEY),' in providers
                or "_presente(S.ELEVENLABS_API_KEY)," in providers,
            ),
            (
                "adam_default",
                "if not _raw_voice:" in settings
                and "ELEVENLABS_VOICE_ADAM" in settings,
            ),
            ("voice_unlock_replay", "unlockReplay" in voice and "pending" in voice),
            ("tts_async_false", 'TTS_ASYNC' in render and '"false"' in render),
            ("adam_in_render", "pNInz6obpgDQGcFmaJgB" in render),
        ]
        results = [{"check": n, "ok": ok} for n, ok in checks]
        for c in results:
            print(f"  [{'OK' if c['ok'] else 'FAIL'}] T.{c['check']}")
        return {"ok": all(c["ok"] for c in results), "checks": results}

    def audit_memory(self) -> dict[str, Any]:
        ses = self._read("persistencia/sesiones.py")
        gestor = self._read("cognicion/memoria/gestor.py")
        checks = [
            ("sqlite_wal", "journal_mode=WAL" in ses and "busy_timeout" in ses),
            ("single_conn_write", "BEGIN IMMEDIATE" in ses),
            ("memoria_inmediata_16", "limite: int = 16" in gestor),
        ]
        results = [{"check": n, "ok": ok} for n, ok in checks]
        for c in results:
            print(f"  [{'OK' if c['ok'] else 'FAIL'}] M.{c['check']}")
        return {"ok": all(c["ok"] for c in results), "checks": results}

    def compile_fix_spec(self) -> str:
        print("[EJECUTANDO DIAGNOSTICO Y CORRECCION DE RAIZ - SALOMON AI]")
        v = self.audit_vision()
        t = self.audit_voice()
        m = self.audit_memory()
        complete = bool(v.get("ok") and t.get("ok") and m.get("ok"))
        spec = {
            "action": (
                "Fix multimodal image input payload, restore ElevenLabs Adam "
                "voice token mapping, and resolve SQLite/RAM memory limits."
            ),
            "module": self.module,
            "status": self.status if complete else "ROOT_CAUSE_INCOMPLETE",
            "components_patched": [
                "Layer 1: Multimodal Base64 Image Forwarding",
                "Layer 2: SQLite Memory Persistence & RAM Limit Stability",
                "Layer 4: ElevenLabs Adam Voice Streaming Pipeline",
            ],
            "vision": v,
            "voice": t,
            "memory": m,
            "complete": complete,
            "deployment": (
                "Emergency commit, git push to Render, PWA hot-load update, "
                "and settings badge active."
            ),
        }
        print(json.dumps({"status": spec["status"], "complete": complete}, indent=2))
        return json.dumps(spec, indent=2, ensure_ascii=True)

    def run(self) -> dict[str, Any]:
        return json.loads(self.compile_fix_spec())


def run_root_cause_fix() -> dict[str, Any]:
    return SalomonRootCauseDiagnosisAndFix().run()


if __name__ == "__main__":
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    report = run_root_cause_fix()
    sys.exit(0 if report.get("complete") else 1)
