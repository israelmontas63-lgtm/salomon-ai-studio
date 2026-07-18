# -*- coding: utf-8 -*-
"""Filtro de Claridad — ruido ↓ · intención central de Israel ↑."""

from __future__ import annotations

import re
from typing import Any

_RUIDO = re.compile(
    r"\b(por favor|pls|please|eh+|este+|o sea|tipo|literalmente|ok+|vale)\b",
    re.IGNORECASE,
)


def filtrar_claridad(mensaje: str) -> dict[str, Any]:
    """
    Extrae intención central y versión enfocada (sin LLM obligatorio).
    """
    bruto = (mensaje or "").strip()
    if not bruto:
        return {
            "ok": False,
            "intencion_central": "",
            "enfocado": "",
            "ruido_filtrado": True,
            "deseo": "sin_mensaje",
        }

    limpio = _RUIDO.sub(" ", bruto)
    limpio = re.sub(r"\s+", " ", limpio).strip(" .,;:¡!¿?")
    lower = limpio.lower()

    deseo = "informacion"
    if any(x in lower for x in ("haz", "implementa", "crea", "arregla", "corrige", "deploy")):
        deseo = "accion"
    elif any(x in lower for x in ("explica", "qué es", "que es", "cómo", "como", "por qué")):
        deseo = "comprension"
    elif any(x in lower for x in ("busca", "investiga", "tendencia", "mercado", "oportunidad")):
        deseo = "exploracion"
    elif any(x in lower for x in ("mal", "error", "equivoc", "no es eso", "otra vez")):
        deseo = "correccion"

    # Intención = primera oración sustancial o mensaje completo corto
    partes = re.split(r"[.!?]\s+", limpio)
    central = partes[0].strip() if partes else limpio
    if len(central) < 8 and len(partes) > 1:
        central = limpio[:220]

    return {
        "ok": True,
        "intencion_central": central[:280],
        "enfocado": limpio[:800],
        "ruido_filtrado": limpio != bruto,
        "deseo": deseo,
        "solucion_directa": (
            "Enfócate en la intención central; evita rodeos y listas de capacidades."
        ),
    }
