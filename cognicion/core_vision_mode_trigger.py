# -*- coding: utf-8 -*-
"""
[FILE: core_vision_mode_trigger.py] — Activador del Modo Visión (Salomón AI).
Gatillo verbal + sincronía con botón cámara (elevación). No toca el neutralizador Back.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

VOICE_KEYWORDS = (
    "modo visión",
    "modo vision",
    "ojos activos",
    "activa el modo visión",
    "puedes ver lo que está frente a mí",
    "desactiva el modo visual",
)

_RE_GATILLO = re.compile(
    r"(?i)\b("
    r"activa(r)?\s+(el\s+)?modo\s+visi[oó]n|"
    r"modo\s+visi[oó]n|"
    r"ojos\s+activos|"
    r"activa(r)?\s+(mis\s+)?ojos|"
    r"activa(r)?\s+visi[oó]n|"
    r"visi[oó]n\s+activa|"
    r"enciende\s+(la\s+)?c[aá]mara|"
    r"abre\s+(la\s+)?c[aá]mara"
    r")\b"
)

# Streaming analítico por voz (ojos ya en standby o a abrir)
_RE_VER_FRENTE = re.compile(
    r"(?i)\bpuedes\s+ver\b.*\b(frente\s+a\s+m[ií]|delante\s+de\s+m[ií])\b|"
    r"(?i)\bmira\s+lo\s+que\s+tengo\s+delante\b"
)

_RE_DESACTIVAR_VISUAL = re.compile(
    r"(?i)\b("
    r"desactiva(r)?\s+(el\s+)?modo\s+visual|"
    r"apaga\s+(el\s+)?modo\s+visual|"
    r"desactiva(r)?\s+(la\s+)?visi[oó]n|"
    r"okay,?\s*salom[oó]n,?\s*desactiva"
    r")\b"
)

ACTIVATION_REPLY = (
    "Cámara en reposo (standby). Los fotogramas se capturan en silencio — "
    "di «Salomón, ¿puedes ver lo que está frente a mí?» para que analice y te responda."
)


class VisionModeTriggerEngine:
    """
    1. GATILLO VERBAL: frases clave → enciende motor de visión.
    2. GATILLO TÁCTIL: sincronizado con botón cámara + elevación.
    3. AISLAMIENTO: no interfiere con UniversalNeutralizerBackButton.
    """

    def __init__(self) -> None:
        self.module = "VisionModeTrigger"

    def matches(self, mensaje: str) -> bool:
        return es_gatillo_modo_vision(mensaje)

    def compile_trigger_spec(self) -> str:
        spec = {
            "triggers": {
                "voice_keyword": list(VOICE_KEYWORDS[:4]),
                "ui_action": "camera_button_tap_with_elevation",
            },
            "behavior": (
                "Engages vision pipeline smoothly and switches Salomon AI "
                "to visual processing state."
            ),
            "isolation": {
                "neutralizer_back": "untouched",
                "forbidden_touch": ["#btn-back", "back_button.js"],
            },
            "assets": {
                "py": "cognicion/core_vision_mode_trigger.py",
                "js": "static/js/vision_mode_trigger.js",
                "camera_ui": "static/js/camera_toggle_ui.js",
            },
            "deployment": "Auto-commit and push to Render production",
        }
        return json.dumps(spec, indent=2)

    def activation_payload(self, mensaje: str = "") -> dict[str, Any]:
        return {
            "activar_modo_vision": True,
            "vision_requerida": True,
            "ui_action": "open_camera_with_elevation",
            "texto": ACTIVATION_REPLY,
            "cognicion": {
                "vision_mode_trigger": True,
                "vision_en_flujo": True,
                "vision_requerida": True,
                "gatillo": (mensaje or "").strip()[:120],
                "protocolo": "VISION_MODE_TRIGGER",
            },
        }

    def verify(self) -> dict[str, Any]:
        js = ROOT / "static" / "js" / "vision_mode_trigger.js"
        css_back = ROOT / "static" / "css" / "back_button.css"
        text = js.read_text(encoding="utf-8") if js.is_file() else ""
        touches_back = ("getElementById(\"btn-back\")" in text) or ("neutralize(" in text)
        return {
            "ok": js.is_file() and not touches_back and css_back.is_file(),
            "js_exists": js.is_file(),
            "isolates_neutralizer": not touches_back,
            "module": self.module,
        }


def es_gatillo_modo_vision(mensaje: str) -> bool:
    return bool(_RE_GATILLO.search(mensaje or ""))


def es_comando_ver_frente(mensaje: str) -> bool:
    return bool(_RE_VER_FRENTE.search(mensaje or ""))


def es_comando_desactivar_visual(mensaje: str) -> bool:
    return bool(_RE_DESACTIVAR_VISUAL.search(mensaje or ""))


def respuesta_activacion_vision(mensaje: str = "") -> dict[str, Any]:
    return VisionModeTriggerEngine().activation_payload(mensaje)


def respuesta_ver_frente(mensaje: str = "") -> dict[str, Any]:
    return {
        "activar_modo_vision": True,
        "vision_requerida": True,
        "vision_analytical": True,
        "ui_action": "engage_analytical_streaming",
        "texto": (
            "Sí — activo el análisis de lo que tienes frente a ti "
            "y te respondo con lo que veo."
        ),
        "cognicion": {
            "voice_triggered_vision": True,
            "analytical_streaming": True,
            "gatillo": (mensaje or "").strip()[:120],
            "protocolo": "VOICE_TRIGGERED_VISION",
        },
    }


def respuesta_desactivar_visual(mensaje: str = "") -> dict[str, Any]:
    return {
        "activar_modo_vision": False,
        "vision_requerida": False,
        "ui_action": "disengage_visual_mode",
        "texto": (
            "Modo visual desactivado. Libero la cámara y vuelvo al chat."
        ),
        "cognicion": {
            "voice_triggered_vision": False,
            "analytical_streaming": False,
            "gatillo": (mensaje or "").strip()[:120],
            "protocolo": "VOICE_TRIGGERED_VISION_OFF",
        },
    }


def obtener_vision_mode_trigger() -> VisionModeTriggerEngine:
    return VisionModeTriggerEngine()


if __name__ == "__main__":
    engine = VisionModeTriggerEngine()
    print(engine.compile_trigger_spec())
    print(engine.verify())
