"""
Caché en memoria con TTL — reduce llamadas repetidas a conectores externos.
"""

from __future__ import annotations

import time
from typing import Any, Callable, TypeVar

from settings import CACHE_TTL_SEGUNDOS

T = TypeVar("T")

_almacen: dict[str, tuple[float, Any]] = {}


def obtener(clave: str) -> Any | None:
    """Devuelve valor cacheado si no expiró."""
    entrada = _almacen.get(clave)
    if not entrada:
        return None
    expira, valor = entrada
    if time.monotonic() > expira:
        _almacen.pop(clave, None)
        return None
    return valor


def guardar(clave: str, valor: Any, ttl: int | None = None) -> None:
    """Guarda un valor con TTL en segundos."""
    segundos = ttl if ttl is not None else CACHE_TTL_SEGUNDOS
    _almacen[clave] = (time.monotonic() + segundos, valor)


def memoizar(clave: str, factory: Callable[[], T], ttl: int | None = None) -> T:
    """Ejecuta factory solo si no hay valor válido en caché."""
    existente = obtener(clave)
    if existente is not None:
        return existente  # type: ignore[return-value]
    valor = factory()
    guardar(clave, valor, ttl=ttl)
    return valor


def limpiar() -> None:
    """Vacía la caché (útil en tests)."""
    _almacen.clear()


def estadisticas() -> dict[str, int]:
    ahora = time.monotonic()
    activos = sum(1 for expira, _ in _almacen.values() if expira > ahora)
    return {"entradas": len(_almacen), "activas": activos}
