# -*- coding: utf-8 -*-
"""
Protocolo de inicio — al abrir Salomón:
  1) Saludo enérgico
  2) Reconocimiento de identidad (Israel Monta)
  3) Estado de disponibilidad total
"""

from __future__ import annotations

from typing import Any

from mente.arquitectura import asegurar_estructura
from mente.hilos import cargar_hilo, guardar_hilo, registrar_turno


_SALUDO_CANONICO = (
    "¡Israel! Aquí estoy — Salomón en línea, mente unificada y a tu disposición total. "
    "Voz, visión y razonamiento sincronizados. Dime qué hacemos."
)


def protocolo_inicio(session_id: str) -> dict[str, Any]:
    """Ejecuta el arranque cerebral y sintetiza voz si hay TTS."""
    asegurar_estructura()
    hilo = cargar_hilo(session_id)
    hilo["estado"] = "inicio"
    hilo["protocolo_inicio"] = True
    guardar_hilo(hilo)

    frase = _SALUDO_CANONICO
    # Intentar frase viva vía LLM (sin web)
    try:
        from cognicion.llm import generar_texto, llm_disponible

        if llm_disponible():
            cand = (
                generar_texto(
                    "Eres Salomón. UNA frase enérgica de saludo a Israel Monta al abrir "
                    "el estudio: reconoce su identidad, di que estás disponible al 100% "
                    "(voz/visión/razón). Sin listar capacidades. Sin web. Solo la frase."
                )
                or ""
            ).strip().strip('"').strip("'")
            baja = cand.lower()
            if (
                28 <= len(cand) <= 320
                and "israel" in baja
                and not any(x in baja for x in ("wikipedia", "cuota", "película", "pelicula"))
            ):
                frase = cand
    except Exception:
        pass

    registrar_turno(session_id, rol="asistente", texto=frase, area="razonamiento")

    audio_base64 = None
    audio_mime = "audio/wav"
    tts_ok = False
    try:
        from acciones.hablar import hablar

        voz = hablar(frase)
        audio_base64 = voz.get("audio_base64")
        audio_mime = voz.get("audio_mime") or "audio/wav"
        tts_ok = bool(voz.get("tts_disponible") or audio_base64)
    except Exception:
        pass

    return {
        "ok": True,
        "protocolo": "INICIO_CEREBRAL",
        "session_id": session_id,
        "frase": frase,
        "identidad": "Israel Monta",
        "disponibilidad": "total",
        "audio_base64": audio_base64,
        "audio_mime": audio_mime,
        "tts_disponible": tts_ok,
        "areas": ["voz", "vision", "razonamiento", "memoria", "hilos"],
    }
