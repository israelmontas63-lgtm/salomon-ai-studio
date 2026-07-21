# -*- coding: utf-8 -*-
"""
[FILE: core_salomon_cursor_challenge_and_autonomous_audit.py]
Motor de Reto y Auditoría Autónoma — consolida hitos de producción de Salomón AI.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

MILESTONE_DEFS: list[dict[str, Any]] = [
    {
        "id": "M1_modular_layers",
        "title": "Modular cognitive schema migration and isolated layer design",
        "evidence": [
            "cognicion/capas_inteligencia/__init__.py",
            "cognicion/capas_inteligencia/layer_contracts.py",
            "cognicion/capas_inteligencia/synaptic_bus.py",
            "cognicion/capas_inteligencia/neural_core_bridge.py",
            "cognicion/capas_inteligencia/layer_07_metacognition/__init__.py",
            "cognicion/core_salomon_supreme_supervisor_and_web_intelligence.py",
        ],
        "must_contain": {
            "cognicion/capas_inteligencia/__init__.py": ['"id": 7', "LAYER_CATALOG"],
            "cognicion/capas_inteligencia/synaptic_bus.py": [
                "AUTHORIZED_SYNAPSES",
                "cement_session_id",
            ],
            "cognicion/capas_inteligencia/layer_contracts.py": ["must_not_contain"],
        },
    },
    {
        "id": "M2_render_persistence",
        "title": "Persistent cloud storage deployment on Render with automated versioning",
        "evidence": [
            "settings.py",
            "render.yaml",
            "version.json",
            "static/js/update_manager.js",
            "static/js/realtime_notification_badge.js",
            "static/js/service-worker.js",
        ],
        "must_contain": {
            "settings.py": ['getenv("DATA_DIR"', 'getenv("SESIONES_DB"'],
            "render.yaml": ["DATA_DIR", "healthCheckPath"],
            "version.json": ['"version"', '"channel"'],
            "static/js/realtime_notification_badge.js": ["SalomonDeployBadge"],
        },
    },
    {
        "id": "M3_multimodal_sync",
        "title": (
            "Synchronized multimodal pipelines "
            "(SQLite WAL memory, voice/audio bridge, and vision standby)"
        ),
        "evidence": [
            "persistencia/sesiones.py",
            "cognicion/memoria/gestor.py",
            "static/js/voice_layer.js",
            "static/js/vision_engine.js",
            "static/js/components/SmartButton.js",
        ],
        "must_contain": {
            "persistencia/sesiones.py": ["journal_mode=WAL", "BEGIN IMMEDIATE"],
            "cognicion/memoria/gestor.py": ["limite: int = 16"],
            "static/js/voice_layer.js": ["SalomonVoiceLayer", "unlockReplay"],
            "static/js/vision_engine.js": [
                "analyticalStreaming",
                "engageAnalyticalStreaming",
                "standby",
            ],
            "static/js/components/SmartButton.js": [
                "DOUBLE_TAP_MS",
                "keepCamera: true",
                "disengageVisualMode",
            ],
        },
    },
]


class SalomonCursorChallengeAudit:
    def __init__(self) -> None:
        self.module = "SalomonCursorChallengeAudit"
        self.status = "CHALLENGE_MODE_ACTIVE"
        self.ledger_path = ROOT / "data" / "salomon_autonomous_milestones.json"

    def _read(self, rel: str) -> str:
        path = ROOT / rel
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    def _exists(self, rel: str) -> bool:
        return (ROOT / rel).is_file()

    def verify_milestone(self, milestone: dict[str, Any]) -> dict[str, Any]:
        missing = [e for e in milestone["evidence"] if not self._exists(e)]
        needle_fails: list[dict[str, str]] = []
        for rel, needles in (milestone.get("must_contain") or {}).items():
            body = self._read(rel)
            for needle in needles:
                if needle not in body:
                    needle_fails.append({"file": rel, "needle": needle})
        ok = not missing and not needle_fails
        return {
            "id": milestone["id"],
            "title": milestone["title"],
            "ok": ok,
            "missing_files": missing,
            "needle_fails": needle_fails,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    def run_supervisor_crosscheck(self) -> dict[str, Any]:
        try:
            from cognicion.core_salomon_supreme_supervisor_and_web_intelligence import (
                run_supreme_supervisor,
            )

            pack = run_supreme_supervisor()
            return {
                "ok": bool(pack.get("complete")),
                "status": pack.get("status"),
            }
        except Exception as exc:
            return {"ok": False, "error": type(exc).__name__}

    def write_ledger(self, payload: dict[str, Any]) -> str:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        return str(self.ledger_path.relative_to(ROOT)).replace("\\", "/")

    def compile_challenge_spec(self) -> str:
        print("[EJECUTANDO AUDITORIA DE RETO Y CAPACIDAD AUTONOMA - SALOMON AI]")
        results = [self.verify_milestone(m) for m in MILESTONE_DEFS]
        for r in results:
            print(f"  [{'OK' if r['ok'] else 'FAIL'}] {r['id']}: {r['title'][:64]}")
            for nf in r.get("needle_fails") or []:
                print(f"      missing {nf['file']} :: {nf['needle']}")

        print("--- crosscheck supervisor ---")
        cross = self.run_supervisor_crosscheck()
        print(f"  supervisor={cross.get('ok')} status={cross.get('status')}")

        milestones_ok = all(r["ok"] for r in results)
        complete = milestones_ok and bool(cross.get("ok"))
        ledger = {
            "module": self.module,
            "status": (
                "CHALLENGE_PASSED_ELITE_PRODUCTION"
                if complete
                else "CHALLENGE_INCOMPLETE"
            ),
            "protocol": "CURSOR_CHALLENGE_AUTONOMOUS_AUDIT",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "milestones": results,
            "supervisor_crosscheck": cross,
            "complete": complete,
            "git_tip_hint": "See git log on main for production commits",
            "deployment": (
                "Auto-commit, push to Render production, PWA update, "
                "and settings badge active."
            ),
        }
        path = self.write_ledger(ledger)
        ledger["ledger_path"] = path
        print(json.dumps({"status": ledger["status"], "complete": complete, "ledger": path}, indent=2))
        return json.dumps(ledger, indent=2, ensure_ascii=True)

    def run(self) -> dict[str, Any]:
        return json.loads(self.compile_challenge_spec())


def run_cursor_challenge_audit() -> dict[str, Any]:
    return SalomonCursorChallengeAudit().run()


if __name__ == "__main__":
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    report = run_cursor_challenge_audit()
    sys.exit(0 if report.get("complete") else 1)
