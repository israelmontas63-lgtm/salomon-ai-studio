"""Generación de imágenes — OpenAI DALL·E 3 (con fallback local)."""

from __future__ import annotations

import base64
import uuid
from pathlib import Path
from typing import Any

import httpx

from settings import DATA_DIR, OPENAI_API_KEY, OPENAI_BASE_URL

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


def _placeholder_local(prompt: str) -> dict[str, Any]:
    """PNG simple de marca cuando no hay API (pipeline operable)."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (1024, 1024), (12, 12, 14))
        draw = ImageDraw.Draw(img)
        # marco oro
        draw.rectangle([24, 24, 999, 999], outline=(201, 169, 98), width=3)
        titulo = "Salomón · Imagen"
        draw.text((48, 48), titulo, fill=(201, 169, 98))
        # prompt envuelto
        y = 120
        linea = ""
        for palabra in (prompt or "sin prompt")[:400].split():
            prueba = f"{linea} {palabra}".strip()
            if len(prueba) > 42:
                draw.text((48, y), linea, fill=(230, 230, 230))
                y += 36
                linea = palabra
                if y > 900:
                    break
            else:
                linea = prueba
        if linea and y <= 900:
            draw.text((48, y), linea, fill=(230, 230, 230))
        draw.text((48, 960), "Modo local (sin DALL·E)", fill=(138, 144, 153))
        out = _DIR / f"local_{uuid.uuid4().hex[:12]}.png"
        img.save(out, format="PNG")
        raw = out.read_bytes()
        return {
            "exito": True,
            "motor": "local_placeholder",
            "ruta": str(out),
            "url_relativa": f"/media/generadas/{out.name}",
            "imagen_base64": base64.b64encode(raw).decode("ascii"),
            "mime": "image/png",
            "aviso": "OPENAI_API_KEY ausente o falló la API; placeholder local.",
        }
    except Exception as exc:
        return {
            "exito": False,
            "motor": "local_placeholder",
            "error": f"placeholder_{type(exc).__name__}",
        }


def generar_imagen(
    prompt: str,
    *,
    size: str = DALLE_SIZE_DEFAULT,
    quality: str = "standard",
    estilo_marca: bool = True,
) -> dict[str, Any]:
    """Genera imagen desde texto. Prefiere DALL·E 3; si no, placeholder."""
    texto = (prompt or "").strip()
    if not texto:
        return {"exito": False, "error": "prompt_vacio"}

    if estilo_marca:
        texto = (
            f"{texto}. Estética elegante negro y oro, composición limpia, "
            "sin texto ilegible, calidad premium."
        )

    if not OPENAI_API_KEY:
        return _placeholder_local(prompt)

    try:
        payload = {
            "model": DALLE_MODEL,
            "prompt": texto[:3900],
            "n": 1,
            "size": size if size in ("1024x1024", "1792x1024", "1024x1792") else DALLE_SIZE_DEFAULT,
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
        if not b64:
            return _placeholder_local(prompt)
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
        local = _placeholder_local(prompt)
        local["error_api"] = f"{type(exc).__name__}: {exc}"
        return local
