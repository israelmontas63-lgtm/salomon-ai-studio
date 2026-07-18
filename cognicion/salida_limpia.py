"""
Sanitiza la salida visible del chat: el contexto RAG/interno nunca debe
aparecer en la burbuja del usuario.
"""

from __future__ import annotations

import re

_MARCADORES_INTERNOS = (
    "[Memoria vectorial",
    "[Memoria inmediata",
    "[Memoria de proyecto",
    "[Memoria de sesión",
    "[Contexto personal",
    "[Datos de clima",
    "[Wikipedia",
    "[Wikidata",
    "[Búsqueda web",
    "[Noticias",
    "[Contexto de visión",
    "[Auto-corrección",
    "[Análisis visual",
    "[Empatía cognitiva",
    "[Comic pack",
    "[Identidad",
    "Pregunta del usuario:",
)

_RE_RELEVANCIA = re.compile(r"\s*\(relevancia:\s*[0-9.]+\)", re.IGNORECASE)
_RE_BLOQUE_MEMORIA = re.compile(
    r"\[Memoria\s+(?:vectorial|inmediata|de proyecto|de sesión)[^\]]*\]"
    r"[\s\S]*?(?=(?:\n\[|\nPregunta del usuario:|\Z))",
    re.IGNORECASE,
)
_RE_INSTRUCCION = re.compile(
    r"(?im)^\s*Instrucción:\s*.*$",
)


def sanitizar_salida_chat(texto: str) -> str:
    """Devuelve solo texto apto para burbuja; elimina fugas de contexto interno."""
    if not texto:
        return texto

    out = texto.replace("\r\n", "\n")

    # Si el modelo o un fallback pegó el bloque de memoria completo, cortarlo
    for marcador in _MARCADORES_INTERNOS:
        idx = out.find(marcador)
        if idx >= 0:
            # Conservar prosa útil anterior al marcador; nunca el bloque interno.
            cabeza = out[:idx].strip()
            cola = out[idx:]
            if cabeza:
                out = cabeza
            elif "Pregunta del usuario:" in cola:
                # Fallback degradado: no hay prosa; no reinyectar el contexto.
                out = ""
            else:
                out = _RE_BLOQUE_MEMORIA.sub("", out).strip()

    out = _RE_BLOQUE_MEMORIA.sub("", out)
    out = _RE_RELEVANCIA.sub("", out)
    out = _RE_INSTRUCCION.sub("", out)

    # Frases típicas de fuga de fallback
    out = re.sub(
        r"(?is)Israel,?\s*me apoy[eé]\s+en nuestra memoria para responderte:\s*",
        "",
        out,
    )
    out = re.sub(
        r"(?im)^\s*\[Memoria vectorial[^\]]*\]\s*$",
        "",
        out,
    )

    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out
