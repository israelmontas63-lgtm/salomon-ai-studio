"""
Ciclo de auto-corrección — detecta errores de consola y sugiere soluciones.
"""

from __future__ import annotations

import re

PATRONES_ERROR = (
    r"traceback",
    r"error:",
    r"exception",
    r"syntaxerror",
    r"typeerror",
    r"valueerror",
    r"modulenotfounderror",
    r"importerror",
    r"attributeerror",
    r"failed",
    r"errno",
    r"exit code",
    r"uncaught",
    r"cannot read",
    r"is not defined",
    r"404",
    r"500",
    r"401",
    r"403",
)


def es_mensaje_de_error(texto: str) -> bool:
    """Detecta si el texto parece un error de consola o terminal."""
    t = (texto or "").lower()
    if len(t) < 12:
        return False
    return any(re.search(patron, t) for patron in PATRONES_ERROR)


def preparar_contexto_autocorreccion(error_texto: str) -> str:
    """Genera contexto para que Gemini proponga corrección proactiva."""
    return f"""[Ciclo de auto-corrección — error detectado]

El sistema reportó el siguiente error:
```
{error_texto.strip()}
```

Instrucción para Salomón:
1. Explica en español dominicano qué significa este error.
2. Identifica la causa raíz más probable en el contexto de Salomón AI Studio.
3. Propón pasos concretos de corrección (archivos, comandos o cambios).
4. Sugiere cómo validar que el problema quedó resuelto.
Sé proactivo, claro y directo."""


def analizar_error_consola(error_texto: str) -> dict:
    """Resumen estructurado del error para metadata."""
    texto = (error_texto or "").strip()
    tipo = "desconocido"

    for nombre in (
        "SyntaxError", "TypeError", "ValueError", "ModuleNotFoundError",
        "ImportError", "AttributeError", "HTTPError",
    ):
        if nombre.lower() in texto.lower():
            tipo = nombre
            break

    return {
        "tipo_error": tipo,
        "longitud": len(texto),
        "detectado": es_mensaje_de_error(texto),
    }
