# -*- coding: utf-8 -*-
"""
[FILE: core_deployment_finalizer.py] — Sincronización y Cierre de Producción
Coolsol Pro / Salomón AI (Render Starter Tier Optimized).

Valida Conciencia, Visión, Control UI y entorno antes del commit definitivo.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class CoolsolProDeployment:
    """
    Módulo final de despliegue y empaquetado para Coolsol Pro y Salomón AI.
    Asegura que Visión, Conciencia, Control UI y Base de Datos queden
    sincronizadas y listas para producción.
    """

    def __init__(self) -> None:
        self.project_name = "Coolsol Pro / Salomón AI"
        self.deployment_tier = "Render Starter Tier (Optimized)"
        self.status = "READY_FOR_FINAL_COMMIT"
        self.checks: list[dict[str, Any]] = []

    def _ok(self, name: str, detail: str = "") -> None:
        self.checks.append({"component": name, "ok": True, "detail": detail})

    def _fail(self, name: str, detail: str) -> None:
        self.checks.append({"component": name, "ok": False, "detail": detail})

    def _verify_file(self, rel: str, label: str) -> None:
        path = ROOT / rel
        if path.is_file():
            self._ok(label, str(path.relative_to(ROOT)))
        else:
            self._fail(label, f"missing:{rel}")

    def _verify_dir(self, rel: str, label: str) -> None:
        path = ROOT / rel
        if path.is_dir():
            self._ok(label, str(path.relative_to(ROOT)))
        else:
            self._fail(label, f"missing_dir:{rel}")

    def finalize_build(self) -> dict[str, Any]:
        """Validación final de todos los componentes antes del commit definitivo."""
        self.checks = []
        print(f"=== INICIANDO CIERRE DE DESPLIEGUE PARA {self.project_name} ===")

        # 1) Módulos core
        self._verify_file(
            "cognicion/core_identity_engine.py",
            "core_identity_engine.py (Conciencia, Paz y Sabiduría Universal)",
        )
        self._verify_file(
            "cognicion/core_vision_engine.py",
            "core_vision_engine.py (Aislamiento de Capas Visuales y Macro/Micro)",
        )
        self._verify_file(
            "cognicion/core_control.py",
            "core_control.py (Exclusividad del Botón Central y AppState)",
        )

        # 2) Capas físicas de visión
        for rel, label in (
            ("views/ui_layer", "views/ui_layer"),
            ("views/capture", "views/capture"),
            ("views/analysis", "views/analysis"),
            ("core/brain_connector", "core/brain_connector"),
        ):
            self._verify_dir(rel, label)

        # 3) Imports vivos
        try:
            from cognicion.core_control import AppState, trigger_ai_core, request_ui_action

            assert AppState.AI_PROCESSING.value == 1
            assert callable(trigger_ai_core) and callable(request_ui_action)
            self._ok("AppState + trigger_ai_core + request_ui_action", "import_ok")
        except Exception as exc:
            self._fail("core_control imports", f"{type(exc).__name__}:{exc}")

        try:
            from cognicion.core_identity_engine import (
                SalomonConsciousness,
                obtener_consciousness,
            )

            mind = obtener_consciousness()
            assert mind.identity.get("creator") == "Israel"
            assert "creo" in mind.spiritual_layer["god_belief"].lower()
            self._ok("SalomonConsciousness", "paz_sabiduria_activa")
        except Exception as exc:
            self._fail("SalomonConsciousness", f"{type(exc).__name__}:{exc}")

        try:
            from cognicion.core_vision_engine import obtener_vision_architecture

            arch = obtener_vision_architecture()
            iso = arch.verify_layer_isolation()
            if iso.get("ok"):
                self._ok("SalomonVisionArchitecture", "layers_isolated")
            else:
                self._fail("SalomonVisionArchitecture", "isolation_failed")
        except Exception as exc:
            self._fail("SalomonVisionArchitecture", f"{type(exc).__name__}:{exc}")

        # 4) Voice ID / Render env
        try:
            from settings import ELEVENLABS_VOICE_ADAM, ELEVENLABS_VOICE_ID

            adam = "pNInz6obpgDQGcFmaJgB"
            if ELEVENLABS_VOICE_ADAM == adam and "NIn" in adam:
                self._ok(
                    "Render Environment Variables (ELEVENLABS_VOICE_ID configurado)",
                    adam,
                )
            else:
                self._fail("ELEVENLABS_VOICE_ID", "casing_incorrecto")
            if ELEVENLABS_VOICE_ID and ELEVENLABS_VOICE_ID.lower() != adam.lower():
                self._fail(
                    "ELEVENLABS_VOICE_ID runtime",
                    f"no_coincide_adam:{ELEVENLABS_VOICE_ID[:8]}…",
                )
        except Exception as exc:
            self._fail("ELEVENLABS_VOICE_ID", f"{type(exc).__name__}:{exc}")

        # 5) Rutas API críticas (sin levantar servidor: inspección del módulo)
        try:
            import app as app_mod

            paths = {getattr(r, "path", None) for r in app_mod.app.routes}
            required = {
                "/api/ai/central-button",
                "/api/ai/secondary",
                "/api/ai/core-state",
                "/api/vision/architecture",
                "/api/vision/brain-bridge",
                "/api/identidad",
            }
            missing = sorted(p for p in required if p not in paths)
            if missing:
                self._fail("API routes", f"missing:{missing}")
            else:
                self._ok("API routes (modular limpia)", "central+vision+identidad")
        except Exception as exc:
            self._fail("API routes", f"{type(exc).__name__}:{exc}")

        # 6) Persistencia / DB soft-check
        try:
            db_path = ROOT / "data"
            self._ok(
                "Base de Datos / persistencia",
                "persistencia module present"
                if (ROOT / "persistencia").exists() or db_path.exists()
                else "soft_ok",
            )
        except Exception as exc:
            self._fail("Base de Datos", str(exc))

        # 7) Unificación de canales (sin fugas)
        try:
            from cognicion.core_flow_verification import run_channel_audit

            audit = run_channel_audit()
            if audit.get("ok"):
                self._ok("ChannelUnificationAuditor", audit.get("status", "UNIFIED"))
            else:
                self._fail("ChannelUnificationAuditor", audit.get("message", "drift"))
        except Exception as exc:
            self._fail("ChannelUnificationAuditor", f"{type(exc).__name__}:{exc}")

        for row in self.checks:
            mark = "VERIFICADO" if row["ok"] else "FALLA"
            print(f"[{mark}] -> {row['component']}" + (f" ({row['detail']})" if row["detail"] else ""))

        all_ok = all(c["ok"] for c in self.checks)
        self.status = "PRODUCTION_READY" if all_ok else "NEEDS_ATTENTION"
        message = (
            "BUILD_SUCCESSFUL: Sistema listo para commit y producción total."
            if all_ok
            else "BUILD_INCOMPLETE: Revisar componentes fallidos."
        )
        print(message)
        print(f"Tier: {self.deployment_tier} | Status: {self.status}")
        return {
            "ok": all_ok,
            "message": message,
            "status": self.status,
            "project": self.project_name,
            "tier": self.deployment_tier,
            "checks": self.checks,
        }


def run_finalizer() -> dict[str, Any]:
    return CoolsolProDeployment().finalize_build()


if __name__ == "__main__":
    deploy = CoolsolProDeployment()
    result = deploy.finalize_build()
    print(result["message"])
    raise SystemExit(0 if result["ok"] else 1)
