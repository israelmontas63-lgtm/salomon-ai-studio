# -*- coding: utf-8 -*-
"""Plugin periférico HomeGateway — Level 9 hot-plug."""

from __future__ import annotations

from typing import Any

_ACTIVO = False
_RUTAS: dict[str, str] = {}


def activar(app: Any = None) -> bool:
    global _ACTIVO, _RUTAS
    from core.peripherals.home_gateway import HomeGateway

    _RUTAS = dict(HomeGateway.RUTAS)
    _ACTIVO = True
    return True


def desactivar() -> None:
    global _ACTIVO
    _ACTIVO = False


def estado() -> dict[str, Any]:
    return {"plugin": "home_gateway", "activo": _ACTIVO, "rutas": dict(_RUTAS)}
