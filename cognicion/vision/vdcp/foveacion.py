"""Etapa 2 — Foveación selectiva (zoom lógico macro/micro sin pérdida)."""

from __future__ import annotations

from typing import Any

import numpy as np


def _clamp_bbox(
    x: int, y: int, w: int, h: int, W: int, H: int, pad: float = 0.08
) -> tuple[int, int, int, int]:
    px = int(w * pad)
    py = int(h * pad)
    x0 = max(0, x - px)
    y0 = max(0, y - py)
    x1 = min(W, x + w + px)
    y1 = min(H, y + h + py)
    return x0, y0, max(1, x1 - x0), max(1, y1 - y0)


def fovear_region(
    bgr: np.ndarray,
    bbox: list[int] | tuple[int, int, int, int],
    *,
    escala: str = "medio",
    min_lado: int = 160,
) -> dict[str, Any]:
    """
    Zoom lógico: recorte desde el buffer original a resolución nativa.
    Si la ROI es micro, se reescala con LANCZOS/cubic (sin inventar detalle OCR-hostil).
    """
    import cv2

    H, W = bgr.shape[:2]
    x, y, w, h = [int(v) for v in bbox]
    x, y, w, h = _clamp_bbox(x, y, w, h, W, H, pad=0.1 if escala == "micro" else 0.06)
    crop = bgr[y : y + h, x : x + w].copy()

    factor = 1.0
    ch, cw = crop.shape[:2]
    # Emular objetivo macro: ampliar micro-textos al menos a min_lado
    if escala == "micro" or min(cw, ch) < min_lado:
        factor = max(min_lado / max(min(cw, ch), 1), 2.0 if escala == "micro" else 1.5)
        factor = min(factor, 6.0)
        nw, nh = int(cw * factor), int(ch * factor)
        crop = cv2.resize(crop, (nw, nh), interpolation=cv2.INTER_CUBIC)
    elif escala == "grande" and max(cw, ch) > 1600:
        # Señales grandes: mantener calidad, limitar solo si absurdo
        factor = 1.0

    return {
        "bbox_foveado": [x, y, w, h],
        "factor_zoom": round(factor, 3),
        "shape": list(crop.shape),
        "imagen": crop,
        "modo": "macro" if factor >= 2 else "identidad",
    }
