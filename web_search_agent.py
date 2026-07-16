"""
Agente de búsqueda web — fachada activa hacia cognicion.busqueda.
Verifica permisos/env y expone el pipeline de consultas externas.
"""

from __future__ import annotations

from typing import Any

from cognicion.busqueda.agente import (
    buscar_web,
    necesita_busqueda_web,
    responder_con_busqueda,
)
from settings import BUSQUEDA_WEB_AUTO, TAVILY_API_KEY


def estado_conectividad() -> dict[str, Any]:
    return {
        "modulo": "web_search_agent",
        "version": "1.3",
        "activo": True,
        "busqueda_web_auto": BUSQUEDA_WEB_AUTO,
        "tavily_key": bool((TAVILY_API_KEY or "").strip()),
        "fallback_ddg": True,
    }


def consultar(mensaje: str) -> dict[str, Any]:
    """Ejecuta búsqueda si el mensaje lo requiere; si no, indica omisión."""
    if not necesita_busqueda_web(mensaje):
        return {"exito": False, "omitido": True, "motivo": "no_requiere_busqueda"}
    return responder_con_busqueda(mensaje)


# Reexportas para imports directos
__all__ = [
    "buscar_web",
    "necesita_busqueda_web",
    "responder_con_busqueda",
    "estado_conectividad",
    "consultar",
]


if __name__ == "__main__":
    import json

    print(json.dumps(estado_conectividad(), ensure_ascii=False, indent=2))
