"""Cliente MCP para Salomón."""

from cognicion.mcp.cliente import estado_mcp, invocar_herramienta_mcp, listar_herramientas_mcp
from cognicion.mcp.contrato import ClienteMCP, HerramientaMCP

__all__ = [
    "ClienteMCP",
    "HerramientaMCP",
    "estado_mcp",
    "invocar_herramienta_mcp",
    "listar_herramientas_mcp",
]
