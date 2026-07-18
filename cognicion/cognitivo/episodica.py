# -*- coding: utf-8 -*-
"""
Memoria Episódica — experiencia de vida (vectorial / JSON fallback).
Éxitos + correcciones de Israel → Chroma capa 'episodica'.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from cognicion.memoria.tipos import TipoMemoria

CAPA = TipoMemoria.EPISODICA.value
FRASE_APRENDIZAJE = "He aprendido de este error, no volverá a ocurrir."


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _memoria():
    from cognicion.memoria.vectorial import obtener_memoria

    return obtener_memoria()


def guardar_episodio(
    texto: str,
    *,
    tipo: str,
    session_id: str | None = None,
    causa_raiz: str = "",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """tipo: exito | correccion | incidente | consolidacion"""
    cuerpo = (texto or "").strip()
    if not cuerpo:
        return {"ok": False, "error": "episodio_vacio"}

    mem = _memoria()
    doc_id = f"ep_{tipo}_{uuid4().hex[:12]}"
    payload = cuerpo
    if causa_raiz:
        payload = f"{cuerpo}\nCausa raíz: {causa_raiz.strip()[:400]}"

    mid = mem.guardar(
        payload[:4000],
        metadata={
            "capa": CAPA,
            "tipo": tipo,
            "tipo_memoria": CAPA,
            "sesion_id": session_id or "global",
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
    return {
        "ok": bool(mid),
        "id": mid,
        "tipo": tipo,
        "capa": CAPA,
        "motor": getattr(mem, "motor", "unknown"),
    }


def recuperar_lecciones(consulta: str, *, n: int = 4, session_id: str | None = None) -> list[str]:
    mem = _memoria()
    if not mem.activa:
        return []
    hits = mem.buscar(consulta or "aprendizaje correccion error", n=max(n * 2, 6), session_id=session_id)
    lecciones: list[str] = []
    for h in hits:
        meta = h.get("metadata") or {}
        capa = str(meta.get("capa") or meta.get("tipo_memoria") or "")
        tipo = str(meta.get("tipo") or "")
        if capa != CAPA and tipo not in ("correccion", "incidente", "exito", "consolidacion"):
            # Aceptar si el texto habla de error/aprendizaje
            texto = (h.get("texto") or "").lower()
            if "aprend" not in texto and "error" not in texto and "correc" not in texto:
                continue
        t = (h.get("texto") or "").strip()
        if t:
            lecciones.append(t[:320])
        if len(lecciones) >= n:
            break
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
