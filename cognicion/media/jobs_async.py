# -*- coding: utf-8 -*-
"""
Cola asíncrona de media — low-footprint para Render Free.
La UI no espera el HTTP largo; consulta GET /api/media/jobs/{id}.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

_LOCK = threading.Lock()
_JOBS: dict[str, dict[str, Any]] = {}
_MAX_JOBS = 8


def _limpiar_viejos() -> None:
    if len(_JOBS) <= _MAX_JOBS:
        return
    orden = sorted(_JOBS.items(), key=lambda kv: kv[1].get("creado", 0))
    for jid, _ in orden[: max(0, len(_JOBS) - _MAX_JOBS)]:
        _JOBS.pop(jid, None)


def encolar_media(
    prompt: str,
    *,
    hint: str | None = "imagen_hd",
    motor: str | None = None,
) -> dict[str, Any]:
    job_id = uuid.uuid4().hex[:12]
    job = {
        "id": job_id,
        "estado": "en_cola",
        "creado": time.time(),
        "prompt": (prompt or "")[:400],
        "hint": hint,
        "resultado": None,
        "error": None,
        "progreso": "En cola (Ultra-Light)…",
    }
    with _LOCK:
        _limpiar_viejos()
        _JOBS[job_id] = job

    def _worker() -> None:
        with _LOCK:
            j = _JOBS.get(job_id)
            if not j:
                return
            j["estado"] = "procesando"
            j["progreso"] = "Mejorando prompt / generando…"
        try:
            from cognicion.media.media_engine import bridge_colsub_media
            from cognicion.eficiencia import hibernar_agentes

            pack = bridge_colsub_media(
                prompt,
                hint=hint,
                forzar_motor=motor,
            )
            with _LOCK:
                j = _JOBS.get(job_id)
                if not j:
                    return
                j["estado"] = "listo" if pack.get("exito") else "error"
                j["resultado"] = pack
                j["error"] = (pack.get("resultado") or {}).get("error") or pack.get("error")
                j["progreso"] = "Listo" if pack.get("exito") else "Error"
                j["latencia_ms"] = pack.get("latencia_ms")
            hibernar_agentes()
        except Exception as exc:
            with _LOCK:
                j = _JOBS.get(job_id)
                if j:
                    j["estado"] = "error"
                    j["error"] = f"{type(exc).__name__}: {exc}"
                    j["progreso"] = "Error"
            try:
                from cognicion.eficiencia import hibernar_agentes

                hibernar_agentes()
            except Exception:
                pass

    t = threading.Thread(target=_worker, name=f"media-job-{job_id}", daemon=True)
    t.start()
    return {
        "exito": True,
        "async": True,
        "job_id": job_id,
        "estado": "en_cola",
        "poll": f"/api/media/jobs/{job_id}",
        "protocolo": "MAX_EFFICIENCY",
        "aviso": "Procesamiento asíncrono — la UI no se congela.",
    }


def estado_job(job_id: str) -> dict[str, Any] | None:
    with _LOCK:
        j = _JOBS.get(job_id)
        if not j:
            return None
        return {
            "id": j["id"],
            "estado": j["estado"],
            "progreso": j.get("progreso"),
            "error": j.get("error"),
            "latencia_ms": j.get("latencia_ms"),
            "resultado": j.get("resultado"),
            "espera_s": round(time.time() - j.get("creado", time.time()), 2),
            "async": True,
        }
