# -*- coding: utf-8 -*-
"""Plugin periférico media (Fal/Replicate) — Level 9."""

from __future__ import annotations

from typing import Any

_ACTIVO = False
_ESTADO: dict[str, Any] = {}


def activar(app: Any = None) -> bool:
    global _ACTIVO, _ESTADO
    from config.providers import Servicio, cadena_nombres, seleccionar

    slot = seleccionar(Servicio.MEDIA)
    _ESTADO = {
        "activo_provider": slot.nombre if slot else None,
        "cadena": cadena_nombres(Servicio.MEDIA),
    }
    _ACTIVO = bool(slot)
    return _ACTIVO


def desactivar() -> None:
    global _ACTIVO
    _ACTIVO = False


def estado() -> dict[str, Any]:
    return {"plugin": "media_stack", "activo": _ACTIVO, **_ESTADO}
