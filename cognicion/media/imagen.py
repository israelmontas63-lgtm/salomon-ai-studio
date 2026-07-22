"""Generación de imágenes — ServiceManager (Fal/Replicate) → DALL·E. Sin placeholder en ejecución."""

from __future__ import annotations

import base64
import uuid
from pathlib import Path
from typing import Any

import httpx

from settings import DATA_DIR, MODO_EJECUCION, OPENAI_API_KEY, OPENAI_BASE_URL

_DIR = DATA_DIR / "media" / "generadas"
_DIR.mkdir(parents=True, exist_ok=True)

DALLE_MODEL = "dall-e-3"
DALLE_SIZE_DEFAULT = "1024x1024"


def _openai_images_url() -> str:
    base = (OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/images/generations"
    return f"{base}/v1/images/generations"


def _guardar_png(datos: bytes, prefijo: str = "img") -> Path:
    path = _DIR / f"{prefijo}_{uuid.uuid4().hex[:12]}.png"
    path.write_bytes(datos)
    return path


def generar_imagen(
    prompt: str,
    *,
    size: str = DALLE_SIZE_DEFAULT,
    quality: str = "standard",
    estilo_marca: bool = True,
    usar_manager: bool = True,
) -> dict[str, Any]:
    """Única ruta: ServiceManager (Fal→Replicate) luego DALL·E. Sin simulación en ejecución."""
    texto = (prompt or "").strip()
    if not texto:
        return {"exito": False, "error": "prompt_vacio"}

    prompt_api = texto
    if estilo_marca:
        prompt_api = (
            f"{texto}. Estética elegante negro y oro, composición limpia, "
            "sin texto ilegible, calidad premium."
        )

    media_err = None
    # 1) Ruta neuronal (Fal / Replicate) — omitible para evitar recursión desde manager
    if usar_manager:
        try:
            from cognicion.servicios import obtener_manager

            mgr = obtener_manager()
            if mgr.activo("media"):
                out = mgr.generar_activo(prompt_api, video=False)
                if out.get("exito"):
                    return out
                media_err = str(out.get("error") or "media_fail")
        except Exception as exc:
            media_err = f"{type(exc).__name__}"

    # 2) OpenAI DALL·E (respaldo real)
    if OPENAI_API_KEY:
        try:
            payload = {
                "model": DALLE_MODEL,
                "prompt": prompt_api[:3900],
                "n": 1,
                "size": size
                if size in ("1024x1024", "1792x1024", "1024x1792")
                else DALLE_SIZE_DEFAULT,
                "quality": quality if quality in ("standard", "hd") else "standard",
                "response_format": "b64_json",
            }
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            }
            with httpx.Client(timeout=120.0) as client:
                r = client.post(_openai_images_url(), json=payload, headers=headers)
                r.raise_for_status()
                data = r.json()
            b64 = (data.get("data") or [{}])[0].get("b64_json")
            if b64:
                raw = base64.b64decode(b64)
                path = _guardar_png(raw, "dalle")
                return {
                    "exito": True,
                    "motor": "dall-e-3",
                    "ruta": str(path),
                    "url_relativa": f"/media/generadas/{path.name}",
                    "imagen_base64": b64,
                    "mime": "image/png",
                    "revised_prompt": (data.get("data") or [{}])[0].get("revised_prompt"),
                }
        except Exception as exc:
            if MODO_EJECUCION:
                return {
                    "exito": False,
                    "error": f"dalle_{type(exc).__name__}",
                    "motor": "dall-e-3",
                    "aviso": media_err,
                }

    # Modo ejecución: nunca devolver fake PNG
    if MODO_EJECUCION:
        return {
            "exito": False,
            "error": "media_sin_proveedor",
            "aviso": "Configure FAL_KEY, REPLICATE_API_TOKEN u OPENAI_API_KEY",
            "motor": "none",
        }

    # Solo fuera de ejecución (dev) — marca visual mínima
    return {
        "exito": False,
        "error": "media_no_disponible",
        "motor": "none",
        "aviso": media_err or "sin_claves_media",
    }
