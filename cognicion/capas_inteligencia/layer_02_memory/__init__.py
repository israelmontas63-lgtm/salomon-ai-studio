# -*- coding: utf-8 -*-
"""
Capa 2 — Memoria persistente e historial de chats.

Fuente de verdad: SQLite (WAL + BEGIN IMMEDIATE) vía `persistencia.sesiones`.
Resiliencia: caché RAM por session_id + fallback si la DB falla/latencia.
Aislamiento: no toca cámara, TTS ni razonamiento profundo (L1/L3/L4 hardware).
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Any, Deque, Final

LAYER_ID = 2
LAYER_NAME = "persistent_memory"

_log = logging.getLogger("salomon.layer_02_memory")

_CACHE_MAX_SESSIONS: Final[int] = 64
_CACHE_MAX_MSGS: Final[int] = 256
_SQLITE_TIMEOUT_HINT_S: Final[float] = 2.5

_cache_lock = threading.RLock()
# session_id → cola de {rol, contenido, ts}
_ram_history: dict[str, Deque[dict[str, str]]] = {}
_cache_meta: dict[str, dict[str, Any]] = {}

_FORBIDDEN: Final[frozenset[str]] = frozenset(
    {
        "getUserMedia",
        "closeCamera",
        "engageAnalyticalStreaming",
        "deploy_agent_swarm",
        "apply_supervision",
        "elevenlabs",
    }
)


def _cement_sid(session_id: Any) -> str | None:
    try:
        from cognicion.capas_inteligencia.synaptic_bus import cement_session_id

        return cement_session_id(session_id)
    except TypeError:
        return None
    except Exception:
        if session_id is None:
            return None
        if isinstance(session_id, str):
            sid = session_id.strip()
            return sid or None
        return None


def _cement_rol(rol: Any) -> str | None:
    try:
        from cognicion.capas_inteligencia.synaptic_bus import cement_turn_roles

        return cement_turn_roles(rol)
    except Exception:
        return None


def cache_push_message(
    session_id: Any,
    rol: Any,
    contenido: Any,
    *,
    timestamp: str | None = None,
) -> bool:
    """Actualiza caché RAM aislada por session_id (sin cruzar chats)."""
    sid = _cement_sid(session_id)
    role = _cement_rol(rol)
    if not sid or not role:
        return False
    if not isinstance(contenido, str) or not contenido:
        return False
    entry = {
        "rol": role,
        "contenido": contenido,
        "timestamp": timestamp or "",
    }
    with _cache_lock:
        q = _ram_history.get(sid)
        if q is None:
            # Eviction FIFO de sesiones si hay demasiadas
            if len(_ram_history) >= _CACHE_MAX_SESSIONS:
                oldest = next(iter(_ram_history))
                _ram_history.pop(oldest, None)
                _cache_meta.pop(oldest, None)
            q = deque(maxlen=_CACHE_MAX_MSGS)
            _ram_history[sid] = q
        q.append(entry)
        _cache_meta[sid] = {
            "updated_at": time.time(),
            "size": len(q),
            "source": "ram",
        }
    return True


def cache_load_messages(session_id: Any) -> list[dict[str, str]]:
    """Lectura rápida desde RAM (solo la session_id pedida)."""
    sid = _cement_sid(session_id)
    if not sid:
        return []
    with _cache_lock:
        q = _ram_history.get(sid)
        if not q:
            return []
        return [{"rol": m["rol"], "contenido": m["contenido"]} for m in q]


def cache_replace_session(session_id: Any, messages: list[dict[str, Any]]) -> None:
    """Hidrata/reemplaza caché tras lectura exitosa de SQLite."""
    sid = _cement_sid(session_id)
    if not sid:
        return
    clean: list[dict[str, str]] = []
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        role = _cement_rol(m.get("rol"))
        body = m.get("contenido")
        if not role or not isinstance(body, str) or not body:
            continue
        clean.append({"rol": role, "contenido": body, "timestamp": ""})
    with _cache_lock:
        q: Deque[dict[str, str]] = deque(clean[-_CACHE_MAX_MSGS:], maxlen=_CACHE_MAX_MSGS)
        if len(_ram_history) >= _CACHE_MAX_SESSIONS and sid not in _ram_history:
            oldest = next(iter(_ram_history))
            _ram_history.pop(oldest, None)
            _cache_meta.pop(oldest, None)
        _ram_history[sid] = q
        _cache_meta[sid] = {
            "updated_at": time.time(),
            "size": len(q),
            "source": "sqlite_hydrate",
        }


def cache_stats() -> dict[str, Any]:
    with _cache_lock:
        return {
            "sessions": len(_ram_history),
            "max_sessions": _CACHE_MAX_SESSIONS,
            "max_msgs": _CACHE_MAX_MSGS,
            "sizes": {k: len(v) for k, v in _ram_history.items()},
        }


def verify_sqlite_wal() -> dict[str, Any]:
    """Contrato: journal_mode=WAL + busy_timeout + transacciones IMMEDIATE."""
    try:
        from pathlib import Path

        root = Path(__file__).resolve().parents[3]
        body = (root / "persistencia" / "sesiones.py").read_text(
            encoding="utf-8", errors="replace"
        )
    except OSError as exc:
        return {"ok": False, "error": type(exc).__name__}

    checks = {
        "journal_mode_wal": "journal_mode=WAL" in body,
        "busy_timeout": "busy_timeout" in body,
        "begin_immediate": "BEGIN IMMEDIATE" in body,
        "guardar_mensaje": "def guardar_mensaje" in body,
        "cargar_mensajes": "def cargar_mensajes" in body,
        "cement_session": "cement_session_id" in body,
    }
    return {"ok": all(checks.values()), "checks": checks, "layer": LAYER_ID}


def save_message(
    session_id: Any,
    rol: Any,
    contenido: Any,
) -> dict[str, Any]:
    """
    Persistencia atómica: SQLite primero; caché RAM siempre (fail-soft).
    session_id tipado str|None — sin sid válido no escribe (anti cross-chat).
    """
    sid = _cement_sid(session_id)
    role = _cement_rol(rol)
    if not sid:
        return {"ok": False, "error": "session_id_invalido", "layer": LAYER_ID}
    if not role:
        return {"ok": False, "error": "rol_invalido", "layer": LAYER_ID}
    if not isinstance(contenido, str) or not contenido:
        return {"ok": False, "error": "contenido_vacio", "layer": LAYER_ID}

    # Caché anticipada: resiliencia si SQLite falla tras el intento
    cache_push_message(sid, role, contenido)

    t0 = time.perf_counter()
    try:
        from persistencia.sesiones import guardar_mensaje

        guardar_mensaje(sid, role, contenido)
        elapsed = time.perf_counter() - t0
        return {
            "ok": True,
            "session_id": sid,
            "rol": role,
            "source": "sqlite",
            "elapsed_ms": round(elapsed * 1000, 2),
            "layer": LAYER_ID,
            "fallback": False,
        }
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        _log.warning(
            "layer_02.save_message: SQLite falló session=%s (%s) — RAM cache activa",
            sid,
            type(exc).__name__,
        )
        return {
            "ok": True,
            "session_id": sid,
            "rol": role,
            "source": "ram_cache",
            "elapsed_ms": round(elapsed * 1000, 2),
            "layer": LAYER_ID,
            "fallback": True,
            "error": type(exc).__name__,
        }


def load_messages(session_id: Any) -> dict[str, Any]:
    """
    Carga historial: SQLite (fuente de verdad) → hidrata RAM.
    Si DB latente/caída → fallback RAM (misma session_id únicamente).
    """
    sid = _cement_sid(session_id)
    if not sid:
        return {
            "ok": False,
            "session_id": None,
            "messages": [],
            "error": "session_id_invalido",
            "layer": LAYER_ID,
        }

    t0 = time.perf_counter()
    try:
        from persistencia.sesiones import cargar_mensajes

        msgs = cargar_mensajes(sid)
        elapsed = time.perf_counter() - t0
        if not isinstance(msgs, list):
            msgs = []
        cache_replace_session(sid, msgs)
        # Latencia alta: aún devolvemos SQLite pero marcamos hint
        slow = elapsed > _SQLITE_TIMEOUT_HINT_S
        return {
            "ok": True,
            "session_id": sid,
            "messages": msgs,
            "source": "sqlite",
            "elapsed_ms": round(elapsed * 1000, 2),
            "slow": slow,
            "layer": LAYER_ID,
            "fallback": False,
        }
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        cached = cache_load_messages(sid)
        _log.warning(
            "layer_02.load_messages: SQLite falló session=%s (%s) — fallback RAM n=%s",
            sid,
            type(exc).__name__,
            len(cached),
        )
        # Segundo intento: vectorial/episódica solo como pista (no mezcla session)
        if not cached:
            cached = _vectorial_session_hint(sid)
        return {
            "ok": bool(cached),
            "session_id": sid,
            "messages": cached,
            "source": "ram_cache" if cached else "empty",
            "elapsed_ms": round(elapsed * 1000, 2),
            "layer": LAYER_ID,
            "fallback": True,
            "error": type(exc).__name__,
        }


def load_recent(session_id: Any, limite: int = 16) -> dict[str, Any]:
    """Memoria inmediata L2→L3: últimos N turnos, session_id estricto."""
    sid = _cement_sid(session_id)
    if not sid:
        return {
            "ok": False,
            "session_id": None,
            "messages": [],
            "error": "session_id_invalido",
            "layer": LAYER_ID,
        }
    lim = max(1, min(int(limite or 16), 64))
    t0 = time.perf_counter()
    try:
        from persistencia.sesiones import ultimos_mensajes

        msgs = ultimos_mensajes(sid, lim)
        elapsed = time.perf_counter() - t0
        return {
            "ok": True,
            "session_id": sid,
            "messages": msgs if isinstance(msgs, list) else [],
            "source": "sqlite",
            "elapsed_ms": round(elapsed * 1000, 2),
            "layer": LAYER_ID,
            "fallback": False,
        }
    except Exception as exc:
        cached = cache_load_messages(sid)[-lim:]
        return {
            "ok": bool(cached),
            "session_id": sid,
            "messages": cached,
            "source": "ram_cache",
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
            "layer": LAYER_ID,
            "fallback": True,
            "error": type(exc).__name__,
        }


def _vectorial_session_hint(session_id: str) -> list[dict[str, str]]:
    """Fallback terciario: no inventa historial; solo señales de sesión si existen."""
    try:
        from cognicion.memoria.vectorial import obtener_memoria

        mem = obtener_memoria()
        if not getattr(mem, "activa", False):
            return []
        hits = mem.buscar(
            "historial chat mensaje",
            n=4,
            session_id=session_id,
        ) or []
        out: list[dict[str, str]] = []
        for h in hits:
            if not isinstance(h, dict):
                continue
            meta = h.get("metadata") if isinstance(h.get("metadata"), dict) else {}
            sid = str(meta.get("sesion_id") or meta.get("session_id") or "")
            if sid and sid != session_id:
                continue
            texto = (h.get("texto") or "").strip()
            if texto:
                out.append({"rol": "asistente", "contenido": texto[:500]})
        return out
    except Exception:
        return []


def ensure_ready() -> dict[str, Any]:
    """Inicializa esquema SQLite (idempotente)."""
    try:
        from persistencia.sesiones import inicializar

        inicializar()
        wal = verify_sqlite_wal()
        return {"ok": bool(wal.get("ok")), "wal": wal, "layer": LAYER_ID}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__, "layer": LAYER_ID}


def seal_boundaries() -> dict[str, Any]:
    """Contrato de aislamiento Capa 2."""
    try:
        with open(__file__, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError:
        src = ""
    breaches = [n for n in _FORBIDDEN if f"{n}(" in src]
    wal = verify_sqlite_wal()
    return {
        "layer": LAYER_ID,
        "name": LAYER_NAME,
        "owns": [
            "sqlite_wal_sessions",
            "chat_history_load_save",
            "ram_history_cache",
            "session_id_cement",
        ],
        "must_not": sorted(_FORBIDDEN),
        "source_of_truth": "persistencia.sesiones (SQLite WAL)",
        "breaches": breaches,
        "wal": wal,
        "ok": not breaches and bool(wal.get("ok")),
    }


def layer_two_status() -> dict[str, Any]:
    boundaries = seal_boundaries()
    return {
        "layer": LAYER_ID,
        "name": LAYER_NAME,
        "ok": bool(boundaries.get("ok")),
        "boundaries": boundaries,
        "cache": cache_stats(),
        "ready": ensure_ready(),
    }
