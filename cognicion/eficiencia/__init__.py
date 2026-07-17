# -*- coding: utf-8 -*-
"""
Máxima Eficiencia v95 — Render Free Tier (Ultra-Light).

Logic-first: sin librerías nuevas. Hibernación de agentes, GC agresivo,
límites de sesión y presupuesto de RAM.
"""

from __future__ import annotations

import gc
import os
from typing import Any


def render_free_tier() -> bool:
    try:
        from settings import RENDER_FREE_TIER

        return bool(RENDER_FREE_TIER)
    except Exception:
        return os.getenv("RENDER_FREE_TIER", "true").strip().lower() in {
            "1", "true", "yes", "on",
        }


def hibernar_agentes() -> dict[str, Any]:
    """Descarga instancias en memoria de agentes y fuerza GC."""
    liberados: list[str] = []
    try:
        import cognicion.agente.coder as coder

        if getattr(coder, "_autonomo", None) is not None:
            coder._autonomo = None
            liberados.append("Agent_Coder")
    except Exception:
        pass
    # Forzar recolección
    n = gc.collect()
    return {
        "hibernados": liberados,
        "gc": n,
        "protocolo": "MAX_EFFICIENCY",
        "version": "95.0.0",
    }


def podar_sesiones(sesiones: dict, max_sesiones: int = 2) -> int:
    """LRU simple: elimina las más antiguas si hay demasiadas (por orden de inserción)."""
    if max_sesiones < 1:
        max_sesiones = 1
    extra = len(sesiones) - max_sesiones
    if extra <= 0:
        return 0
    keys = list(sesiones.keys())
    removed = 0
    for k in keys[:extra]:
        sesiones.pop(k, None)
        removed += 1
    if removed:
        gc.collect()
    return removed


def estado_eficiencia() -> dict[str, Any]:
    from settings import (
        COLSUB_MAX_AGENTES,
        COLSUB_MAX_WORKERS,
        MEDIA_HTTP_TIMEOUT,
        MAX_SESIONES_RAM,
    )

    return {
        "protocol": "MAX_EFFICIENCY",
        "version": "95.0.0",
        "parent_protocol": "MULTI_AGENT_DEPLOY",
        "active": True,
        "render_free_tier": render_free_tier(),
        "logic_first": True,
        "no_heavy_libs": True,
        "hibernacion_agentes": True,
        "media_async": True,
        "media_http_timeout_s": MEDIA_HTTP_TIMEOUT,
        "max_sesiones_ram": MAX_SESIONES_RAM,
        "colsub_caps": {
            "max_agentes": COLSUB_MAX_AGENTES,
            "max_workers": COLSUB_MAX_WORKERS,
        },
        "ram_target": "bajo_limite_free_tier",
        "listo_free_tier": True,
    }
