# -*- coding: utf-8 -*-
"""
[FILE: core_salomon_supreme_supervisor_and_web_intelligence.py]
Agente Supervisor Supremo + Web Intelligence (audita capas y consulta fuentes externas).
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

_RE_ARCH_WEB = re.compile(
    r"(?i)\b("
    r"arquitectura\s+(de\s+)?(ia|ai|cognitiva|neuronal)|"
    r"framework\s+(de\s+)?(ia|ai|llm|rag)|"
    r"c[oó]mo\s+(se\s+)?(estructura|diseña|implementa)|"
    r"best\s+practice|documentaci[oó]n\s+oficial|"
    r"paper|arxiv|openai|anthropic|langchain|langgraph|"
    r"referencia\s+t[eé]cnica|est[aá]ndar\s+(de\s+)?(ia|industria)|"
    r"valida(r)?\s+(con\s+)?(fuente|web|internet)|"
    r"busca\s+(en\s+)?(la\s+)?web|investiga"
    r")\b"
)


class SalomonSupremeSupervisorEngine:
    def __init__(self) -> None:
        self.module = "SalomonSupremeSupervisorEngine"
        self.status = "SUPREME_SUPERVISOR_AND_WEB_INTELLIGENCE_ACTIVE"
        self.total_layers_supervised = 7

    def _read(self, rel: str) -> str:
        path = ROOT / rel
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    def _exists(self, rel: str) -> bool:
        return (ROOT / rel).is_file()

    def audit_memory_layer(self) -> dict[str, Any]:
        ses = self._read("persistencia/sesiones.py")
        gestor = self._read("cognicion/memoria/gestor.py")
        ok = (
            "journal_mode=WAL" in ses
            and "BEGIN IMMEDIATE" in ses
            and "limite: int = 16" in gestor
            and "guardar_mensaje" in ses
        )
        return {
            "layer": 2,
            "name": "memory_sqlite_wal",
            "ok": ok,
            "detail": "WAL+atomic+16 turns" if ok else "memory contract broken",
        }

    def audit_voice_bridge(self) -> dict[str, Any]:
        voice = self._read("static/js/voice_layer.js")
        settings = self._read("settings.py")
        providers = self._read("config/providers.py")
        ok = (
            "SalomonVoiceLayer" in voice
            and "ELEVENLABS_VOICE_ADAM" in settings
            and "_presente(S.ELEVENLABS_API_KEY)" in providers
        )
        return {
            "layer": 4,
            "name": "voice_audio_bridge",
            "ok": ok,
            "detail": "Adam TTS path" if ok else "voice bridge incomplete",
        }

    def audit_vision_standby(self) -> dict[str, Any]:
        ve = self._read("static/js/vision_engine.js")
        ok = (
            "analyticalStreaming" in ve
            and "standby" in ve
            and "engageAnalyticalStreaming" in ve
            and "disengageVisualMode" in ve
        )
        return {
            "layer": 1,
            "name": "vision_standby",
            "ok": ok,
            "detail": "standby/analytical router" if ok else "vision router missing",
        }

    def audit_smart_button(self) -> dict[str, Any]:
        btn = self._read("static/js/components/SmartButton.js")
        cam_block = (
            "if (window.SalomonCamera && window.SalomonCamera.isActive()) return true;"
            in btn
        )
        ok = (
            "DOUBLE_TAP_MS" in btn
            and "_tapCount" in btn
            and "neutralize" in btn
            and not cam_block
        )
        return {
            "layer": "button",
            "name": "smart_button_controller",
            "ok": ok,
            "detail": "1/2 tap + sensory synapse" if ok else "button desync",
        }

    def audit_synaptic_contracts(self) -> dict[str, Any]:
        try:
            from cognicion.capas_inteligencia.layer_contracts import verify_contracts
            from cognicion.capas_inteligencia.neural_core_bridge import (
                harmonize_all_layers,
            )

            c = verify_contracts()
            b = harmonize_all_layers()
            ok = bool(c.get("ok")) and bool(b.get("sealed"))
            return {
                "ok": ok,
                "contracts": c.get("ok"),
                "bridges_sealed": b.get("sealed"),
                "name": "synaptic_contracts",
            }
        except Exception as exc:
            return {"ok": False, "error": type(exc).__name__, "name": "synaptic_contracts"}

    def audit_all_layers(self) -> dict[str, Any]:
        """Auditoría cruzada en tiempo de supervisión."""
        layers = [
            self.audit_vision_standby(),
            self.audit_memory_layer(),
            self.audit_voice_bridge(),
            self.audit_smart_button(),
        ]
        syn = self.audit_synaptic_contracts()
        ok = all(x.get("ok") for x in layers) and bool(syn.get("ok"))
        return {
            "ok": ok,
            "desync": [x["name"] for x in layers if not x.get("ok")]
            + ([] if syn.get("ok") else ["synaptic_contracts"]),
            "layers": layers,
            "synaptic": syn,
            "via": "supreme_supervisor",
        }

    def needs_web_intelligence(self, mensaje: str) -> bool:
        """Web cuando falta contexto técnico/arquitectónico o hay vacío factual."""
        text = (mensaje or "").strip()
        if not text:
            return False
        if _RE_ARCH_WEB.search(text):
            return True
        try:
            from cognicion.core_salomon_master_neural_engine import obtener_master_neural

            return bool(obtener_master_neural().should_search_web(text, rag_empty=True))
        except Exception:
            return bool(_RE_ARCH_WEB.search(text))

    def fetch_web_intelligence(self, mensaje: str) -> dict[str, Any]:
        """
        Consulta recursos externos (enjambre paralelo) — fail-soft.
        No inventa: solo sintetiza hallazgos del swarm.
        """
        if not self.needs_web_intelligence(mensaje):
            return {"ok": False, "skipped": True, "bloque": "", "via": "web_intelligence"}

        try:
            from cognicion.core_salomon_master_neural_engine import obtener_master_neural

            # Preferir consulta orientada a arquitectura si aplica
            query = mensaje
            if _RE_ARCH_WEB.search(mensaje or ""):
                query = (
                    f"{mensaje}\n"
                    "(Prioriza documentación oficial, frameworks de IA, "
                    "arquitecturas cognitivas y referencias técnicas verificables.)"
                )
            pack = obtener_master_neural().deploy_agent_swarm(query)
            bloque = pack.get("bloque") or ""
            if bloque:
                bloque = (
                    "[Supervisor — Web Intelligence / recursos externos]\n"
                    + bloque.replace(
                        "[Enjambre neuronal — agentes paralelos en vivo]\n",
                        "",
                        1,
                    )
                )
            return {
                "ok": bool(pack.get("ok")),
                "bloque": bloque,
                "swarm": pack,
                "via": "supreme_web_intelligence",
            }
        except Exception as exc:
            return {
                "ok": False,
                "error": type(exc).__name__,
                "bloque": "",
                "via": "supreme_web_intelligence",
            }

    def supervise_turn(
        self,
        mensaje: str,
        *,
        session_id: str | None = None,
        already_swarmed: bool = False,
    ) -> dict[str, Any]:
        """
        Punto de entrada del orquestador: audita capas + opcional web intelligence.
        No rompe el turno si falla (fail-soft).
        """
        audit = self.audit_all_layers()
        web: dict[str, Any] = {"skipped": True}
        if not already_swarmed and self.needs_web_intelligence(mensaje):
            web = self.fetch_web_intelligence(mensaje)
        elif already_swarmed:
            web = {"ok": True, "skipped": True, "reason": "swarm_already", "bloque": ""}

        return {
            "ok": bool(audit.get("ok")),
            "audit": audit,
            "web": web,
            "bloque": (web.get("bloque") or "") if web.get("ok") else "",
            "session_id": session_id,
            "status": self.status if audit.get("ok") else "SUPERVISOR_DESYNC",
            "via": "supreme_supervisor",
        }

    def compile_supervisor_spec(self) -> str:
        print("[COMPILANDO AGENTE SUPERVISOR Y CONEXION WEB - SALOMON AI]")
        audit = self.audit_all_layers()
        for layer in audit.get("layers") or []:
            print(
                f"  [{'OK' if layer.get('ok') else 'FAIL'}] "
                f"{layer.get('name')}: {layer.get('detail')}"
            )
        syn = audit.get("synaptic") or {}
        print(
            f"  [{'OK' if syn.get('ok') else 'FAIL'}] synaptic "
            f"contracts={syn.get('contracts')} sealed={syn.get('bridges_sealed')}"
        )
        complete = bool(audit.get("ok"))
        spec = {
            "action": (
                "Enforce a supreme neural supervisor agent to coordinate all "
                "cognitive layers, connect to external web intelligence for "
                "architectural resources, and halt any code regressions."
            ),
            "module": self.module,
            "status": self.status if complete else "SUPERVISOR_DESYNC",
            "components": [
                "Neural Supervisor Agent (Cross-layer auditing)",
                "Web Intelligence & Resource Retrieval Module",
                "Strict Execution Compliance Engine",
            ],
            "audit": audit,
            "complete": complete,
            "deployment": (
                "Auto-commit, push to Render production, PWA update, "
                "and settings badge active."
            ),
        }
        print(json.dumps({"status": spec["status"], "complete": complete}, indent=2))
        return json.dumps(spec, indent=2, ensure_ascii=True)

    def run(self) -> dict[str, Any]:
        return json.loads(self.compile_supervisor_spec())


_ENGINE: SalomonSupremeSupervisorEngine | None = None


def obtener_supreme_supervisor() -> SalomonSupremeSupervisorEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = SalomonSupremeSupervisorEngine()
    return _ENGINE


def run_supreme_supervisor() -> dict[str, Any]:
    return obtener_supreme_supervisor().run()


if __name__ == "__main__":
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    report = run_supreme_supervisor()
    sys.exit(0 if report.get("complete") else 1)
