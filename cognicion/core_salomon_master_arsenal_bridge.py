# [FILE: core_salomon_master_arsenal_bridge.py]
# Puente Maestro de Conexión Absoluta de APIs (Salomón AI)
"""
Carga obligatoria del arsenal (.env / Render) y dispara generación gráfica.
Stack real: FastAPI (no Flask).
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

_log = logging.getLogger("salomon.master_bridge")

_RE_REFUSAL = re.compile(
    r"(?is)"
    r"("
    r"no\s+(puedo|tengo\s+la\s+capacidad\s+de|soy\s+capaz\s+de)\s+"
    r"(generar|crear|dibujar|producir|hacer)\s+"
    r"(im[aá]genes?|gr[aá]ficos?|dibujos?|fotos?|ilustraciones?)"
    r"|"
    r"(i\s+can'?t|i\s+cannot|i'?m\s+unable\s+to)\s+"
    r"(generate|create|draw)\s+(images?|pictures?|graphics?)"
    r"|"
    r"como\s+(modelo|ia|asistente)\s+de\s+texto[^.!?\n]{0,80}"
    r"(no\s+puedo|no\s+genero|no\s+creo)\s+[^.!?\n]{0,40}im[aá]gen"
    r")"
    r"[^.!?\n]*[.!?]?"
)


def _env(*names: str) -> str:
    for n in names:
        v = (os.getenv(n) or "").strip()
        if v:
            return v
    return ""


def _flag(*names: str) -> bool:
    return bool(_env(*names))


class SalomonMasterArsenalBridge:
    """Puente maestro: inventaría llaves y habilita el motor gráfico."""

    MODULE = "SalomonMasterArsenalBridge"
    STATUS = "MASTER_BRIDGE_ENGAGED"
    VERSION = "110.17.3"

    def __init__(self) -> None:
        self.module = self.MODULE
        self.status = self.STATUS
        self._engaged = False

    def _snapshot(self) -> dict[str, Any]:
        """Lee settings (.env cargado) con fallback a os.environ / Render."""
        try:
            import settings as S

            gem = bool((S.GEMINI_API_KEY or "").strip())
            groq = bool((S.GROQ_API_KEY or "").strip())
            oai = bool((S.OPENAI_API_KEY or "").strip())
            fal = bool((S.FAL_KEY or "").strip())
            rep = bool((S.REPLICATE_API_TOKEN or "").strip())
            elev = bool((S.ELEVENLABS_API_KEY or "").strip())
            deep = bool((S.DEEPGRAM_API_KEY or "").strip())
        except Exception:
            gem = _flag("GEMINI_API_KEY")
            groq = _flag("GROQ_API_KEY", "GROK_API_KEY")
            oai = _flag("OPENAI_API_KEY")
            fal = _flag("FAL_KEY")
            rep = _flag("REPLICATE_API_TOKEN", "REPLICATE_API_KEY")
            elev = _flag("ELEVENLABS_API_KEY")
            deep = _flag("DEEPGRAM_API_KEY")

        keys_status = {
            "Gemini (Conciencia)": gem,
            "Groq (Fluidez)": groq,
            "OpenAI (Respaldo)": oai,
            "Replicate/Fal (Imágenes)": bool(fal or rep),
            "ElevenLabs/Deepgram (Voz)": bool(elev or deep),
        }
        return {
            "keys_status": keys_status,
            "detail": {
                "GEMINI_API_KEY": "set" if gem else "missing",
                "GROQ_API_KEY": "set" if groq else "missing",
                "OPENAI_API_KEY": "set" if oai else "missing",
                "FAL_KEY": "set" if fal else "missing",
                "REPLICATE": "set" if rep else "missing",
                "ELEVENLABS_API_KEY": "set" if elev else "missing",
                "DEEPGRAM_API_KEY": "set" if deep else "missing",
            },
            "image_generation_available": bool(fal or rep or oai),
            "llm_available": bool(gem or groq or oai),
            "voice_available": bool(elev or deep),
            "preferred_image_route": (
                "fal" if fal else ("replicate" if rep else ("openai" if oai else "none"))
            ),
        }

    def verify_and_connect_all(self) -> dict[str, Any]:
        snap = self._snapshot()
        _log.info(
            "[SALOMÓN AI] Estado del Arsenal de APIs conectado: %s",
            snap["keys_status"],
        )
        # Calienta dispatcher + arsenal (sin generar imagen aún)
        try:
            from cognicion.core_salomon_universal_key_dispatcher import (
                obtener_dispatcher,
            )

            snap["dispatcher"] = obtener_dispatcher().inventory()
        except Exception as exc:
            snap["dispatcher_error"] = type(exc).__name__
        try:
            from cognicion.core_salomon_api_arsenal_image_generator import (
                obtener_arsenal,
            )

            snap["arsenal"] = obtener_arsenal().connect_and_activate()
        except Exception as exc:
            snap["arsenal_error"] = type(exc).__name__

        snap["status"] = self.status
        snap["module"] = self.module
        snap["version"] = self.VERSION
        snap["engaged"] = True
        self._engaged = True
        return snap

    def scrub_capability_refusals(self, texto: str, *, imagen_url: str | None = None) -> str:
        """Elimina negativas de capacidad gráfica; si hay URL, ancla el mensaje."""
        if not texto:
            if imagen_url:
                return f"Imagen lista: {imagen_url}"
            return texto or ""
        out = _RE_REFUSAL.sub("", texto)
        out = re.sub(r"\n{3,}", "\n\n", out).strip()
        if imagen_url and imagen_url not in out:
            out = (
                (out.rstrip() + "\n\n") if out else ""
            ) + f"Imagen lista: {imagen_url}"
        elif not out and imagen_url:
            out = f"Imagen lista: {imagen_url}"
        return out

    def ensure_image_for_prompt(self, user_prompt: str) -> dict[str, Any]:
        """Si el prompt es gráfico, dispara Fal/Replicate/OpenAI de inmediato."""
        from cognicion.core_salomon_universal_key_dispatcher import (
            dispatch_image_intent,
            obtener_dispatcher,
        )

        if not obtener_dispatcher().wants_image(user_prompt or ""):
            return {"ok": False, "skipped": True, "reason": "not_image_intent"}
        pack = dispatch_image_intent(user_prompt or "")
        if pack.get("ok") and pack.get("url"):
            return pack
        # Fallback arsenal directo
        try:
            from cognicion.core_salomon_api_arsenal_image_generator import (
                generate_from_intent,
            )

            alt = generate_from_intent(user_prompt or "")
            if alt.get("ok") and alt.get("url"):
                alt["via"] = alt.get("via") or "master_bridge_arsenal"
                return alt
        except Exception as exc:
            pack = dict(pack or {})
            pack["bridge_fallback_error"] = type(exc).__name__
        return pack

    def as_json(self) -> str:
        return json.dumps(
            self.verify_and_connect_all(),
            indent=2,
            ensure_ascii=False,
            default=str,
        )


_BRIDGE: SalomonMasterArsenalBridge | None = None


def obtener_bridge() -> SalomonMasterArsenalBridge:
    global _BRIDGE
    if _BRIDGE is None:
        _BRIDGE = SalomonMasterArsenalBridge()
    return _BRIDGE


def engage_master_bridge() -> dict[str, Any]:
    """Boot hook: conectar arsenal completo."""
    return obtener_bridge().verify_and_connect_all()


if __name__ == "__main__":
    bridge = SalomonMasterArsenalBridge()
    print("[EJECUTANDO PUENTE MAESTRO DE APIS - SALOMÓN AI]")
    print(bridge.as_json())
