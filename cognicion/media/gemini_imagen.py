# -*- coding: utf-8 -*-
"""
Generación de imagen vía Gemini (flash-image / Imagen) — failover multimodal.

Se usa cuando Fal/Replicate/OpenAI fallan por saldo o cuota.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import base64
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from settings import DATA_DIR

_DIR = DATA_DIR / "media" / "generadas"
_DIR.mkdir(parents=True, exist_ok=True)

# Orden: más barato / disponible primero (2 modelos para no bloquear el chat)
_GEMINI_IMAGE_MODELS = (
    "gemini-2.5-flash-image",
    "gemini-3.1-flash-lite-image",
)


def _gemini_key() -> str:
    import os

    try:
        from settings import GEMINI_API_KEY, GOOGLE_API_KEY  # type: ignore

        return (GEMINI_API_KEY or GOOGLE_API_KEY or "").strip() or (
            os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        ).strip()
    except Exception:
        return (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()


def _retry_delays() -> tuple[float, ...]:
    # Corto: 429 de cuota Gemini rara vez se recupera en segundos
    return (0.0, 1.0, 2.5)


def generar_imagen_gemini(prompt: str) -> dict[str, Any]:
    """Genera imagen con Gemini multimodal. Retry+backoff en 429/5xx."""
    texto = (prompt or "").strip()
    if not texto:
        return {"exito": False, "error": "prompt_vacio", "motor": "gemini"}
    key = _gemini_key()
    if not key:
        return {"exito": False, "error": "gemini_api_key_ausente", "motor": "gemini"}

    errores: list[str] = []
    body = {
        "contents": [{"parts": [{"text": texto[:3500]}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }

    for model in _GEMINI_IMAGE_MODELS:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": key,
        }
        for delay in _retry_delays():
            if delay:
                time.sleep(delay)
            try:
                with httpx.Client(timeout=120.0) as client:
                    r = client.post(url, json=body, headers=headers)
                if r.status_code in (429, 500, 502, 503, 504):
                    errores.append(f"{model}:http_{r.status_code}")
                    continue
                if r.status_code >= 400:
                    snip = (r.text or "")[:180]
                    errores.append(f"{model}:http_{r.status_code}:{snip}")
                    break  # modelo no usable; siguiente
                data = r.json()
                b64, mime = _extraer_inline(data)
                if not b64:
                    errores.append(f"{model}:sin_imagen")
                    break
                raw = base64.b64decode(b64)
                ext = "png" if "png" in (mime or "") else "jpg"
                nombre = f"gemini_{uuid.uuid4().hex[:12]}.{ext}"
                path = _DIR / nombre
                path.write_bytes(raw)
                return {
                    "exito": True,
                    "motor": "gemini",
                    "modelo": model,
                    "ruta": str(path),
                    "url_relativa": f"/media/generadas/{nombre}",
                    "imagen_base64": b64,
                    "mime": mime or f"image/{ext}",
                    "calidad": "pro_ultra",
                    "via": "gemini_image_failover",
                }
            except Exception as exc:
                errores.append(f"{model}:{type(exc).__name__}")
                continue

    return {
        "exito": False,
        "error": "gemini_imagen_agotado",
        "detalle": errores[:8],
        "motor": "gemini",
    }


def _extraer_inline(data: dict[str, Any]) -> tuple[str | None, str | None]:
    for c in data.get("candidates") or []:
        parts = ((c.get("content") or {}).get("parts")) or []
        for p in parts:
            inline = p.get("inlineData") or p.get("inline_data") or {}
            b64 = inline.get("data")
            if b64:
                mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                return str(b64), str(mime)
    return None, None
