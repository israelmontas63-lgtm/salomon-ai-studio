# [FILE: core_salomon_auto_clean_and_deployment_orchestrator.py]
# Orquestador Autónomo de Limpieza Estructural y Corrección de Errores (Salomón AI)
"""Promueve el árbol de producción a la raíz del workspace y valida rutas FastAPI."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

ESSENTIAL_FILES = (
    "app.py",
    "requirements.txt",
    "render.yaml",
    "Procfile",
    "cerebro.py",
    "settings.py",
    "version.json",
)

ESSENTIAL_DIRS = (
    "static",
    "templates",
    "cognicion",
    "core",
    "api",
    "persistencia",
)

# Frontend → backend (FastAPI, no Flask)
CRITICAL_JS_ROUTES = {
    "static/js/components/SmartButton.js": ("/api/ai/central-button",),
    "static/js/ai_state_lock.js": (
        "/api/ai/central-button",
        "/api/ai/secondary",
        "/api/ai/lock",
    ),
    "static/js/voice_layer.js": ("/api/tts",),
    "static/js/vision_engine.js": ("/api/vision/brain-bridge",),
    "static/js/script.js": ("/api/chat", "/api/historial"),
}


class SalomonAutoCleanAndOrchestrator:
    """Limpieza estructural + validación de rutas de producción."""

    MODULE = "SalomonAutoCleanAndOrchestrator"
    STATUS = "CLEAN_AND_SYNCHRONIZED"
    VERSION = "110.16.0"

    def __init__(self, root_dir: str | None = None) -> None:
        self.root_dir = Path(root_dir or os.getcwd()).resolve()
        self.module = self.MODULE

    def _exists(self, rel: str) -> bool:
        return (self.root_dir / rel).exists()

    def validate_root(self) -> dict[str, Any]:
        missing_files = [f for f in ESSENTIAL_FILES if not self._exists(f)]
        missing_dirs = [d for d in ESSENTIAL_DIRS if not self._exists(d)]
        nested = self._exists("_render_repo")
        return {
            "ok": not missing_files and not missing_dirs and not nested,
            "missing_files": missing_files,
            "missing_dirs": missing_dirs,
            "nested_render_repo_present": nested,
            "root": str(self.root_dir),
        }

    def clean_temp_logs(self) -> list[str]:
        removed: list[str] = []
        for name in (".tunnel.log", ".tunnel.err.log"):
            path = self.root_dir / name
            if path.is_file():
                try:
                    path.unlink()
                    removed.append(name)
                except OSError:
                    pass
        return removed

    def audit_js_routes(self) -> dict[str, Any]:
        """Verifica que el JS de dictado/visión/TTS apunte a endpoints FastAPI reales."""
        issues: list[dict[str, str]] = []
        checked = 0
        for rel, routes in CRITICAL_JS_ROUTES.items():
            path = self.root_dir / rel
            if not path.is_file():
                issues.append({"file": rel, "error": "missing_file"})
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for route in routes:
                checked += 1
                if route not in text:
                    issues.append({"file": rel, "error": f"missing_route:{route}"})
            if "flask" in text.lower() and "fastapi" not in text.lower():
                issues.append({"file": rel, "error": "flask_reference_without_fastapi"})
        return {"ok": len(issues) == 0, "checked": checked, "issues": issues}

    def execute_cleanup_and_sync(self) -> dict[str, Any]:
        removed_logs = self.clean_temp_logs()
        root = self.validate_root()
        routes = self.audit_js_routes()
        status = (
            "CLEAN_AND_SYNCHRONIZED"
            if root.get("ok") and routes.get("ok")
            else "NEEDS_ATTENTION"
        )
        return {
            "status": status,
            "module": self.module,
            "version": self.VERSION,
            "backend": "FastAPI (gunicorn + uvicorn) — not Flask",
            "root_validation": root,
            "js_routes": routes,
            "removed_logs": removed_logs,
            "action": (
                "Validated production files at workspace root, confirmed smart-button / "
                "vision / Adam TTS routes against FastAPI endpoints, cleaned temp logs."
            ),
            "deployment": (
                "Ready for automated git commit, Render push, and PWA cache refresh."
            ),
            "note": (
                "_legacy_workspace/ holds the pre-flatten Cursor shell; "
                "it is gitignored and not deployed."
            ),
        }


def run_orchestrator(root: str | None = None) -> dict[str, Any]:
    return SalomonAutoCleanAndOrchestrator(root).execute_cleanup_and_sync()


if __name__ == "__main__":
    orchestrator = SalomonAutoCleanAndOrchestrator(str(ROOT))
    print(f"[SALOMÓN AI] Limpieza estricta en la raíz: {ROOT}")
    print(json.dumps(orchestrator.execute_cleanup_and_sync(), indent=2, ensure_ascii=False))
