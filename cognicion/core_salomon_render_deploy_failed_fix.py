# -*- coding: utf-8 -*-
"""
[FILE: core_salomon_render_deploy_failed_fix.py]
Diagnóstico y corrección de fallo de despliegue en Render.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

CRITICAL = [
    "app.py",
    "cerebro.py",
    "settings.py",
    "cognicion/capas_inteligencia/synaptic_bus.py",
    "cognicion/capas_inteligencia/layer_contracts.py",
    "cognicion/core_salomon_synaptic_contracts_and_layer_isolation.py",
    "cognicion/core_salomon_neural_isolation_and_voice_vision_bridge.py",
    "persistencia/sesiones.py",
    "scripts/check_layer_isolation.py",
]


class SalomonRenderDeployFix:
    def __init__(self) -> None:
        self.module = "SalomonRenderDeployFix"
        self.status = "DIAGNOSTIC_AND_FIX_ACTIVE"

    def diagnose_commit_ref(self, ref: str = "b82d71f") -> dict[str, Any]:
        """El ref del panel Render puede no coincidir con un commit git local."""
        import subprocess

        found = False
        tip = ""
        try:
            tip = subprocess.check_output(
                ["git", "rev-parse", "--short=12", "HEAD"],
                cwd=str(ROOT),
                text=True,
            ).strip()
            subprocess.check_output(
                ["git", "rev-parse", "--verify", ref],
                cwd=str(ROOT),
                stderr=subprocess.DEVNULL,
            )
            found = True
        except Exception:
            found = False
        return {
            "requested_ref": ref,
            "found_in_repo": found,
            "local_tip": tip,
            "note": (
                "Si el ref no existe en git, suele ser un deploy ID de Render "
                "o un commit de otro branch; validar tip actual y boot."
            ),
        }

    def compile_critical(self) -> dict[str, Any]:
        errors: list[dict[str, str]] = []
        ok_files: list[str] = []
        for rel in CRITICAL:
            path = ROOT / rel
            if not path.is_file():
                errors.append({"file": rel, "error": "missing"})
                continue
            try:
                src = path.read_text(encoding="utf-8")
                ast.parse(src)
                # Solo AST (py_compile a temp falla en Windows por permisos)
                ok_files.append(rel)
            except Exception as exc:
                errors.append({"file": rel, "error": f"{type(exc).__name__}:{exc}"})
        return {
            "ok": not errors,
            "ok_files": ok_files,
            "errors": errors,
        }

    def import_smoke(self) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        try:
            from cognicion.capas_inteligencia.synaptic_bus import list_synapses

            checks.append({"check": "synaptic_bus", "ok": True, "n": len(list_synapses())})
        except Exception as exc:
            checks.append({"check": "synaptic_bus", "ok": False, "error": str(exc)})
        try:
            from cognicion.eficiencia import estado_eficiencia

            st = estado_eficiencia()
            checks.append({"check": "eficiencia", "ok": True, "version": st.get("version")})
        except Exception as exc:
            checks.append({"check": "eficiencia", "ok": False, "error": str(exc)})
        try:
            import app as _app  # noqa: F401

            checks.append({"check": "import_app", "ok": True})
        except Exception as exc:
            checks.append({"check": "import_app", "ok": False, "error": str(exc)})
        return {"ok": all(c.get("ok") for c in checks), "checks": checks}

    def compile_fix_spec(self) -> str:
        print("[EJECUTANDO DIAGNOSTICO DE FALLO EN RENDER - SALOMON AI]")
        ref = self.diagnose_commit_ref("b82d71f")
        print(f"  ref b82d71f found={ref['found_in_repo']} tip={ref['local_tip']}")
        print("--- compile critical ---")
        comp = self.compile_critical()
        for e in comp.get("errors") or []:
            print(f"  FAIL {e}")
        print("--- import smoke ---")
        smoke = self.import_smoke()
        for c in smoke.get("checks") or []:
            print(f"  [{'OK' if c.get('ok') else 'FAIL'}] {c.get('check')}")
        complete = bool(comp.get("ok")) and bool(smoke.get("ok"))
        spec = {
            "action": (
                "Diagnose render failed deployment log, fix dependency/syntax "
                "errors, and push a clean green build."
            ),
            "module": self.module,
            "status": "RENDER_BOOT_VERIFIED" if complete else "RENDER_FIX_NEEDED",
            "target": "Restore server state to Live production.",
            "ref_diagnosis": ref,
            "compile": comp,
            "smoke": smoke,
            "complete": complete,
            "production_probe_hint": (
                "Live tip should serve /api/salud with live=true and matching build."
            ),
            "deployment": (
                "Auto-commit, push to Render production, PWA update, "
                "and settings badge active."
            ),
        }
        print(json.dumps({"status": spec["status"], "complete": complete}, indent=2))
        return json.dumps(spec, indent=2, ensure_ascii=True)

    def run(self) -> dict[str, Any]:
        return json.loads(self.compile_fix_spec())


def run_render_deploy_fix() -> dict[str, Any]:
    return SalomonRenderDeployFix().run()


if __name__ == "__main__":
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    report = run_render_deploy_fix()
    sys.exit(0 if report.get("complete") else 1)
