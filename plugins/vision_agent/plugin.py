# -*- coding: utf-8 -*-
"""Plugin periférico VisionAgent — Level 9 hot-plug."""

from __future__ import annotations

from typing import Any

_ACTIVO = False


def activar(app: Any = None) -> bool:
    global _ACTIVO
    from core.peripherals.vision_agent import VisionAgent

    VisionAgent.activate()
    _ACTIVO = True
    return True


def desactivar() -> None:
    global _ACTIVO
    _ACTIVO = False


def estado() -> dict[str, Any]:
    from core.peripherals.vision_agent import VisionAgent

    return {"plugin": "vision_agent", "activo": _ACTIVO, **VisionAgent.estado()}
