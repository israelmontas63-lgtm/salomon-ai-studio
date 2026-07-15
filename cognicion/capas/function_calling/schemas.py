"""
Esquemas de herramientas para LLM function-calling.
Lee el registry existente sin modificar herramientas.py.
"""

from __future__ import annotations

from typing import Any

import herramientas

# Herramientas permitidas para el LLM (excluye CLI y backup_import por seguridad)
_HERRAMIENTAS_LLM = frozenset({
    "corregir",
    "traducir",
    "ayuda",
    "analiticas",
    "planes",
    "seguridad",
    "optimizar",
    "solar",
    "resumir",
    "backup_export",
})

_PARAMETROS: dict[str, dict[str, dict[str, Any]]] = {
    "corregir": {
        "texto": {"type": "string", "description": "Texto a corregir ortográficamente"},
    },
    "traducir": {
        "texto": {"type": "string", "description": "Texto a traducir"},
        "origen": {"type": "string", "description": "Idioma origen (es, en)", "default": "es"},
        "destino": {"type": "string", "description": "Idioma destino (es, en)", "default": "en"},
    },
    "analiticas": {
        "session_turnos": {"type": "integer", "description": "Número de turnos de la sesión"},
    },
    "resumir": {
        "nombre": {"type": "string", "description": "Nombre del archivo"},
        "contenido": {"type": "string", "description": "Contenido del archivo a resumir"},
    },
    "backup_export": {
        "historial": {"type": "array", "description": "Historial de mensajes", "items": {"type": "object"}},
        "config": {"type": "object", "description": "Configuración a exportar"},
    },
}


def herramientas_permitidas() -> frozenset[str]:
    return _HERRAMIENTAS_LLM


def construir_esquemas_openai() -> list[dict[str, Any]]:
    """Convierte el registry a formato tools de OpenAI."""
    esquemas: list[dict[str, Any]] = []
    for h in herramientas.listar_herramientas():
        if h.id not in _HERRAMIENTAS_LLM:
            continue
        props = _PARAMETROS.get(h.id, {})
        required = list(props.keys()) if props else []
        esquemas.append({
            "type": "function",
            "function": {
                "name": h.id,
                "description": h.descripcion,
                "parameters": {
                    "type": "object",
                    "properties": props or {},
                    "required": required,
                },
            },
        })
    return esquemas


def listar_para_api() -> list[dict[str, str]]:
    return [
        {"id": h.id, "nombre": h.nombre, "descripcion": h.descripcion}
        for h in herramientas.listar_herramientas()
        if h.id in _HERRAMIENTAS_LLM
    ]
