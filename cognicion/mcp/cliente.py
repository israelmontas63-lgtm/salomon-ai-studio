"""
Cliente MCP — esqueleto para conectar servidores externos (Fase 4).
"""

from __future__ import annotations

import json
import os
from typing import Any

from cognicion.mcp.contrato import HerramientaMCP
from cognicion.registro import obtener_logger

_log = obtener_logger("mcp")


def _parsear_servidores() -> list[dict[str, Any]]:
    raw = os.getenv("MCP_SERVERS", "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def estado_mcp() -> dict[str, Any]:
    servidores = _parsear_servidores()
    return {
        "habilitado": bool(servidores),
        "servidores_configurados": len(servidores),
        "servidores": [s.get("nombre", s.get("id", "?")) for s in servidores],
        "modo": "cliente",
        "fase": "esqueleto",
    }


def listar_herramientas_mcp() -> list[HerramientaMCP]:
    """Placeholder — Fase 4 conectará vía stdio/SSE."""
    return []


def invocar_herramienta_mcp(nombre: str, argumentos: dict[str, Any]) -> Any:
    raise NotImplementedError(
        "Cliente MCP en fase esqueleto. Configure MCP_SERVERS en Fase 4."
    )
