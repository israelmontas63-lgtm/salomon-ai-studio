"""
Contratos MCP (Model Context Protocol) — puente a herramientas externas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class HerramientaMCP:
    nombre: str
    descripcion: str
    servidor: str
    parametros: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ClienteMCP(Protocol):
    """Interfaz mínima de un cliente MCP."""

    def conectado(self) -> bool: ...

    def listar_herramientas(self) -> list[HerramientaMCP]: ...

    def invocar(self, nombre: str, argumentos: dict[str, Any]) -> Any: ...
