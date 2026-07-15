"""
Gestor seguro de secretos — solo lectura desde entorno/settings, nunca en código.
"""

from __future__ import annotations

import os
from typing import Any

_CLAVES_CONOCIDAS = (
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
    "OPENWEATHER_API_KEY",
    "SALOMON_API_KEY",
    "SALOMON_ADMIN_KEY",
)

_SETTINGS_MAP = {
    "GEMINI_API_KEY": "GEMINI_API_KEY",
    "OPENAI_API_KEY": "OPENAI_API_KEY",
    "GROQ_API_KEY": "GROQ_API_KEY",
    "OPENWEATHER_API_KEY": "OPENWEATHER_API_KEY",
    "SALOMON_API_KEY": "SALOMON_API_KEY",
    "SALOMON_ADMIN_KEY": "SALOMON_ADMIN_KEY",
}


def obtener_secreto(nombre: str) -> str:
    """Lee un secreto. Prioriza settings (testeable) y luego os.environ."""
    attr = _SETTINGS_MAP.get(nombre)
    if attr:
        try:
            import settings

            valor = getattr(settings, attr, "")
            if valor:
                return str(valor).strip()
        except ImportError:
            pass
    return os.getenv(nombre, "").strip()


def secreto_configurado(nombre: str) -> bool:
    return bool(obtener_secreto(nombre))


def inventario_secretos() -> list[dict[str, Any]]:
    """Lista qué secretos existen sin revelar valores."""
    return [
        {
            "nombre": clave,
            "configurado": secreto_configurado(clave),
            "longitud": len(obtener_secreto(clave)),
        }
        for clave in _CLAVES_CONOCIDAS
    ]


def claves_activas() -> dict[str, bool]:
    return {
        "gemini": secreto_configurado("GEMINI_API_KEY"),
        "openai": secreto_configurado("OPENAI_API_KEY"),
        "groq": secreto_configurado("GROQ_API_KEY"),
        "openweather": secreto_configurado("OPENWEATHER_API_KEY"),
        "api_protegida": secreto_configurado("SALOMON_API_KEY"),
        "admin_protegido": secreto_configurado("SALOMON_ADMIN_KEY"),
    }
