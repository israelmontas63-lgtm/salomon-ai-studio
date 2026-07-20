# -*- coding: utf-8 -*-
"""
Motor de análisis detallado (macro y micro visual).
Prohibido importar UI o templates aquí.
"""

from __future__ import annotations

from typing import Any


def analyze_frame_modes(focus_mode: str, frame: dict[str, Any]) -> dict[str, Any]:
    """
    Prepara metadatos de análisis macro/micro.
    El razonamiento pesado lo hace el cerebro vía brain_bridge + cognicion.vision.
    """
    mode = (focus_mode or "continuous").lower()
    scale = {
        "macro": {"zoom_hint": 2.4, "detail": "high", "scene": "near"},
        "micro": {"zoom_hint": 0.85, "detail": "context", "scene": "wide"},
        "continuous": {"zoom_hint": 1.0, "detail": "balanced", "scene": "adaptive"},
    }.get(mode, {"zoom_hint": 1.0, "detail": "balanced", "scene": "adaptive"})

    return {
        "layer": "macro_micro_engine",
        "path": "views/analysis/",
        "focus_mode": mode,
        "resolution_mode": "adaptive_ultra",
        "context_retention": True,
        "frame_ok": bool(frame.get("ok")),
        "frame_bytes": frame.get("bytes") or 0,
        "scale": scale,
        # Hook opcional a VDCP / analizador sin acoplar UI
        "pipeline": "macro_micro_dynamic",
    }


def run_scene_analysis(
    imagen_base64: str,
    *,
    mime: str = "image/jpeg",
    prompt: str = "",
) -> dict[str, Any]:
    """Análisis local vía cognicion.vision (sin UI)."""
    from cognicion.vision import analizar_imagen

    resultado = analizar_imagen(
        imagen_base64,
        mime_type=mime,
        contexto_usuario=prompt or "",
    )
    return {
        "layer": "macro_micro_engine",
        "texto": getattr(resultado, "contexto", None) or "",
        "ok": bool(getattr(resultado, "exito", False)),
        "error": getattr(resultado, "error", None),
    }


def analysis_layer_status() -> dict[str, Any]:
    return {
        "layer": "macro_micro_engine",
        "path": "views/analysis/",
        "role": "macro_micro_visual",
        "mixes_with_ui": False,
    }
