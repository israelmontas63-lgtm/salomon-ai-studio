"""Generación de imágenes — Fal/Replicate → DALL·E → Gemini. Sin placeholder en ejecución."""

from __future__ import annotations

import base64
import uuid
from pathlib import Path
from typing import Any

import httpx

from settings import DATA_DIR, MODO_EJECUCION, OPENAI_API_KEY, OPENAI_BASE_URL

_DIR = DATA_DIR / "media" / "generadas"
_DIR.mkdir(parents=True, exist_ok=True)

DALLE_MODELS = ("dall-e-3", "dall-e-2", "gpt-image-1")
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
    """Única ruta: ServiceManager (Fal→Replicate) luego DALL·E → Gemini."""
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
            media_err = f"{type(exc).__name__}:{exc}"[:240]

    # 2) OpenAI Images (respaldo) — sin response_format (rompe en algunas cuentas)
    dalle_errs: list[str] = []
    if OPENAI_API_KEY:
        size_ok = (
            size
            if size in ("1024x1024", "1792x1024", "1024x1792", "512x512", "256x256")
            else DALLE_SIZE_DEFAULT
        )
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        for model in DALLE_MODELS:
            payload: dict[str, Any] = {
                "model": model,
                "prompt": prompt_api[:3900],
                "n": 1,
                "size": "1024x1024" if model == "gpt-image-1" else (
                    "512x512" if model == "dall-e-2" and size_ok not in ("256x256", "512x512")
                    else size_ok
                ),
            }
            if model.startswith("dall-e"):
                payload["quality"] = quality if quality in ("standard", "hd") else "standard"
            try:
                with httpx.Client(timeout=120.0) as client:
                    r = client.post(_openai_images_url(), json=payload, headers=headers)
                if r.status_code >= 400:
                    dalle_errs.append(f"{model}:http_{r.status_code}:{(r.text or '')[:160]}")
                    continue
                data = r.json()
                item = (data.get("data") or [{}])[0]
                b64 = item.get("b64_json")
                url = item.get("url")
                raw: bytes | None = None
                if b64:
                    raw = base64.b64decode(b64)
                elif url:
                    with httpx.Client(timeout=90.0) as client:
                        raw = client.get(url, follow_redirects=True).content
                        b64 = base64.b64encode(raw).decode("ascii")
                if raw and b64:
                    path = _guardar_png(raw, "dalle")
                    return {
                        "exito": True,
                        "motor": model,
                        "ruta": str(path),
                        "url_relativa": f"/media/generadas/{path.name}",
                        "imagen_base64": b64,
                        "mime": "image/png",
                        "revised_prompt": item.get("revised_prompt"),
                    }
                dalle_errs.append(f"{model}:sin_imagen")
            except Exception as exc:
                dalle_errs.append(f"{model}:{type(exc).__name__}")

    # 3) Gemini image failover
    try:
        from cognicion.media.gemini_imagen import generar_imagen_gemini

        gem = generar_imagen_gemini(prompt_api)
        if gem.get("exito"):
            return gem
        media_err = f"{media_err}|gemini:{gem.get('error')}" if media_err else str(
            gem.get("error")
        )
    except Exception as exc:
        media_err = f"{media_err}|gemini:{type(exc).__name__}" if media_err else type(exc).__name__

    if MODO_EJECUCION:
        return {
            "exito": False,
            "error": "media_sin_proveedor",
            "aviso": media_err,
            "detalle": dalle_errs[:6],
            "motor": "none",
            "error_codigo": 23,
        }

    # Dev: placeholder solo fuera de MODO_EJECUCION
    return {
        "exito": False,
        "error": "media_sin_proveedor",
        "aviso": media_err,
        "detalle": dalle_errs[:6],
        "motor": "none",
        "error_codigo": 23,
    }
