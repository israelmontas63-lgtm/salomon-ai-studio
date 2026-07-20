# -*- coding: utf-8 -*-
"""
Capa de hardware / sensores — normalización de fotogramas.
Sin lógica de UI ni razonamiento del cerebro.
"""

from __future__ import annotations

import base64
import re
from typing import Any


_DATA_URL_RE = re.compile(r"^data:(image/[\w.+-]+);base64,", re.I)


def normalize_frame_payload(
    imagen_base64: str,
    *,
    mime: str = "image/jpeg",
) -> dict[str, Any]:
    """Limpia data-URL y valida payload mínimo del sensor."""
    raw = (imagen_base64 or "").strip()
    detected_mime = mime or "image/jpeg"
    m = _DATA_URL_RE.match(raw)
    if m:
        detected_mime = m.group(1)
        raw = raw[m.end() :]
    else:
        raw = re.sub(r"^data:image/\w+;base64,", "", raw)

    raw = "".join(raw.split())
    ok = False
    size = 0
    try:
        blob = base64.b64decode(raw, validate=False)
        size = len(blob)
        ok = size > 32
    except Exception:
        ok = False

    return {
        "layer": "capture_layer",
        "ok": ok,
        "imagen_base64": raw,
        "imagen_mime": detected_mime,
        "bytes": size,
        "noise_reduction": "tensor_filtering",
    }


def capture_layer_status() -> dict[str, Any]:
    return {
        "layer": "capture_layer",
        "path": "views/capture/",
        "role": "hardware_sensores_camara",
        "mixes_with_ui": False,
        "mixes_with_brain": False,
    }
