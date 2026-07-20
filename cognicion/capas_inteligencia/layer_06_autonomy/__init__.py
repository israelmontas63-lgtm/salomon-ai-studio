# -*- coding: utf-8 -*-
"""
Capa 6 — Autonomía en segundo plano y enjambre de verificación factual.
Usa cola async + agentes paralelos existentes (fail-soft).
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import threading
import time
from typing import Any

_CACHE: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()
_CACHE_TTL_S = 600


def _cache_key(session_id: str | None, mensaje: str) -> str:
    sid = (session_id or "global").strip() or "global"
    tip = (mensaje or "").strip()[:160].lower()
    return f"{sid}::{tip}"


def get_cached_verification(session_id: str | None, mensaje: str) -> dict[str, Any] | None:
    key = _cache_key(session_id, mensaje)
    with _LOCK:
        pack = _CACHE.get(key)
        if not pack:
            return None
        if time.time() - float(pack.get("_ts") or 0) > _CACHE_TTL_S:
            _CACHE.pop(key, None)
            return None
        return dict(pack)


def _store_cache(session_id: str | None, mensaje: str, result: dict[str, Any]) -> None:
    key = _cache_key(session_id, mensaje)
    with _LOCK:
        data = dict(result)
        data["_ts"] = time.time()
        _CACHE[key] = data
        # Limitar tamaño
        if len(_CACHE) > 80:
            oldest = sorted(_CACHE.items(), key=lambda kv: kv[1].get("_ts", 0))[:20]
            for k, _ in oldest:
                _CACHE.pop(k, None)


def run_verification_swarm(
    mensaje: str,
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Enjambre de verificación paralelo (web/académico/mercado)."""
    from cognicion.core_salomon_master_neural_engine import obtener_master_neural

    engine = obtener_master_neural()
    if not engine.should_search_web(mensaje):
        return {
            "ok": False,
            "skipped": True,
            "reason": "no_factual_gap",
            "layer": 6,
        }
    pack = engine.deploy_agent_swarm(mensaje)
    result = {
        "ok": bool(pack.get("ok")),
        "bloque": pack.get("bloque") or "",
        "swarm": pack,
        "layer": 6,
        "via": "layer_06_verification_swarm",
        "session_id": session_id,
    }
    _store_cache(session_id, mensaje, result)
    return result


def schedule_background_verification(
    mensaje: str,
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    """
    Programa verificación en segundo plano (no bloquea la respuesta al usuario).
    Si ya hay caché fresca, la reutiliza.
    """
    cached = get_cached_verification(session_id, mensaje)
    if cached and cached.get("ok"):
        return {"ok": True, "scheduled": False, "cached": True, "result": cached}

    from cognicion.core_salomon_master_neural_engine import obtener_master_neural

    if not obtener_master_neural().should_search_web(mensaje):
        return {"ok": False, "scheduled": False, "skipped": True}

    try:
        from cognicion.cola import encolar

        encolar(run_verification_swarm, mensaje, session_id=session_id)
        return {
            "ok": True,
            "scheduled": True,
            "layer": 6,
            "via": "cola_background",
        }
    except Exception as exc:
        # Fallback sync ligero si la cola no está
        try:
            result = run_verification_swarm(mensaje, session_id=session_id)
            return {
                "ok": bool(result.get("ok")),
                "scheduled": False,
                "sync_fallback": True,
                "result": result,
                "error": type(exc).__name__,
            }
        except Exception as exc2:
            return {"ok": False, "error": type(exc2).__name__, "layer": 6}


def consume_background_block(
    mensaje: str,
    *,
    session_id: str | None = None,
) -> str:
    """Si el enjambre de fondo ya terminó, devuelve el bloque de contexto."""
    cached = get_cached_verification(session_id, mensaje)
    if cached and cached.get("bloque"):
        return str(cached["bloque"])
    return ""


def layer_six_status() -> dict[str, Any]:
    with _LOCK:
        n = len(_CACHE)
    return {
        "layer": 6,
        "name": "autonomy_verification_swarm",
        "cache_entries": n,
        "ttl_s": _CACHE_TTL_S,
        "ok": True,
    }
