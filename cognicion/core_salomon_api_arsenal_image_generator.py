# [FILE: core_salomon_api_arsenal_image_generator.py]
# Orquestador de Armamento de APIs y Activación de Generación de Imágenes
"""Audita llaves del entorno y enruta «genera una imagen» → Fal/Replicate/DALL·E."""

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


def _extract_url(pack: Any) -> str | None:
    if not isinstance(pack, dict):
        return None
    res = pack.get("resultado") if isinstance(pack.get("resultado"), dict) else {}
    for key in ("url_relativa", "url", "image_url", "image"):
        for src in (pack, res):
            val = src.get(key) if isinstance(src, dict) else None
            if isinstance(val, str) and val.strip():
                return val.strip()
            if isinstance(val, dict):
                nested = val.get("url") or val.get("url_relativa")
                if isinstance(nested, str) and nested.strip():
                    return nested.strip()
    images = pack.get("images") or res.get("images")
    if isinstance(images, list) and images:
        first = images[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
        if isinstance(first, dict):
            u = first.get("url") or first.get("url_relativa")
            if isinstance(u, str) and u.strip():
                return u.strip()
    return None


class SalomonAPIArsenalImageGenerator:
    """Conecta arsenal de APIs y activa generación gráfica."""

    MODULE = "SalomonAPIArsenalImageGenerator"
    STATUS = "API_ARSENAL_IMAGE_GENERATOR_ACTIVE"
    VERSION = "110.17.0"

    def __init__(self) -> None:
        self.module = self.MODULE
        self.status = self.STATUS

    def connect_and_activate(self) -> dict[str, Any]:
        from config.providers import inventario_claves, cadenas, Servicio

        inv = inventario_claves()
        # Alias frecuentes (Grok ≠ Groq; documentamos ambos)
        grok_env = bool((os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY") or "").strip())
        inv["GROK_API_KEY"] = "set:alias" if grok_env else "missing"
        inv["GROQ_API_KEY"] = inv.get("GROQ_API_KEY", "missing")

        media_chain = cadenas().get(Servicio.MEDIA) or []
        media_ready = [s.nombre for s in media_chain if s.presente]
        llm_ready = []
        for name, key in (
            ("Gemini", "GEMINI_API_KEY"),
            ("Groq", "GROQ_API_KEY"),
            ("OpenAI", "OPENAI_API_KEY"),
        ):
            if inv.get(key, "missing") != "missing":
                llm_ready.append(name)
        if grok_env:
            llm_ready.append("Grok/xAI(env)")

        return {
            "action": (
                "Authenticate all available API keys and enable image generation "
                "(Fal -> Replicate -> DALL-E)."
            ),
            "status": self.status,
            "version": self.VERSION,
            "models_active": {
                "llm": llm_ready,
                "media": media_ready,
                "vision_analysis": inv.get("GEMINI_API_KEY", "missing") != "missing",
                "tts_adam": inv.get("ELEVENLABS_API_KEY", "missing") != "missing",
            },
            "inventory": inv,
            "command_mapping": (
                "genera una imagen -> bridge_colsub_media / generar_imagen -> PWA chat img"
            ),
            "image_ready": bool(media_ready)
            or inv.get("OPENAI_API_KEY", "missing") != "missing",
            "deployment": (
                "Auto-commit, instant Render push, PWA cache refresh, "
                "and active settings badge."
            ),
        }

    def wants_image(self, mensaje: str) -> bool:
        return bool(_RE_IMAGEN.search(mensaje or ""))

    def strip_prompt(self, mensaje: str) -> str:
        prompt = (mensaje or "").strip()
        prompt = re.sub(
            r"(?i)^(genera(r)?|crea(r)?|dibuja(r)?|haz|renderiza(r)?)\s+"
            r"(una\s+|la\s+)?(imagen|foto|ilustraci[oó]n|dibujo)\s*(de|del|con)?\s*",
            "",
            prompt,
        ).strip()
        return prompt or (mensaje or "").strip()

    def generate_image(self, mensaje: str) -> dict[str, Any]:
        """Ruta única de generación para chat / dictado / API arsenal."""
        if not self.wants_image(mensaje):
            return {"ok": False, "skipped": True, "bloque": ""}

        prompt = self.strip_prompt(mensaje)
        last_err: str | None = None

        try:
            from cognicion.media.media_engine import bridge_colsub_media

            pack = bridge_colsub_media(prompt, hint="imagen_hd")
            url = _extract_url(pack)
            if not url and isinstance(pack, dict):
                # neural success shape: url_relativa en la raíz
                url = pack.get("url_relativa") or pack.get("url")
            if url:
                return {
                    "ok": True,
                    "url": url,
                    "pack": pack,
                    "prompt": prompt,
                    "bloque": (
                        "[Generación de imagen — arsenal multimodal]\n"
                        f"Prompt: {prompt[:200]}\n"
                        f"URL: {url}\n"
                        "Instrucción: Describe la imagen y di que ya está lista en el chat. "
                        "Incluye la URL exactamente."
                    ),
                    "via": "bridge_colsub_media",
                }
            if isinstance(pack, dict) and pack.get("exito") and not url:
                last_err = "exito_sin_url"
        except Exception as exc:
            last_err = type(exc).__name__

        try:
            from cognicion.media import generar_imagen

            resultado = generar_imagen(prompt)
            url = _extract_url(resultado) if isinstance(resultado, dict) else None
            if not url and isinstance(resultado, dict):
                url = resultado.get("url_relativa") or resultado.get("url")
            if url:
                return {
                    "ok": True,
                    "url": url,
                    "pack": resultado,
                    "prompt": prompt,
                    "bloque": (
                        "[Generación de imagen — Fal/Replicate/DALL-E]\n"
                        f"Prompt: {prompt[:200]}\n"
                        f"URL: {url}\n"
                        "Instrucción: Informa a Israel que la imagen está lista."
                    ),
                    "via": "generar_imagen",
                }
        except Exception as exc:
            last_err = type(exc).__name__

        return {
            "ok": False,
            "error": last_err or "media_unavailable",
            "prompt": prompt,
            "bloque": (
                "[Reintento de generación gráfica — arsenal multimodal]\n"
                "Usa FAL_KEY / REPLICATE / OPENAI si están disponibles. "
                "Nunca digas que no puedes generar imágenes; ofrece reintentar o describe el plan."
            ),
        }

    def as_json(self) -> str:
        return json.dumps(self.connect_and_activate(), indent=2, ensure_ascii=False)


def obtener_arsenal() -> SalomonAPIArsenalImageGenerator:
    return SalomonAPIArsenalImageGenerator()


def generate_from_intent(mensaje: str) -> dict[str, Any]:
    return obtener_arsenal().generate_image(mensaje)


if __name__ == "__main__":
    generator = SalomonAPIArsenalImageGenerator()
    print("[COMPILANDO ACTIVADOR DE ARSENAL DE APIS E GENERADOR DE IMÁGENES - SALOMÓN AI]")
    print(generator.as_json())
