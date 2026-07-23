# [FILE: core_salomon_universal_key_dispatcher.py]
# Enrutador Dinámico de Arsenal de APIs y Generación Inmediata (Salomón AI)
"""
Lee llaves en runtime (.env / Render) y despacha generación gráfica
a Fal → Replicate → OpenAI. Stack: FastAPI (no Flask).
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

_RE_IMAGEN = re.compile(
    r"(?i)\b("
    r"(genera(r)?|crea(r)?|dibuja(r)?|haz|renderiza(r)?)\b[\w\s]{0,40}\b"
    r"(imagen|foto|ilustraci[oó]n|dibujo|picture|image|art|estrella)|"
    r"(imagen|foto|ilustraci[oó]n)\s+(de|del|con)\b"
    r")"
)


def _env(*names: str) -> str:
    for n in names:
        v = (os.getenv(n) or "").strip()
        if v:
            return v
    return ""


class SalomonUniversalKeyDispatcher:
    """Conector centralizado: arsenal de llaves + disparo inmediato de imagen."""

    MODULE = "SalomonUniversalKeyDispatcher"
    STATUS = "UNIVERSAL_DISPATCHER_READY"
    VERSION = "110.17.2"

    def __init__(self) -> None:
        self.module = self.MODULE
        self.status = self.STATUS

    def inventory(self) -> dict[str, Any]:
        """Snapshot runtime (nunca expone el secreto completo)."""
        # Prefer settings (carga .env) si está disponible
        try:
            import settings as S

            fal = bool((S.FAL_KEY or "").strip())
            rep = bool((S.REPLICATE_API_TOKEN or "").strip())
            gem = bool((S.GEMINI_API_KEY or "").strip())
            groq = bool((S.GROQ_API_KEY or "").strip())
            oai = bool((S.OPENAI_API_KEY or "").strip())
        except Exception:
            fal = bool(_env("FAL_KEY"))
            rep = bool(_env("REPLICATE_API_TOKEN", "REPLICATE_API_KEY"))
            gem = bool(_env("GEMINI_API_KEY"))
            # Solo GROQ real — GROK/XAI no es cliente xAI en este stack
            groq = bool(_env("GROQ_API_KEY"))
            oai = bool(_env("OPENAI_API_KEY"))

        return {
            "FAL_KEY": "set" if fal else "missing",
            "REPLICATE": "set" if rep else "missing",
            "GEMINI_API_KEY": "set" if gem else "missing",
            "GROQ_API_KEY": "set" if groq else "missing",
            "GROK_API_KEY": "unused_alias_not_xai",
            "OPENAI_API_KEY": "set" if oai else "missing",
            "image_generation_available": bool(fal or rep or oai),
            "llm_available": bool(gem or groq or oai),
            "preferred_image_route": (
                "fal" if fal else ("replicate" if rep else ("openai" if oai else "none"))
            ),
        }

    def wants_image(self, user_prompt: str) -> bool:
        return bool(_RE_IMAGEN.search(user_prompt or ""))

    def resolve_and_dispatch(self, user_prompt: str) -> dict[str, Any]:
        inv = self.inventory()
        prompt = (user_prompt or "").strip()
        if not prompt:
            return {
                "ok": False,
                "error": "prompt_vacio",
                "image_generation_available": inv["image_generation_available"],
                "inventory": inv,
            }

        if not self.wants_image(prompt):
            return {
                "ok": False,
                "skipped": True,
                "reason": "not_image_intent",
                "prompt_received": prompt[:200],
                "image_generation_available": inv["image_generation_available"],
                "inventory": inv,
            }

        if not inv["image_generation_available"]:
            return {
                "ok": False,
                "error": "no_image_keys",
                "mensaje": (
                    "No hay FAL_KEY / REPLICATE_API_KEY / OPENAI_API_KEY en el entorno."
                ),
                "inventory": inv,
            }

        # Despacho real → arsenal (Fal → Replicate → DALL-E)
        from cognicion.core_salomon_api_arsenal_image_generator import (
            generate_from_intent,
        )

        # Normalizar frases cortas tipo "Genera una estrella"
        msg = prompt
        if not re.search(r"(?i)\b(imagen|foto|ilustraci|dibujo|picture|image)\b", msg):
            msg = f"Genera una imagen de {prompt}"

        pack = generate_from_intent(msg)
        url = pack.get("url")
        return {
            "ok": bool(pack.get("ok") and url),
            "prompt_received": prompt[:200],
            "url": url,
            "via": pack.get("via") or inv.get("preferred_image_route"),
            "image_generation_available": True,
            "inventory": inv,
            "action": (
                "Intercept image intents, route to Fal/Replicate/OpenAI, "
                "return URL to PWA chat."
            ),
            "pack": pack.get("pack"),
            "error": pack.get("error"),
            "status": self.status,
            "version": self.VERSION,
        }

    def as_json(self, user_prompt: str = "Genera una estrella") -> str:
        return json.dumps(
            self.resolve_and_dispatch(user_prompt),
            indent=2,
            ensure_ascii=False,
            default=str,
        )


def obtener_dispatcher() -> SalomonUniversalKeyDispatcher:
    return SalomonUniversalKeyDispatcher()


def dispatch_image_intent(user_prompt: str) -> dict[str, Any]:
    return obtener_dispatcher().resolve_and_dispatch(user_prompt)


if __name__ == "__main__":
    dispatcher = SalomonUniversalKeyDispatcher()
    print("[INICIALIZANDO ENRUTADOR UNIVERSAL DE LLAVES - SALOMON AI]")
    print(json.dumps(dispatcher.inventory(), indent=2))
    print(dispatcher.as_json("Genera una estrella"))
