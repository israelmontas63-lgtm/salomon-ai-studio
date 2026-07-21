# [FILE: core_salomon_multimodal_intent_router_and_voice_trigger.py]
# Motor de Enrutamiento de Intenciones y Activación de Voz (Salomón AI)
"""Enruta 'activa el modo visión' → análisis + Adam TTS; dictado 1 toque → voz+texto."""

from __future__ import annotations

import json
from typing import Any


class SalomonIntentRouterEngine:
    """Contrato: visión por comando de voz + respuesta dual en dictado."""

    MODULE = "SalomonIntentRouterEngine"
    STATUS = "MULTIMODAL_INTENT_ROUTER_ACTIVE"
    VERSION = "110.14.0"

    def __init__(self) -> None:
        self.module = self.MODULE
        self.status = self.STATUS

    def compile_router_spec(self) -> dict[str, Any]:
        return {
            "action": (
                "Enforce voice-triggered vision mode with descriptive vocal "
                "feedback and dual voice/text output on single-tap dictation mode."
            ),
            "components": [
                "Voice Triggered Vision Parser ('Activa el modo visión')",
                "Dual Voice (Adam TTS) & Text Output Pipeline",
                "Single-Tap Dictation Audio-Response Binding",
            ],
            "routing": {
                "activa_modo_vision": "engage_analytical_streaming + brain-bridge + Adam",
                "dictation_1_tap": "texto en chat + ensureSpeak(/api/tts fallback)",
            },
            "deployment": (
                "Auto-commit, push to Render production, PWA update, "
                "and settings badge active."
            ),
            "version": self.VERSION,
            "status": self.status,
        }

    def as_json(self) -> str:
        return json.dumps(self.compile_router_spec(), indent=2, ensure_ascii=False)


def estado_router() -> dict[str, Any]:
    return SalomonIntentRouterEngine().compile_router_spec()


if __name__ == "__main__":
    router = SalomonIntentRouterEngine()
    print("[COMPILANDO ENRUTADOR DE INTENCIONES Y VOZ MULTIMODAL - SALOMÓN AI]")
    print(router.as_json())
