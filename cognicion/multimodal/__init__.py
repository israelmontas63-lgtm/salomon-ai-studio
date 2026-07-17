# -*- coding: utf-8 -*-
"""
Multimodal Core v70 — visión, generación HD y agentes visuales
bajo presupuesto SystemGuard (5s indicador de progreso).
"""

from __future__ import annotations

import time
from typing import Any

MEDIA_PROGRESS_BUDGET_MS = 5000

_MARCAS_GENERACION = (
    "genera un boceto",
    "genera una imagen",
    "genera imagen",
    "crea una imagen",
    "crea un boceto",
    "dibuja",
    "ilustra",
    "imagen de alta definición",
    "imagen de alta definicion",
    "imagen hd",
    "foto realista",
    "render de",
    "video de",
    "genera un video",
    "crea un video",
)


def es_generacion_visual(texto: str) -> bool:
    t = (texto or "").lower()
    return any(m in t for m in _MARCAS_GENERACION)


def estado_multimodal() -> dict[str, Any]:
    from cognicion.media.media_engine import estado_media_routing

    media = estado_media_routing()
    return {
        "protocol": "MULTIMODAL_CORE",
        "version": "70.0.0",
        "parent_protocol": "SALOMON_VIVIENTE",
        "active": True,
        "modules": {
            "hd_generator": True,
            "prompt_enhancer": True,
            "visual_scrapers": True,
            "system_guard_budget_ms": MEDIA_PROGRESS_BUDGET_MS,
        },
        "media_routing": media,
        "progress_indicator": {
            "threshold_ms": MEDIA_PROGRESS_BUDGET_MS,
            "ui": "visual-progress / media-panel",
        },
    }


def ejecutar_con_presupuesto(fn, *args, **kwargs) -> dict[str, Any]:
    """
    Ejecuta generación/búsqueda midiendo latencia.
    No tumba el proceso; marca progreso_requerido si > 5s.
    """
    t0 = time.perf_counter()
    try:
        resultado = fn(*args, **kwargs)
    except Exception as exc:
        ms = int((time.perf_counter() - t0) * 1000)
        return {
            "exito": False,
            "error": f"{type(exc).__name__}: {exc}",
            "latencia_ms": ms,
            "progreso_requerido": ms >= MEDIA_PROGRESS_BUDGET_MS,
            "budget_ms": MEDIA_PROGRESS_BUDGET_MS,
            "system_guard": "media_budget_soft",
        }
    ms = int((time.perf_counter() - t0) * 1000)
    if isinstance(resultado, dict):
        out = dict(resultado)
    else:
        out = {"resultado": resultado, "exito": True}
    out["latencia_ms"] = ms
    out["progreso_requerido"] = ms >= MEDIA_PROGRESS_BUDGET_MS
    out["budget_ms"] = MEDIA_PROGRESS_BUDGET_MS
    out["system_guard"] = "media_budget_soft"
    if ms >= MEDIA_PROGRESS_BUDGET_MS:
        out["aviso_progreso"] = (
            "Generación superó 5s — mostrar Indicador de Progreso Visual."
        )
    return out
