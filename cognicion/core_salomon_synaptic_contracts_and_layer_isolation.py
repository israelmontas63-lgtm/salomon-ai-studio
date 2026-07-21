# -*- coding: utf-8 -*-
"""
[FILE: core_salomon_synaptic_contracts_and_layer_isolation.py]
Motor de contratos sinápticos y aislamiento por capas (modo estricto).
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class SalomonSynapticArchitectEngine:
    def __init__(self) -> None:
        self.module = "SalomonSynapticArchitectEngine"
        self.status = "SYNAPTIC_CONTRACTS_STRICT_MODE_ACTIVE"

    def _read(self, rel: str) -> str:
        path = ROOT / rel
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    def verify_synaptic_bus(self) -> dict[str, Any]:
        from cognicion.capas_inteligencia.synaptic_bus import (
            cement_imagen_payload,
            cement_session_id,
            cement_turn_roles,
            list_synapses,
            synapse_allowed,
        )

        checks: list[dict[str, Any]] = []
        ok = True

        def mark(name: str, passed: bool, detail: str = "") -> None:
            nonlocal ok
            checks.append({"check": name, "ok": passed, "detail": detail})
            if not passed:
                ok = False
            print(f"  [{'OK' if passed else 'FAIL'}] SYN.{name}: {detail}")

        synapses = list_synapses()
        mark("registry", len(synapses) >= 5, f"canales={len(synapses)}")
        mark(
            "voice_to_vision",
            synapse_allowed(4, 1, "voice_triggered_vision"),
            "L4->L1 autorizado",
        )
        mark(
            "vision_no_direct_sqlite",
            not synapse_allowed(1, 2, "persist_turn"),
            "L1 no escribe memoria directa",
        )
        mark(
            "memory_to_reason",
            synapse_allowed(2, 3, "memory_immediate"),
            "L2->L3 memoria inmediata",
        )

        try:
            assert cement_session_id("  abc  ") == "abc"
            assert cement_session_id("") is None
            assert cement_session_id(None) is None
            mark("cement_session", True, "session_id tipado")
        except Exception as exc:
            mark("cement_session", False, str(exc))

        try:
            pack = cement_imagen_payload("aaa", "image/jpeg")
            assert pack["ok"] is True
            cement_turn_roles("usuario")
            mark("cement_payloads", True, "imagen+rol tipados")
        except Exception as exc:
            mark("cement_payloads", False, str(exc))

        # Antisabotaje: visión no llama guardar_mensaje
        ve = self._read("static/js/vision_engine.js")
        mark(
            "vision_no_guardar_mensaje",
            "guardar_mensaje" not in ve,
            "visión aislada de SQLite",
        )
        ses = self._read("persistencia/sesiones.py")
        mark(
            "sqlite_wal_atomic",
            "journal_mode=WAL" in ses and "BEGIN IMMEDIATE" in ses,
            "memoria atómica",
        )
        gestor = self._read("cognicion/memoria/gestor.py")
        mark("memory_16_turns", "limite: int = 16" in gestor, "ventana 16")
        mark(
            "vision_standby_router",
            "analyticalStreaming" in ve and "engageAnalyticalStreaming" in ve,
            "standby/analítico",
        )
        l7 = self._read(
            "cognicion/capas_inteligencia/layer_07_metacognition/__init__.py"
        )
        mark(
            "l7_no_swarm",
            "deploy_agent_swarm(" not in l7,
            "metacognición no re-lanza enjambre",
        )

        return {"ok": ok, "checks": checks, "synapses": len(synapses)}

    def run_full_isolation(self) -> dict[str, Any]:
        from cognicion.capas_inteligencia.layer_contracts import verify_contracts
        from cognicion.capas_inteligencia.neural_core_bridge import harmonize_all_layers

        contracts = verify_contracts()
        bridges = harmonize_all_layers()
        return {
            "ok": bool(contracts.get("ok")) and bool(bridges.get("sealed")),
            "contracts_ok": contracts.get("ok"),
            "bridges_sealed": bridges.get("sealed"),
            "failed": [f for f in (contracts.get("findings") or []) if not f.get("ok")],
        }

    def compile_synaptic_spec(self) -> str:
        print("[COMPILANDO ARQUITECTURA DE CONTRATOS SINAPTICOS - SALOMON AI]")
        print("--- Sinapsis y cemento ---")
        syn = self.verify_synaptic_bus()
        print("--- Aislamiento de capas ---")
        iso = self.run_full_isolation()
        print(
            f"  contracts={iso.get('contracts_ok')} bridges={iso.get('bridges_sealed')}"
        )
        complete = bool(syn.get("ok")) and bool(iso.get("ok"))
        spec = {
            "action": (
                "Enforce strict synaptic contract boundaries across all neural "
                "layers to prevent cross-module corruption and regressions."
            ),
            "module": self.module,
            "status": self.status if complete else "SYNAPTIC_STRICT_INCOMPLETE",
            "components": [
                "Layer Isolation & Interface Contracts",
                "Atomic SQLite WAL Memory (16-turn context)",
                "Voice-Triggered Vision Standby Router",
            ],
            "synaptic": syn,
            "isolation": iso,
            "complete": complete,
            "antisabotage": "scripts/check_layer_isolation.py",
            "deployment": (
                "Auto-commit, push to Render production, PWA update, "
                "and settings badge active."
            ),
        }
        print(json.dumps({"status": spec["status"], "complete": complete}, indent=2))
        return json.dumps(spec, indent=2, ensure_ascii=True)

    def run(self) -> dict[str, Any]:
        return json.loads(self.compile_synaptic_spec())


def run_synaptic_architect() -> dict[str, Any]:
    return SalomonSynapticArchitectEngine().run()


if __name__ == "__main__":
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    report = run_synaptic_architect()
    sys.exit(0 if report.get("complete") else 1)
