# -*- coding: utf-8 -*-
"""
Fase 1 — Salomón autónomo (Estado Vivo).

Capacidades:
  • Ver: análisis de escena con Gemini Vision (no solo UI).
  • Pensar en paralelo: búsqueda + síntesis bajo una sola voz.
  • Comunicar mientras piensa: generador de eventos SSE / callbacks.
  • Núcleo: respuestas conversacionales pasan por INSTRUCCION_SISTEMA (cerebro).
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from typing import Any, Callable

from cognicion.autonoma.agentes_fase1 import correr_busqueda_y_sintesis_paralelo
from cognicion.estado_vivo import responder_con_nucleo
from cognicion.salida_limpia import sanitizar_salida_chat
from cognicion.vision.analizador import analizar_imagen, analizar_escena

ProgressFn = Callable[[str, dict[str, Any]], None]


def _necesita_busqueda(mensaje: str, tiene_imagen: bool) -> bool:
    from cognicion.busqueda.pedido_explicito import (
        es_saludo_o_charla_simple,
        pedido_busqueda_explicito,
    )

    t = (mensaje or "").strip().lower()
    if tiene_imagen and len(t) < 8:
        return False
    if len(t) < 3:
        return False
    if es_saludo_o_charla_simple(mensaje):
        return False
    # Memory Cortex: solo pedido explícito de Israel
    return pedido_busqueda_explicito(mensaje)


def _percepcion_vision(
    imagen_base64: str | None,
    imagen_mime: str,
    mensaje: str,
    on_progress: ProgressFn | None,
) -> dict[str, Any]:
    if not imagen_base64:
        return {"ok": False, "texto": "", "modo": None}
    if on_progress:
        on_progress("viendo", {"mensaje": "Estoy mirando la imagen…"})
    # Escena general (Fase 1); UI audit solo si el usuario lo pide
    t = (mensaje or "").lower()
    if any(x in t for x in ("interfaz", "ui", "pantalla", "layout", "botón", "boton")):
        res = analizar_imagen(imagen_base64, mime_type=imagen_mime, contexto_usuario=mensaje)
        modo = "ui"
    else:
        res = analizar_escena(imagen_base64, mime_type=imagen_mime, contexto_usuario=mensaje)
        modo = "escena"
    texto = ""
    if res.exito:
        # Quitar wrappers internos para la síntesis visible
        texto = res.contexto or ""
        for pref in (
            "[Análisis visual — captura de pantalla]",
            "[Análisis visual — escena]",
            "Instrucción:",
        ):
            if pref in texto:
                texto = texto.split(pref)[-1] if pref.startswith("[") else texto.split(pref)[0]
        texto = texto.strip()
    if on_progress:
        on_progress(
            "vision_lista",
            {
                "mensaje": "Ya vi la imagen." if res.exito else "No pude ver la imagen con claridad.",
                "ok": res.exito,
                "modo": modo,
                "error": res.error,
            },
        )
    return {"ok": bool(res.exito), "texto": texto, "modo": modo, "error": res.error}


def ejecutar_fase1(
    mensaje: str,
    *,
    imagen_base64: str | None = None,
    imagen_mime: str = "image/png",
    on_progress: ProgressFn | None = None,
) -> dict[str, Any]:
    """Ejecuta el pipeline Fase 1 y devuelve texto + metadata."""
    t0 = time.time()
    if on_progress:
        on_progress("pensando", {"mensaje": "Estoy pensando…"})

    if imagen_base64:
        vision = _percepcion_vision(imagen_base64, imagen_mime, mensaje or "", on_progress)
    else:
        vision = {"ok": False, "texto": "", "modo": None}

    consulta = (mensaje or "").strip() or (
        "Describe lo que ves y dame el contexto útil." if imagen_base64 else ""
    )

    meta: dict[str, Any] = {
        "fase": "1",
        "protocolo": "SALOMON_AUTONOMO_FASE1",
        "vision": {
            "usada": bool(imagen_base64),
            "ok": vision.get("ok"),
            "modo": vision.get("modo"),
        },
        "agentes": [],
        "eventos": [],
    }

    if not consulta and not vision.get("texto"):
        texto = responder_con_nucleo(
            "Israel acaba de abrir la sesión sin mensaje. "
            "Salúdalo con tono HD Cognitiva (fluido, contextual, sobrio) "
            "y ofrece acompañamiento breve sin listar capacidades."
        )
        meta["nucleo"] = "estado_vivo"
        meta["ms"] = int((time.time() - t0) * 1000)
        return {"texto": texto, "exito": True, "metadata": meta}

    # Solo visión (sin búsqueda) si es foto + mensaje mínimo
    if imagen_base64 and not _necesita_busqueda(consulta, True):
        if on_progress:
            on_progress("sintetizando", {"mensaje": "Organizo lo que vi…"})
        visto = vision.get("texto") or "No logré extraer detalle visual esta vez."
        texto = responder_con_nucleo(
            consulta or "Describe lo que ves de forma útil y sobria.",
            contexto=f"[Lo que vi]\n{visto}",
        )
        meta["agentes"] = ["vision", "sintesis_nucleo"]
        meta["nucleo"] = "estado_vivo"
        meta["ms"] = int((time.time() - t0) * 1000)
        return {"texto": texto, "exito": True, "metadata": meta}

    if _necesita_busqueda(consulta, bool(imagen_base64)):
        pack = correr_busqueda_y_sintesis_paralelo(
            consulta,
            vision_texto=vision.get("texto") or "",
            on_progress=on_progress,
        )
        texto = sanitizar_salida_chat(pack.get("texto") or "")
        meta["agentes"] = pack.get("agentes") or ["busqueda", "sintesis"]
        meta["nucleo"] = "estado_vivo"
        meta["busqueda"] = {
            "agentes_ok": (pack.get("pack_busqueda") or {}).get("agentes_ok"),
            "total_hallazgos": (pack.get("pack_busqueda") or {}).get("total_hallazgos"),
        }
        meta["ms"] = int((time.time() - t0) * 1000)
        return {"texto": texto, "exito": bool(texto), "metadata": meta}

    # Fallback conversacional → núcleo HD Cognitiva (misma voz que /api/chat)
    texto = responder_con_nucleo(consulta)
    meta["nucleo"] = "estado_vivo"
    meta["ms"] = int((time.time() - t0) * 1000)
    return {"texto": texto, "exito": True, "metadata": meta}


def iter_eventos_fase1(
    mensaje: str,
    *,
    imagen_base64: str | None = None,
    imagen_mime: str = "image/png",
) -> Iterator[dict[str, Any]]:
    """Genera eventos SSE: status… y al final `done` con la respuesta."""
    eventos: list[dict[str, Any]] = []

    def on_progress(etapa: str, extra: dict[str, Any]) -> None:
        ev = {"type": "status", "etapa": etapa, **(extra or {})}
        eventos.append(ev)

    # Emitimos en vivo vía lista; el generador flushea conforme crecen
    # Para SSE real usamos cola simple en el endpoint; aquí devolvemos
    # progreso + resultado de forma compatible con StreamingResponse.
    resultado_box: dict[str, Any] = {}

    def run() -> None:
        resultado_box["r"] = ejecutar_fase1(
            mensaje,
            imagen_base64=imagen_base64,
            imagen_mime=imagen_mime,
            on_progress=on_progress,
        )

    import threading

    th = threading.Thread(target=run, daemon=True)
    th.start()
    idx = 0
    while th.is_alive() or idx < len(eventos):
        while idx < len(eventos):
            yield eventos[idx]
            idx += 1
        if th.is_alive():
            time.sleep(0.05)
    while idx < len(eventos):
        yield eventos[idx]
        idx += 1

    r = resultado_box.get("r") or {
        "texto": "Israel, hubo un fallo en el pipeline Fase 1.",
        "exito": False,
        "metadata": {"fase": "1"},
    }
    yield {
        "type": "done",
        "texto": r.get("texto"),
        "exito": r.get("exito"),
        "metadata": r.get("metadata") or {},
    }


def evento_sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
