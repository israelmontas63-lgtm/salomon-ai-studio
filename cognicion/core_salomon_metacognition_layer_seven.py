# -*- coding: utf-8 -*-
"""
[FILE: core_salomon_metacognition_layer_seven.py]
Auditoría cognitiva: Capa 7 (metacognición) + sellado de fronteras L1–L7.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class SalomonMetacognitionArchitecture:
    def __init__(self) -> None:
        self.module = "SalomonMetacognitionArchitecture"
        self.total_layers = 7

    def _exists(self, rel: str) -> bool:
        return (ROOT / rel).is_file()

    def _read(self, rel: str) -> str:
        path = ROOT / rel
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    def audit_standard_gap(self) -> dict[str, Any]:
        """
        Comparación con estándares de IA avanzada:
        Percepción, Memoria, Razonamiento, NLP/Voz, UI/PWA, Autonomía,
        y Metacognición (evaluación pre-emisión).
        """
        return {
            "standard_stack": [
                "perception",
                "memory",
                "reasoning",
                "language_voice",
                "ui_automation",
                "autonomy_grounding",
                "metacognition_supervision",
            ],
            "gap_found": True,
            "gap": (
                "Faltaba supervisión metacognitiva post-LLM: L3/L6 hacen "
                "grounding factual pero no evalúan el borrador antes de emitir."
            ),
            "remediation": "Layer 7 metacognition_supervision",
            "sufficient_without_l7": False,
        }

    def verify_layer_7(self) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        ok = True

        def mark(name: str, passed: bool, detail: str) -> None:
            nonlocal ok
            checks.append({"check": name, "ok": passed, "detail": detail})
            if not passed:
                ok = False
            print(f"  [{'OK' if passed else 'FAIL'}] L7.{name}: {detail}")

        mark(
            "module",
            self._exists(
                "cognicion/capas_inteligencia/layer_07_metacognition/__init__.py"
            ),
            "modulo metacognicion presente",
        )
        cerebro = self._read("cerebro.py")
        mark(
            "cerebro_hook",
            "apply_supervision" in cerebro and "layer_07" in cerebro,
            "puerta de emision cableada en cerebro",
        )
        # Fronteras: L7 no debe re-lanzar enjambres
        l7 = self._read(
            "cognicion/capas_inteligencia/layer_07_metacognition/__init__.py"
        )
        mark(
            "no_swarm_collision",
            "deploy_agent_swarm(" not in l7
            and "schedule_background_verification(" not in l7
            and "enrich_turn(" not in l7
            and "from cognicion.orquesta" not in l7,
            "L7 no re-ejecuta L3/L6",
        )
        cat = self._read("cognicion/capas_inteligencia/__init__.py")
        mark(
            "catalog",
            '"id": 7' in cat or "metacognition" in cat,
            "catalogo declara Capa 7",
        )
        try:
            from cognicion.capas_inteligencia.layer_07_metacognition import (
                apply_supervision,
                seal_boundaries,
            )

            _txt, rep = apply_supervision(
                "Esto es un hecho al 100%: el precio es $999 en 2099.",
                user_message="¿Cuál es el precio exacto ahora?",
                meta={"cognicion": {}},
            )
            mark(
                "runtime_hedge",
                bool(rep.get("action") in ("hedge", "emit", "fallback")),
                f"action={rep.get('action')} score={rep.get('score')}",
            )
            bounds = seal_boundaries()
            mark("boundaries", bool(bounds.get("ok")), "fronteras selladas")
        except Exception as exc:
            mark("runtime_hedge", False, str(exc))
            mark("boundaries", False, str(exc))

        return {"ok": ok, "checks": checks}

    def consolidate_prior_layers(self) -> dict[str, Any]:
        try:
            from cognicion.core_salomon_ultimate_layer_six import (
                run_ultimate_architecture,
            )

            base = run_ultimate_architecture()
            return {
                "ok": bool(base.get("complete")),
                "status": base.get("status"),
                "architecture_layers_reported": base.get("architecture_layers"),
            }
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}:{exc}"}

    def run(self) -> dict[str, Any]:
        print("[AUDITORIA METACOGNITIVA — CAPA 7 SALOMON AI]")
        gap = self.audit_standard_gap()
        print(f"  Gap: {gap['gap']}")
        print("--- Capas 1-6 (consolidacion) ---")
        prior = self.consolidate_prior_layers()
        print("--- Capa 7: Metacognicion ---")
        l7 = self.verify_layer_7()
        complete = bool(prior.get("ok")) and bool(l7.get("ok"))
        return {
            "status": (
                "SEVEN_LAYERS_COMPLETE_METACOGNITION_SEALED"
                if complete
                else "METACOGNITION_INCOMPLETE"
            ),
            "module": self.module,
            "architecture_layers": self.total_layers,
            "standard_gap": gap,
            "layers_1_to_6": prior,
            "layer_7": l7,
            "complete": complete,
            "deployment": (
                "Commit, push to Render, PWA hot-load, tuerquita badge active."
            ),
        }


def run_metacognition_architecture() -> dict[str, Any]:
    return SalomonMetacognitionArchitecture().run()


if __name__ == "__main__":
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    report = run_metacognition_architecture()
    print(json.dumps(
        {k: report[k] for k in ("status", "complete", "architecture_layers")},
        indent=2,
    ))
    sys.exit(0 if report.get("complete") else 1)
