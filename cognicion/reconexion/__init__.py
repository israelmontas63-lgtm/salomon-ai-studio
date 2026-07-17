# -*- coding: utf-8 -*-
"""
Reconexión de Emergencia v104 — puertos, memoria, periféricos, gateway web.

Corrige desconexiones críticas sin tocar CameraEngine (Golden State).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cognicion.identidad import CREADOR, FIRMA_OWNERSHIP

ROOT = Path(__file__).resolve().parents[2]
VERSION = "105.0.0"


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def puerto_canonico(valor: int | str | None = None) -> int:
    """
    Puerto dinámico de alta disponibilidad.
    - Tipografía 800 → 8000
    - En Render / producción: PORT
    - Local: COLSUB_PORT o primer puerto libre desde 8000
    """
    raw = valor
    if raw is None:
        raw = os.getenv("PORT") or os.getenv("COLSUB_PORT")
    if raw is not None and str(raw).strip() != "":
        try:
            p = int(str(raw).strip())
        except Exception:
            p = 8000
        if p == 800:
            p = 8000
        if 1 <= p <= 65535:
            return p
    # Alta disponibilidad local: buscar puerto libre
    import socket

    for candidate in (8000, 8001, 8080, 8888, 10000):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("0.0.0.0", candidate))
                return candidate
        except OSError:
            continue
    return 8000


def reiniciar_memoria() -> dict[str, Any]:
    """Reinstancia memoria vectorial (+ fallback JSON) y prueba R/W."""
    from cognicion.memoria.vectorial import reiniciar_instancia, obtener_memoria

    reiniciar_instancia()
    mem = obtener_memoria()
    eco_id = None
    hits: list[Any] = []
    if mem.activa:
        eco_id = mem.guardar(
            "v104 eco reconexion memoria — lectura/escritura OK",
            metadata={"tipo": "eco", "capa": "corto", "protocolo": "v104"},
        )
        hits = mem.buscar("v104 eco reconexion memoria", top_k=3)
    return {
        "ok": bool(mem.activa and eco_id),
        "activa": mem.activa,
        "motor": getattr(mem, "motor", "chroma"),
        "eco_id": eco_id,
        "hits": len(hits or []),
        "puerto_memoria": "local_filesystem",  # nunca HttpClient :800
    }


def probar_gateway_web() -> dict[str, Any]:
    """Prueba de búsqueda web (Tavily / Wikipedia / DDG)."""
    from cognicion.busqueda.agente import buscar_web

    pack = buscar_web("tecnologia inteligencia artificial 2026")
    return {
        "ok": bool(pack.get("exito")),
        "motor": pack.get("motor"),
        "resultados": len(pack.get("resultados") or []),
        "tiene_respuesta": bool(pack.get("respuesta_directa") or pack.get("exito")),
        "error": pack.get("error"),
    }


def estado_perifericos_config() -> dict[str, Any]:
    """Config de I/O — micrófono/cámara vía MediaDevices (cliente)."""
    return {
        "ok": True,
        "media_devices_api": "navigator.mediaDevices.getUserMedia",
        "camera_engine": "/camera-engine.js?v=20.1",
        "reconexion_js": "/reconexion-perifericos.js?v=104",
        "dictado": "audio:true via getUserMedia + SpeechRecognition si disponible",
        "security_kernel": "audio-only priorizado en emergencia (sin tocar Golden Camera)",
        "nota": "Permisos reales se otorgan en el navegador/PWA (HTTPS o localhost).",
    }


def ejecutar_reconexion_emergencia() -> dict[str, Any]:
    """Protocolo completo + prueba de eco."""
    puerto = puerto_canonico()
    # Alinear env para procesos hijos / BCA
    os.environ["COLSUB_PORT"] = str(puerto)
    if not os.getenv("PORT"):
        os.environ.setdefault("PORT", str(puerto))

    memoria = reiniciar_memoria()
    web = probar_gateway_web()
    peri = estado_perifericos_config()

    eco_ok = bool(memoria.get("ok") and web.get("ok") and peri.get("ok"))
    return {
        "ok": eco_ok,
        "protocol": "RECONEXION_EMERGENCIA_PUERTOS_PERIFERICOS",
        "version": VERSION,
        "creador": CREADOR,
        "firma": FIRMA_OWNERSHIP,
        "at": _utc(),
        "puerto": {
            "canonico": puerto,
            "remap_800_a_8000": True,
            "host": os.getenv("COLSUB_HOST", "0.0.0.0"),
            "render_port_env": os.getenv("PORT"),
        },
        "memoria": memoria,
        "gateway_web": web,
        "perifericos": peri,
        "service_worker": {
            "external_pass_through": True,
            "nota": "SW no intercepta orígenes externos; /api/busqueda = network-only",
        },
        "estado": (
            "CONECTIVIDAD RESTABLECIDA - TODOS LOS SISTEMAS ACTIVOS"
            if eco_ok
            else "RECONEXION_PARCIAL - revisar fallos"
        ),
        "eco": {
            "memoria_rw": bool(memoria.get("ok")),
            "busqueda_web": bool(web.get("ok")),
            "perifericos_config": bool(peri.get("ok")),
        },
    }


def estado_conectividad() -> dict[str, Any]:
    """Estado ligero sin reescribir memoria (para /api/salud)."""
    try:
        from cognicion.memoria.vectorial import obtener_memoria

        mem_ok = obtener_memoria().activa
        motor = getattr(obtener_memoria(), "motor", "chroma")
    except Exception:
        mem_ok = False
        motor = "offline"
    return {
        "protocol": "RECONEXION_EMERGENCIA_PUERTOS_PERIFERICOS",
        "version": VERSION,
        "active": True,
        "puerto_canonico": puerto_canonico(),
        "memoria_activa": mem_ok,
        "memoria_motor": motor,
        "gateway_web": True,
        "perifericos_js": "/reconexion-perifericos.js?v=104",
        "creador": CREADOR,
    }
