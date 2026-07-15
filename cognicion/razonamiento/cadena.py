"""
Chain of Thought (CoT) — razonamiento lógico antes de responder.
"""

from __future__ import annotations

import re

PALABRAS_TECNICAS = (
    "código", "codigo", "error", "bug", "implementa", "implementar",
    "función", "funcion", "corregir", "corrección", "correccion",
    "debug", "arregla", "arreglar", "refactor", "api", "endpoint",
    "backend", "frontend", "react", "python", "fastapi", "gemini",
    "integrar", "módulo", "modulo", "archivo", "deploy", "configura",
    "typescript", "javascript", "css", "html", "base de datos",
)

MARCADOR_RESPUESTA = "---RESPUESTA---"


def requiere_razonamiento(entrada: str) -> bool:
    """Detecta tareas técnicas que benefician de CoT."""
    texto = (entrada or "").lower()
    return any(palabra in texto for palabra in PALABRAS_TECNICAS)


def aplicar_cadena_de_pensamiento(entrada: str) -> str:
    """Envuelve la entrada con instrucciones de razonamiento paso a paso."""
    return f"""[Modo razonamiento técnico — Chain of Thought]

Antes de dar tu respuesta final, realiza un análisis lógico interno:
1. Comprende exactamente qué pide el usuario.
2. Enumera los pasos técnicos necesarios en orden.
3. Identifica posibles errores, riesgos o dependencias.
4. Valida que la solución sea coherente con el proyecto Salomón AI Studio.

Luego escribe tu respuesta final para el usuario DESPUÉS de la línea exacta:
{MARCADOR_RESPUESTA}

Tu respuesta final debe ser clara, en español dominicano natural, y lista para ejecutar.

Tarea del usuario:
{entrada}"""


def extraer_respuesta_final(texto: str) -> str:
    """Extrae la respuesta final si Gemini usó el marcador CoT."""
    if MARCADOR_RESPUESTA in texto:
        partes = texto.split(MARCADOR_RESPUESTA, 1)
        final = partes[1].strip()
        return final if final else texto.strip()

    texto = re.sub(
        r"(?i)^\s*\[razonamiento interno\].*?(?=\n\n|\Z)",
        "",
        texto,
        flags=re.DOTALL,
    )
    return texto.strip() or texto
