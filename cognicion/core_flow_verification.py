# -*- coding: utf-8 -*-
"""
[FILE: core_flow_verification.py] — Verificador de Unificación de Canales
Salomón AI / Coolsol Pro.

Audita que hardware, cámara, UI y entradas converjan al mismo núcleo,
sin rutas huérfanas.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class ChannelUnificationAuditor:
    """
    Motor de auditoría técnica: todos los flujos deben apuntar al núcleo central.
    """

    def __init__(self) -> None:
        self.target_core = "SalomonBrain / core_identity_engine.py"
        self.expected_sources = [
            "UI Layer (/views/ui_layer/)",
            "Capture Layer (/views/capture/)",
            "Macro/Micro Vision Engine (/views/analysis/)",
            "Central Action Button (AppState.AI_PROCESSING)",
        ]
        self.findings: list[dict[str, Any]] = []

    def _mark(self, source: str, ok: bool, detail: str) -> None:
        self.findings.append(
            {
                "source": source,
                "ok": ok,
                "detail": detail,
                "target": self.target_core,
            }
        )
        tag = "VERIFICADO" if ok else "HUERFANO"
        # ASCII-safe for Windows consoles (cp1252)
        line = f"[{tag}] La fuente '{source}' -> {detail}"
        try:
            print(line)
        except UnicodeEncodeError:
            print(line.encode("ascii", "replace").decode("ascii"))

    def _read(self, rel: str) -> str:
        path = ROOT / rel
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    def _dir_ok(self, rel: str) -> bool:
        return (ROOT / rel).is_dir()

    def audit_routing_integrity(self) -> dict[str, Any]:
        """Verifica que los componentes apunten al cerebro unificado."""
        self.findings = []
        print("=== AUDITORIA DE UNIFICACION DE CANALES ===")
        print(f"Nucleo objetivo: {self.target_core}")

        # —— Capas físicas ——
        ui_ok = self._dir_ok("views/ui_layer") and "request_ui_action" in self._read(
            "views/ui_layer/__init__.py"
        )
        self._mark(
            self.expected_sources[0],
            ui_ok,
            "views/ui_layer -> core_control.request_ui_action (portero -> nucleo)"
            if ui_ok
            else "capa UI ausente o sin gate",
        )

        cap_ok = self._dir_ok("views/capture") and "normalize_frame_payload" in self._read(
            "views/capture/__init__.py"
        )
        self._mark(
            self.expected_sources[1],
            cap_ok,
            "views/capture -> frame normalizado -> analysis/brain_bridge"
            if cap_ok
            else "capa captura ausente",
        )

        an_txt = self._read("views/analysis/__init__.py")
        an_ok = self._dir_ok("views/analysis") and "brain_bridge" in an_txt
        self._mark(
            self.expected_sources[2],
            an_ok,
            "views/analysis (macro/micro) -> brain_bridge + cognicion.vision"
            if an_ok
            else "analisis no referencia brain_bridge",
        )

        # —— Botón central / AppState ——
        ctrl = self._read("cognicion/core_control.py")
        btn_js = self._read("static/js/components/SmartButton.js")
        lock_js = self._read("static/js/ai_state_lock.js")
        central_ok = (
            "trigger_ai_core" in ctrl
            and "AI_PROCESSING" in ctrl
            and (
                "trigger_ai_core" in btn_js
                or "trigger_ai_core" in lock_js
                or "callBrainDirect" in btn_js
            )
            and "/api/ai/central-button" in lock_js
        )
        self._mark(
            self.expected_sources[3],
            central_ok,
            "SmartButton/AILock -> /api/ai/central-button -> trigger_ai_core -> cerebro"
            if central_ok
            else "boton central no cableado a trigger_ai_core",
        )

        # —— Puente visual ——
        bridge = self._read("core/brain_connector/bridge.py")
        vision_js = self._read("static/js/vision_engine.js")
        bridge_ok = (
            "trigger_ai_core" in bridge
            and "send_visual_to_core" in bridge
            and "/api/vision/brain-bridge" in vision_js
        )
        self._mark(
            "Vision Brain Bridge",
            bridge_ok,
            "vision_engine -> /api/vision/brain-bridge -> send_visual_to_core -> trigger_ai_core"
            if bridge_ok
            else "fuga: vision no usa brain-bridge",
        )

        # —— Identidad / conciencia en cerebro ——
        cerebro = self._read("cerebro.py")
        id_eng = self._read("cognicion/core_identity_engine.py")
        identity_ok = (
            "obtener_identity_engine" in cerebro
            and "SalomonConsciousness" in id_eng
            and "procesar_entrada" in cerebro
        )
        self._mark(
            "Identity / Consciousness Core",
            identity_ok,
            "cerebro.procesar_entrada consulta core_identity_engine (SalomonConsciousness)"
            if identity_ok
            else "cerebro no consulta identity engine",
        )

        # —— Chat unificado ——
        app_py = self._read("app.py")
        script_js = self._read("static/js/script.js")
        mente = self._read("mente/conexion.py")
        chat_ok = ("/api/chat" in script_js) and (
            "procesar_unificado" in mente or "procesar_entrada" in app_py
        )
        self._mark(
            "Chat / User Input",
            chat_ok,
            "script.js -> /api/chat -> mente/cerebro (mismo nucleo)"
            if chat_ok
            else "chat con ruta huerfana",
        )

        # —— Cámara respeta exclusividad ——
        cam = self._read("static/js/camera_logic.js")
        cam_ok = "request_ui_action" in cam and "camera_blocked_by_ai_priority" in cam
        self._mark(
            "Camera Hardware Gate",
            cam_ok,
            "camera_logic -> request_ui_action + bloqueo fisico si AI_PROCESSING"
            if cam_ok
            else "camara sin gate de exclusividad",
        )

        # —— Rutas API presentes ——
        try:
            import app as app_mod

            paths = {getattr(r, "path", None) for r in app_mod.app.routes}
            need = {
                "/api/ai/central-button",
                "/api/vision/brain-bridge",
                "/api/chat",
                "/api/identidad",
            }
            missing = sorted(need - paths)
            api_ok = not missing
            self._mark(
                "API Surface",
                api_ok,
                "rutas unificadas presentes" if api_ok else f"faltan:{missing}",
            )
        except Exception as exc:
            self._mark("API Surface", False, f"{type(exc).__name__}:{exc}")

        all_ok = all(f["ok"] for f in self.findings)
        message = (
            "ROUTING_SUCCESSFUL: Ningún componente opera de forma aislada; "
            "todo converge en el cerebro de Salomón."
            if all_ok
            else "ROUTING_DRIFT: Hay rutas huérfanas o desconexiones — revisar findings."
        )
        print(message)
        return {
            "ok": all_ok,
            "message": message,
            "target_core": self.target_core,
            "expected_sources": list(self.expected_sources),
            "findings": self.findings,
            "status": "UNIFIED" if all_ok else "DRIFT",
        }


def run_channel_audit() -> dict[str, Any]:
    return ChannelUnificationAuditor().audit_routing_integrity()


if __name__ == "__main__":
    result = run_channel_audit()
    print(result["message"])
    raise SystemExit(0 if result["ok"] else 1)
