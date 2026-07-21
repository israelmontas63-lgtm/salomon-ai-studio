# -*- coding: utf-8 -*-
"""
Memoria Episódica — ruta canónica (`cognicion.episodica`).

Experiencia de vida (vectorial / JSON + caché RAM PWA).
Éxitos + correcciones de Israel → Chroma capa 'episodica'.

Compat: `cognicion.cognitivo.episodica` reexporta este módulo.
"""

from __future__ import annotations

import logging
import re
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque
from uuid import uuid4

from cognicion.memoria.tipos import TipoMemoria

CAPA = TipoMemoria.EPISODICA.value
FRASE_APRENDIZAJE = "He aprendido de este error, no volverá a ocurrir."

_log = logging.getLogger("salomon.episodica")

_CACHE_MAX: int = 64
_cache_lock = threading.Lock()
_ram_cache: Deque[dict[str, Any]] = deque(maxlen=_CACHE_MAX)

_RE_TOKENS = re.compile(r"[a-záéíóúñü0-9_\-]{2,}", re.IGNORECASE)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _memoria() -> Any:
    from cognicion.memoria.vectorial import obtener_memoria

    return obtener_memoria()


def _tokens(texto: str) -> list[str]:
    return [m.group(0).lower() for m in _RE_TOKENS.finditer(texto or "")]


def _cache_push(entry: dict[str, Any]) -> None:
    with _cache_lock:
        _ram_cache.appendleft(entry)


def _cache_buscar(consulta: str, *, n: int, session_id: str | None) -> list[str]:
    tokens = [t for t in _tokens(consulta) if len(t) >= 3][:12]
    out: list[str] = []
    with _cache_lock:
        items = list(_ram_cache)
    for item in items:
        sid = str(item.get("session_id") or "global")
        if session_id and sid not in (session_id, "global"):
            continue
        texto = str(item.get("texto") or "")
        if not texto:
            continue
        baja = texto.lower()
        tipo = str(item.get("tipo") or "")
        if tokens and not any(t in baja for t in tokens):
            if tipo not in ("correccion", "incidente", "exito", "consolidacion"):
                continue
        out.append(texto[:320])
        if len(out) >= n:
            break
    return out


def guardar_episodio(
    texto: str,
    *,
    tipo: str,
    session_id: str | None = None,
    causa_raiz: str = "",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cuerpo = (texto or "").strip()
    if not cuerpo:
        _log.warning("episodica.guardar_episodio: episodio_vacio")
        return {"ok": False, "error": "episodio_vacio"}

    doc_id = f"ep_{tipo}_{uuid4().hex[:12]}"
    payload = cuerpo
    if causa_raiz:
        payload = f"{cuerpo}\nCausa raíz: {causa_raiz.strip()[:400]}"

    sid = session_id or "global"
    cache_entry: dict[str, Any] = {
        "id": doc_id,
        "texto": payload[:4000],
        "tipo": tipo,
        "capa": CAPA,
        "session_id": sid,
        "causa_raiz": (causa_raiz or "")[:200],
        "at": _utc(),
    }
    _cache_push(cache_entry)

    try:
        mem = _memoria()
    except Exception as exc:
        _log.warning(
            "episodica.guardar_episodio: motor_indisponible (%s) — usando solo caché RAM",
            type(exc).__name__,
        )
        return {
            "ok": True,
            "id": doc_id,
            "tipo": tipo,
            "capa": CAPA,
            "motor": "ram_cache",
            "fallback": True,
        }

    if not getattr(mem, "activa", False):
        _log.warning(
            "episodica.guardar_episodio: mem.activa=False — persistencia degradada a caché RAM id=%s",
            doc_id,
        )
        return {
            "ok": True,
            "id": doc_id,
            "tipo": tipo,
            "capa": CAPA,
            "motor": "ram_cache",
            "fallback": True,
        }

    try:
        mid = mem.guardar(
            payload[:4000],
            metadata={
                "capa": CAPA,
                "tipo": tipo,
                "tipo_memoria": CAPA,
                "sesion_id": sid,
                "owner": "Israel Montas",
                "at": _utc(),
                **{
                    k: v
                    for k, v in (meta or {}).items()
                    if isinstance(v, (str, int, float, bool))
                },
            },
            doc_id=doc_id,
        )
    except Exception as exc:
        _log.warning(
            "episodica.guardar_episodio: fallo vectorial (%s) — caché RAM activa",
            type(exc).__name__,
        )
        return {
            "ok": True,
            "id": doc_id,
            "tipo": tipo,
            "capa": CAPA,
            "motor": "ram_cache",
            "fallback": True,
            "error": type(exc).__name__,
        }

    return {
        "ok": bool(mid),
        "id": mid or doc_id,
        "tipo": tipo,
        "capa": CAPA,
        "motor": getattr(mem, "motor", "vectorial"),
        "fallback": False,
    }


def recuperar_lecciones(
    consulta: str,
    *,
    n: int = 4,
    session_id: str | None = None,
) -> list[str]:
    n_safe = max(1, min(int(n or 4), 12))
    consulta_safe = (consulta or "aprendizaje correccion error").strip()

    lecciones: list[str] = []

    try:
        mem = _memoria()
    except Exception as exc:
        _log.warning(
            "episodica.recuperar_lecciones: no se pudo obtener motor vectorial (%s) — fallback RAM",
            type(exc).__name__,
        )
        return _cache_buscar(consulta_safe, n=n_safe, session_id=session_id)

    if not getattr(mem, "activa", False):
        _log.warning(
            "episodica.recuperar_lecciones: mem.activa=False — alertando y usando caché RAM PWA"
        )
        return _cache_buscar(consulta_safe, n=n_safe, session_id=session_id)

    hits: list[Any] = []
    try:
        raw = mem.buscar(
            consulta_safe,
            n=max(n_safe * 2, 6),
            session_id=session_id,
        )
        hits = list(raw or [])
    except Exception as exc:
        _log.warning(
            "episodica.recuperar_lecciones: buscar() falló (%s) — reintento caché RAM",
            type(exc).__name__,
        )
        return _cache_buscar(consulta_safe, n=n_safe, session_id=session_id)

    for h in hits:
        if not isinstance(h, dict):
            continue
        meta = h.get("metadata") or {}
        if not isinstance(meta, dict):
            meta = {}
        capa = str(meta.get("capa") or meta.get("tipo_memoria") or "")
        tipo = str(meta.get("tipo") or "")
        if capa != CAPA and tipo not in ("correccion", "incidente", "exito", "consolidacion"):
            texto = (h.get("texto") or "").lower()
            if "aprend" not in texto and "error" not in texto and "correc" not in texto:
                continue
        t = (h.get("texto") or "").strip()
        if t:
            lecciones.append(t[:320])
        if len(lecciones) >= n_safe:
            break

    if not lecciones:
        _log.warning(
            "episodica.recuperar_lecciones: vectorial sin hits — fallback caché RAM (consulta=%r)",
            consulta_safe[:80],
        )
        lecciones = _cache_buscar(consulta_safe, n=n_safe, session_id=session_id)

    return lecciones


def es_correccion_usuario(mensaje: str) -> bool:
    t = (mensaje or "").lower()
    claves = (
        "está mal",
        "esta mal",
        "te equivoc",
        "incorrecto",
        "no es eso",
        "corrige",
        "otra vez fall",
        "no vuelvas",
        "error tuyo",
        "fallaste",
    )
    return any(k in t for k in claves)


def estado_cache_ram() -> dict[str, Any]:
    with _cache_lock:
        size = len(_ram_cache)
        tipos = [str(x.get("tipo") or "") for x in _ram_cache]
    return {
        "size": size,
        "max": _CACHE_MAX,
        "tipos": tipos[:16],
        "activa": size > 0,
    }
