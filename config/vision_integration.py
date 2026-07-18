# -*- coding: utf-8 -*-
"""
Integración de visión — cámara en el flujo de entrada de Salomón.
Activa si hay imagen o instrucción visual explícita.
"""

from __future__ import annotations

import os
import re
from typing import Any

VISION_ENABLED = os.getenv("VISION_ENABLED", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
VISION_IN_INPUT_FLOW = os.getenv("VISION_IN_INPUT_FLOW", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
CAMERA_ENGINE = "camera-engine.js / MediaStreamManager"
VISION_ENDPOINT = "api/chat (imagen_base64) + cognicion.vision"

_RE_ORDEN_VISUAL = re.compile(
    r"(?i)\b("
    r"mira(\s+esto|\s+la\s+c[aá]mara)?|"
    r"qu[eé]\s+ves|"
    r"qu[eé]\s+est[aá]s\s+viendo|"
    r"analiza\s+(esto|la\s+imagen|la\s+foto|la\s+escena)|"
    r"describe\s+(esto|la\s+imagen|la\s+foto|lo\s+que\s+ves)|"
    r"usa\s+la\s+c[aá]mara|"
    r"activa\s+visi[oó]n|"
    r"visi[oó]n\s+activa|"
    r"foto|"
    r"imagen|"
    r"c[aá]mara"
    r")\b"
)


def es_instruccion_visual(mensaje: str) -> bool:
    """True si Israel pide ver / analizar escena o imagen."""
    if not VISION_ENABLED:
        return False
    return bool(_RE_ORDEN_VISUAL.search(mensaje or ""))


def vision_debe_activar(*, mensaje: str = "", tiene_imagen: bool = False) -> bool:
    if not VISION_ENABLED or not VISION_IN_INPUT_FLOW:
        return False
    if tiene_imagen:
        return True
    return es_instruccion_visual(mensaje)


def vision_parameters() -> dict[str, Any]:
    return {
        "enabled": VISION_ENABLED,
        "in_input_flow": VISION_IN_INPUT_FLOW,
        "engine": CAMERA_ENGINE,
        "endpoint": VISION_ENDPOINT,
        "activa": bool(VISION_ENABLED and VISION_IN_INPUT_FLOW),
        "nucleo": "SalomonAI.procesar_entrada(imagen_base64=…)",
    }


def vision_status() -> dict[str, Any]:
    p = vision_parameters()
    return {
        "activa": bool(p["activa"]),
        "parametros": p,
    }
