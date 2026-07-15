"""
Contratos del núcleo OS — interfaces estables entre componentes.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ComponenteOS(Protocol):
    """Componente registrable en el kernel."""

    id: str
    nombre: str
    version: str

    def estado(self) -> dict[str, Any]: ...


@runtime_checkable
class MotorOS(Protocol):
    """Motor cognitivo del sistema operativo."""

    id: str
    nombre: str

    def disponible(self) -> bool: ...

    def describir(self) -> dict[str, Any]: ...
