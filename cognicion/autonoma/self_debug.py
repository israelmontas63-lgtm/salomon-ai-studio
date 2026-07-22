# -*- coding: utf-8 -*-
"""
Self-Debug — autodiagnóstico y autoreparación SEGURA (autopreservación).

NO reescribe archivos fuente del proyecto (Ley Cero / no-regresión).
Sí: registra trazas, clasifica fallos, aplica reparaciones conocidas
(circuit breakers, reload-env, failover) y propone parches en ledger.
"""

from __future__ import annotations

import json
import threading
import time
import traceback
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from settings import DATA_DIR, ROOT_DIR

_LEDGER = Path(DATA_DIR) / "self_debug_ledger.jsonl"
_LOCK = threading.RLock()
_RECIENTES: deque[dict[str, Any]] = deque(maxlen=80)
_STATS = {
    "capturados": 0,
    "reparaciones_ok": 0,
    "reparaciones_fail": 0,
    "propuestas": 0,
}


def _leer_version() -> str:
    try:
        raw = json.loads((Path(ROOT_DIR) / "version.json").read_text(encoding="utf-8"))
        return str(raw.get("version") or "110.22.3")
    except Exception:
        return "110.22.3"


_VERSION = _leer_version()


@dataclass
class EventoFallo:
    ts: str
    origen: str
    tipo: str
    mensaje: str
    status_http: int | None = None
    traceback: str = ""
    path: str | None = None
    categoria: str = "desconocido"
    reparacion: dict[str, Any] = field(default_factory=dict)
    propuesta: str | None = None


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_ledger(entry: dict[str, Any]) -> bool:
    try:
        _LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            with _LEDGER.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False


def clasificar_fallo(
    exc: BaseException | None = None,
    *,
    status_http: int | None = None,
    mensaje: str = "",
) -> str:
    """Categoría estable para routing de reparación."""
    texto = f"{type(exc).__name__ if exc else ''} {mensaje} {status_http or ''}".lower()
    if status_http in (401, 403) or "invalid api key" in texto or "authentication" in texto:
        return "auth_key"
    if status_http == 402 or "insufficient balance" in texto or "payment" in texto:
        return "saldo"
    if status_http == 429 or "rate limit" in texto or "quota" in texto or "resource_exhausted" in texto:
        return "cuota"
    # Multimedia antes que timeout genérico (p.ej. "elevenlabs timeout")
    if any(x in texto for x in ("tts", "elevenlabs", "cartesia", "voice")):
        return "multimedia_tts"
    if any(x in texto for x in ("fal", "replicate", "dall", "imagen", "media", "video")):
        return "multimedia_media"
    if any(x in texto for x in ("deepgram", "stt", "microphone", "mic")):
        return "multimedia_stt"
    if any(x in texto for x in ("vision", "camera", "opencv", "frame")):
        return "vision"
    if status_http in (500, 502, 503, 504) or "timeout" in texto or "timed out" in texto:
        return "red_transitoria"
    if any(x in texto for x in ("syntax", "indent", "import error", "modulenotfound")):
        return "codigo"
    if any(x in texto for x in ("gemini", "deepseek", "openai", "groq", "llm", "openrouter")):
        return "llm"
    if status_http and 400 <= status_http < 500:
        return "cliente_http"
    if status_http and status_http >= 500:
        return "servidor_http"
    return "desconocido"


def _propuesta_para(categoria: str, origen: str) -> str:
    mapa = {
        "auth_key": (
            f"Revisar API key del motor en origen={origen}. "
            "Acción segura: POST /api/llm/reload-env o sync Render."
        ),
        "saldo": (
            "Saldo insuficiente en proveedor (p.ej. DeepSeek 402). "
            "Failover automático a siguiente LLM; recargar saldo en panel del proveedor."
        ),
        "cuota": (
            "Cuota/429 detectada. Abrir circuit breaker temporal y rotar proveedor "
            "(Gemini→DeepSeek→OpenRouter→Groq)."
        ),
        "red_transitoria": (
            "Error de red/timeout. Reintentar con backoff; no reescribir código."
        ),
        "multimedia_tts": (
            "Fallo TTS. Verificar ELEVENLABS_API_KEY / Voice ID Adam; "
            "reintentar /api/tts o Cartesia si existe."
        ),
        "multimedia_media": (
            "Fallo imagen/video. Cadena Fal→Replicate→DALL·E vía Smart Router; "
            "POST /api/media/generar_imagen con usar_routing=true."
        ),
        "multimedia_stt": "Fallo STT Deepgram. Verificar DEEPGRAM_API_KEY y reintentar /api/stt.",
        "vision": (
            "Fallo visión/cámara. Revisar permisos getUserMedia y "
            "/api/vision/brain-bridge; no tocar motor de visión UI."
        ),
        "codigo": (
            "Anomalía de código detectada. Autopreservación: NO auto-editar fuentes. "
            "Registrar traza y proponer patch humano/Cursor."
        ),
        "llm": "Fallo LLM. Usar cascada Smart Router / chat_con_historial con preferir.",
        "cliente_http": "HTTP 4xx: validar payload y auth; no destruir capa estable.",
        "servidor_http": "HTTP 5xx: reintentar; si persiste, activar failover de motor.",
        "desconocido": "Clasificar manualmente; conservar ledger y no mutar núcleos.",
    }
    return mapa.get(categoria, mapa["desconocido"])


def reparar_seguro(categoria: str) -> dict[str, Any]:
    """
    Aplica SOLO acciones runtime seguras (sin tocar archivos .py del repo).
    """
    acciones: list[str] = []
    ok = True
    detalle: dict[str, Any] = {}

    try:
        if categoria in ("cuota", "llm", "red_transitoria", "saldo", "auth_key"):
            try:
                from cognicion.llm import (
                    _deepseek_circuit_cerrar,
                    _gemini_circuit_cerrar,
                    recargar_entorno_llm,
                )

                _gemini_circuit_cerrar()
                _deepseek_circuit_cerrar()
                acciones.append("circuit_llm_cerrados")
                st = recargar_entorno_llm()
                acciones.append("llm_reload_env")
                detalle["llm_keys"] = st.get("keys")
            except Exception as exc:
                ok = False
                detalle["llm_error"] = type(exc).__name__

        if categoria in ("multimedia_media", "multimedia_tts", "multimedia_stt"):
            try:
                from cognicion.orquesta.smart_router import estado_smart_router

                detalle["smart_router"] = {
                    k: estado_smart_router().get(k)
                    for k in ("ok", "media_listo", "tts_listo", "cadenas")
                }
                acciones.append("smart_router_recheck")
            except Exception as exc:
                detalle["media_error"] = type(exc).__name__

        if categoria in ("auth_key", "desconocido", "red_transitoria"):
            try:
                from cognicion.servicios.clientes import limpiar_cache_clientes

                limpiar_cache_clientes()
                acciones.append("clientes_cache_clear")
            except Exception as exc:
                detalle["cache_error"] = type(exc).__name__

        if not acciones:
            acciones.append("solo_registro_y_propuesta")
    except Exception as exc:
        ok = False
        detalle["fatal"] = type(exc).__name__

    return {"ok": ok, "acciones": acciones, "detalle": detalle, "muta_fuentes": False}


def registrar_fallo(
    *,
    origen: str,
    exc: BaseException | None = None,
    status_http: int | None = None,
    mensaje: str = "",
    path: str | None = None,
    auto_reparar: bool = True,
) -> dict[str, Any]:
    """Punto único: captura → clasifica → ledger → reparación segura opcional."""
    tipo = type(exc).__name__ if exc else (f"http_{status_http}" if status_http else "evento")
    msg = (mensaje or (str(exc) if exc else "")).strip()[:800]
    tb = ""
    if exc is not None:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-4000:]
    categoria = clasificar_fallo(exc, status_http=status_http, mensaje=msg)
    propuesta = _propuesta_para(categoria, origen)
    reparacion: dict[str, Any] = {}
    if auto_reparar:
        reparacion = reparar_seguro(categoria)
        with _LOCK:
            if reparacion.get("ok"):
                _STATS["reparaciones_ok"] += 1
            else:
                _STATS["reparaciones_fail"] += 1
            _STATS["propuestas"] += 1

    evento = EventoFallo(
        ts=_ahora(),
        origen=origen,
        tipo=tipo,
        mensaje=msg,
        status_http=status_http,
        traceback=tb,
        path=path,
        categoria=categoria,
        reparacion=reparacion,
        propuesta=propuesta,
    )
    pack = asdict(evento)
    with _LOCK:
        _STATS["capturados"] += 1
        _RECIENTES.appendleft(pack)
    _append_ledger(pack)
    return pack


def health_motores() -> dict[str, Any]:
    """Chequeo no destructivo de conectividad de motores (sin secretos)."""
    out: dict[str, Any] = {"ok": True, "motores": {}, "ts": _ahora()}
    try:
        from cognicion.orquesta.smart_router import estado_smart_router

        sr = estado_smart_router()
        out["smart_router"] = {
            "ok": sr.get("ok"),
            "media_listo": sr.get("media_listo"),
            "tts_listo": sr.get("tts_listo"),
            "llm_listo": sr.get("llm_listo"),
            "web_listo": sr.get("web_listo"),
            "huerfanas": sr.get("huerfanas"),
        }
        out["motores"]["smart_router"] = bool(sr.get("ok"))
    except Exception as exc:
        out["ok"] = False
        out["motores"]["smart_router"] = False
        registrar_fallo(origen="self_debug.health", exc=exc, auto_reparar=False)

    try:
        from cognicion.llm import estado_llm

        llm = estado_llm()
        out["llm"] = {
            "disponible": llm.get("disponible"),
            "keys": llm.get("keys"),
            "gemini_circuit_open": llm.get("gemini_circuit_open"),
            "deepseek_circuit_open": llm.get("deepseek_circuit_open"),
        }
        out["motores"]["llm"] = bool(llm.get("disponible") or any((llm.get("keys") or {}).values()))
    except Exception as exc:
        out["ok"] = False
        out["motores"]["llm"] = False
        registrar_fallo(origen="self_debug.health.llm", exc=exc, auto_reparar=False)

    try:
        from cognicion.busqueda.agente import estado_circuit_breakers

        out["web_breakers"] = estado_circuit_breakers()
        out["motores"]["web"] = True
    except Exception as exc:
        out["motores"]["web"] = False
        registrar_fallo(origen="self_debug.health.web", exc=exc, auto_reparar=False)

    try:
        from lib.web_search import estado_conectividad

        out["web"] = estado_conectividad()
    except Exception:
        pass

    # Presencia de llaves (.env) — sin valores
    try:
        import os

        keys_flags = {
            "GEMINI_API_KEY": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
            "DEEPSEEK_API_KEY": bool(os.getenv("DEEPSEEK_API_KEY")),
            "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
            "ELEVENLABS_API_KEY": bool(os.getenv("ELEVENLABS_API_KEY")),
            "FAL_KEY": bool(os.getenv("FAL_KEY") or os.getenv("FAL_API_KEY")),
            "REPLICATE_API_TOKEN": bool(os.getenv("REPLICATE_API_TOKEN")),
            "DEEPGRAM_API_KEY": bool(os.getenv("DEEPGRAM_API_KEY")),
            "RENDER_API_KEY": bool(os.getenv("RENDER_API_KEY")),
        }
        out["env_keys"] = keys_flags
        out["motores"]["env_core"] = any(
            keys_flags[k] for k in ("GEMINI_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY")
        )
        out["motores"]["env_media"] = keys_flags["FAL_KEY"] or keys_flags["REPLICATE_API_TOKEN"]
        out["motores"]["env_tts"] = keys_flags["ELEVENLABS_API_KEY"]
        out["render_sync"] = {"api_key_presente": keys_flags["RENDER_API_KEY"]}
    except Exception:
        pass

    vivos = sum(1 for v in out["motores"].values() if v)
    out["score"] = round(100.0 * vivos / max(1, len(out["motores"])), 1)
    out["ok"] = out["score"] >= 50.0
    return out


def ciclo_autodiagnostico(*, reparar: bool = True) -> dict[str, Any]:
    """Un ciclo completo: health → si flaquea, reparación segura → re-health."""
    t0 = time.perf_counter()
    antes = health_motores()
    reparo: dict[str, Any] | None = None
    if reparar and not antes.get("ok"):
        reparo = reparar_seguro("red_transitoria")
    despues = health_motores() if reparo else antes
    return {
        "ok": bool(despues.get("ok")),
        "version": _VERSION,
        "protocol": "SELF_DEBUG_AUTOREPAIR",
        "muta_fuentes": False,
        "antes": {"ok": antes.get("ok"), "score": antes.get("score")},
        "despues": {"ok": despues.get("ok"), "score": despues.get("score"), "motores": despues.get("motores")},
        "reparacion": reparo,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        "stats": dict(_STATS),
        "recientes": list(_RECIENTES)[:8],
    }


def estado_self_debug() -> dict[str, Any]:
    with _LOCK:
        recientes = list(_RECIENTES)[:12]
        stats = dict(_STATS)
    return {
        "ok": True,
        "version": _VERSION,
        "protocol": "SELF_DEBUG_AUTOREPAIR",
        "autopreservacion": True,
        "muta_fuentes": False,
        "ledger": str(_LEDGER.name),
        "stats": stats,
        "recientes": recientes,
        "health": health_motores(),
    }
