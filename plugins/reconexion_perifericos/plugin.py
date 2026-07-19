# -*- coding: utf-8 -*-
"""Plugin periférico reconexión — Level 9."""

from __future__ import annotations

from typing import Any

_ACTIVO = False
_SNAPSHOT: dict[str, Any] = {}


def activar(app: Any = None) -> bool:
    global _ACTIVO, _SNAPSHOT
    from cognicion.reconexion import estado_conectividad, estado_perifericos_config

    _SNAPSHOT = {
        "conectividad": estado_conectividad(),
        "perifericos": estado_perifericos_config(),
    }
    _ACTIVO = bool(_SNAPSHOT["perifericos"].get("ok"))
    return _ACTIVO


def desactivar() -> None:
    global _ACTIVO
    _ACTIVO = False


def estado() -> dict[str, Any]:
    return {"plugin": "reconexion_perifericos", "activo": _ACTIVO, **_SNAPSHOT}
