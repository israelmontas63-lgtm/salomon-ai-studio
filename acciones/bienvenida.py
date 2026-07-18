"""Bienvenida — frase de apertura + ElevenLabs para el arranque de la UI."""

from __future__ import annotations

from typing import Any

from acciones.hablar import hablar
from cognicion.llm import generar_texto, llm_disponible

_FALLBACK = (
    "¡Israel! Aquí estoy — Salomón en línea, mente unificada y a tu disposición total. "
    "Voz, visión y razonamiento sincronizados. Dime qué hacemos."
)


def _frase_valida(texto: str) -> bool:
    t = (texto or "").strip()
    baja = t.lower()
    if not (24 <= len(t) <= 280):
        return False
    if any(
        x in baja
        for x in (
            "cuota",
            "límite",
            "limite",
            "gemini",
            "groq",
            "wikipedia",
            "prueba preguntas",
            "eres el agente",
            "redacta",
            "too many",
        )
    ):
        return False
    return any(k in baja for k in ("israel", "salom", "hola", "bienvenid"))


def generar_frase_bienvenida() -> dict[str, Any]:
    """
    Cerebro: genera una frase de bienvenida nueva (LLM) o fallback elegante.
    """
    meta: dict[str, Any] = {"ruta": "contenido"}
    frase = _FALLBACK

    if llm_disponible():
        prompt = (
            "Eres Salomón. Escribe UNA sola frase de bienvenida breve, cálida "
            "y enérgica para Israel al abrir Salomón AI Studio. "
            "Tono elegante y profesional. Solo la frase, sin comillas ni título."
        )
        try:
            cand = (generar_texto(prompt) or "").strip().strip('"').strip("'")
            if _frase_valida(cand):
                frase = cand
                meta["llm"] = True
            else:
                meta["llm"] = False
                meta["bienvenida_fallback"] = True
        except Exception as exc:
            meta["llm"] = False
            meta["error"] = type(exc).__name__
            meta["bienvenida_fallback"] = True
    else:
        meta["llm"] = False
        meta["bienvenida_fallback"] = True

    return {"frase": frase, "ruta": "contenido", "metadata": meta}


def ciclo_bienvenida_completa() -> dict[str, Any]:
    """Genera frase + sintetiza con ElevenLabs (listo para UI y reproducción)."""
    gen = generar_frase_bienvenida()
    voz = hablar(gen["frase"])
    return {
        "frase": gen["frase"],
        "ruta_grafo": gen["ruta"],
        "exito_voz": voz.get("exito"),
        "audio_base64": voz.get("audio_base64"),
        "audio_mime": voz.get("audio_mime") or "audio/mpeg",
        "tts_disponible": voz.get("tts_disponible"),
        "error_voz": voz.get("error"),
        "motor": voz.get("motor"),
        "metadata": gen["metadata"],
    }
