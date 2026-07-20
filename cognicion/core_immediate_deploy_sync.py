# -*- coding: utf-8 -*-
"""
[FILE: core_immediate_deploy_sync.py] — Despliegue Automatizado y Validación Total
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class ImmediateDeployEngine:
    """
    Centrado de botón, validación de capas y señal de listo para commit/push.
    (El push lo ejecuta el agente Cursor en el mismo pipeline.)
    """

    def __init__(self) -> None:
        self.target_actions = [
            "1. Forzar centrado absoluto del boton inteligente en la barra inferior.",
            "2. Auditar el aislamiento estricto de capas (Vision, Conciencia UI, Memoria).",
            "3. Ejecutar git add, git commit y git push automaticos hacia el servidor.",
        ]

    def _verify_centering(self) -> dict[str, Any]:
        boton = (ROOT / "static" / "css" / "boton.css").read_text(encoding="utf-8")
        styles = (ROOT / "static" / "css" / "styles.css").read_text(encoding="utf-8")
        ok = "1fr auto 1fr" in boton and "1fr auto 1fr" in styles
        ok = ok and "grid-column: 2" in boton and "margin: 0 !important" in boton
        return {"ok": ok, "method": "CSS Grid 1fr auto 1fr", "target": "#smart-button"}

    def _verify_layers(self) -> dict[str, Any]:
        required = [
            "cognicion/core_identity_engine.py",
            "cognicion/core_vision_engine.py",
            "cognicion/core_control.py",
            "views/ui_layer",
            "views/capture",
            "views/analysis",
            "core/brain_connector",
        ]
        missing = [p for p in required if not (ROOT / p).exists()]
        return {"ok": not missing, "missing": missing}

    def execute_pipeline(self) -> dict[str, Any]:
        print("=== INICIANDO PIPELINE DE DESPLIEGUE AUTOMATICO ===")
        for action in self.target_actions:
            print(f"[EJECUTANDO] -> {action}")

        centering = self._verify_centering()
        layers = self._verify_layers()

        try:
            from cognicion.core_flow_verification import run_channel_audit

            channels = run_channel_audit()
        except Exception as exc:
            channels = {"ok": False, "error": f"{type(exc).__name__}:{exc}"}

        try:
            from cognicion.core_deployment_finalizer import run_finalizer

            finalize = run_finalizer()
        except Exception as exc:
            finalize = {"ok": False, "error": f"{type(exc).__name__}:{exc}"}

        all_ok = bool(centering["ok"] and layers["ok"] and channels.get("ok") and finalize.get("ok"))
        message = (
            "DEPLOY_SUCCESSFUL: Boton centrado, capas verificadas y actualizacion en camino a produccion."
            if all_ok
            else "DEPLOY_BLOCKED: Revisar centrado o capas antes del push."
        )
        print(message)
        return {
            "ok": all_ok,
            "message": message,
            "centering": centering,
            "layers": layers,
            "channels": {"ok": channels.get("ok"), "status": channels.get("status")},
            "finalize": {"ok": finalize.get("ok"), "status": finalize.get("status")},
        }


if __name__ == "__main__":
    result = ImmediateDeployEngine().execute_pipeline()
    print(result["message"])
    raise SystemExit(0 if result["ok"] else 1)
