# -*- coding: utf-8 -*-
"""
Hilos de conversación — cada session_id = un contexto propio.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mente.arquitectura import HILOS_DIR, asegurar_estructura

_log = logging.getLogger("salomon.mente.hilos")


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path(session_id: str) -> Path:
    asegurar_estructura()
    safe = "".join(
        c if c.isalnum() or c in "-_" else "_" for c in (session_id or "default")
    )
    return HILOS_DIR / f"{safe}.json"


def cargar_hilo(session_id: str) -> dict[str, Any]:
    path = _path(session_id)
    if not path.is_file():
        return {
            "session_id": session_id or "default",
            "creado_at": _utc(),
            "actualizado_at": _utc(),
            "area_activa": "razonamiento",
            "turnos": [],
            "hechos": [],
            "estado": "nuevo",
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        _log.warning("mente.hilos: JSON no-dict en %s — reiniciando hilo", path)
    except Exception:
        _log.warning(
            "mente.hilos: lectura falló path=%s session=%s",
            path,
            session_id,
            exc_info=True,
        )
    return {
        "session_id": session_id or "default",
        "creado_at": _utc(),
        "actualizado_at": _utc(),
        "area_activa": "razonamiento",
        "turnos": [],
        "hechos": [],
        "estado": "recuperado",
    }


def guardar_hilo(hilo: dict[str, Any]) -> None:
    path = _path(str(hilo.get("session_id") or "default"))
    hilo["actualizado_at"] = _utc()
    try:
        from cognicion.memoria.atomic_json import atomic_write_json

        if not atomic_write_json(path, hilo):
            _log.warning("mente.hilos: atomic_write falló path=%s", path)
    except Exception:
        _log.warning(
            "mente.hilos: escritura falló path=%s",
            path,
            exc_info=True,
        )


def borrar_hilo(session_id: str) -> bool:
    """Elimina el archivo de hilo de una sesión (reset limpio)."""
    path = _path(session_id)
    try:
        if path.is_file():
            path.unlink()
        lock = path.with_suffix(path.suffix + ".lock")
        if lock.is_file():
            lock.unlink()
        return True
    except Exception:
        _log.warning("mente.hilos: borrar falló session=%s", session_id, exc_info=True)
        return False


def registrar_turno(
    session_id: str,
    *,
    rol: str,
    texto: str,
    area: str = "razonamiento",
) -> dict[str, Any]:
    hilo = cargar_hilo(session_id)
    hilo["area_activa"] = area
    hilo.setdefault("turnos", []).append(
        {
            "at": _utc(),
            "rol": rol,
            "texto": (texto or "")[:4000],
            "area": area,
        }
    )
    if len(hilo["turnos"]) > 80:
        hilo["turnos"] = hilo["turnos"][-80:]
    hilo["estado"] = "activo"
    guardar_hilo(hilo)
    return hilo


def contexto_hilo(session_id: str, *, limite: int = 12) -> str:
    """Bloque de contexto del hilo actual (para el cerebro)."""
    hilo = cargar_hilo(session_id)
    turnos = hilo.get("turnos") or []
    if not turnos:
        return ""
    lineas = ["[Hilo semántico — conversación activa con Israel Monta]"]
    for t in turnos[-limite:]:
        quien = "Israel" if t.get("rol") == "usuario" else "Salomón"
        lineas.append(f"{quien}: {(t.get('texto') or '')[:500]}")
    lineas.append(
        "Instrucción: Continúa este hilo. No inventes temas externos. "
        "No busques películas ni web salvo orden canónica."
    )
    return "\n".join(lineas)


def clasificar_area(mensaje: str, *, tiene_imagen: bool = False) -> str:
    from config.vision_integration import es_instruccion_visual
    from config.memory_cortex import pedido_busqueda_explicito

    t = (mensaje or "").lower()
    if tiene_imagen or es_instruccion_visual(mensaje):
        return "vision"
    if any(x in t for x in ("micrófono", "microfono", "dictado", "escucha", "voz")):
        return "voz"
    if pedido_busqueda_explicito(mensaje):
        return "razonamiento"
    return "razonamiento"
