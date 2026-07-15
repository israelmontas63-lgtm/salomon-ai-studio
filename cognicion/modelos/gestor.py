"""
Gestor de modelos — selección por tarea (orquestación multi-modelo).
"""

from __future__ import annotations

from enum import Enum

from settings import (
    GEMINI_MODEL,
    GEMINI_VISION_MODEL,
    GROQ_MODEL,
    MODEL_PROVIDER,
    OPENAI_MODEL,
)


class TareaModelo(str, Enum):
    CHAT = "chat"
    VISION = "vision"
    RAZONAMIENTO = "razonamiento"
    CODIGO = "codigo"
    RAPIDO = "rapido"


_PERFILES: dict[TareaModelo, dict[str, str]] = {
    TareaModelo.CHAT: {"tarea": "chat", "descripcion": "Conversación general"},
    TareaModelo.VISION: {"tarea": "vision", "descripcion": "Análisis multimodal"},
    TareaModelo.RAZONAMIENTO: {
        "tarea": "razonamiento",
        "descripcion": "Chain of Thought y problemas complejos",
    },
    TareaModelo.CODIGO: {"tarea": "codigo", "descripcion": "Generación y corrección de código"},
    TareaModelo.RAPIDO: {"tarea": "rapido", "descripcion": "Respuestas de baja latencia"},
}

_ALIASES: dict[str, TareaModelo] = {
    "chat": TareaModelo.CHAT,
    "vision": TareaModelo.VISION,
    "razonamiento": TareaModelo.RAZONAMIENTO,
    "tecnico": TareaModelo.RAZONAMIENTO,
    "codigo": TareaModelo.CODIGO,
    "code": TareaModelo.CODIGO,
    "rapido": TareaModelo.RAPIDO,
    "fast": TareaModelo.RAPIDO,
}


def normalizar_tarea(valor: str | None) -> TareaModelo:
    if not valor:
        return TareaModelo.CHAT
    return _ALIASES.get(valor.strip().lower(), TareaModelo.CHAT)


def resolver_modelo(tarea: str | TareaModelo | None = None) -> dict[str, str | None]:
    """
    Resuelve proveedor y modelo según la tarea.

    Returns:
        dict con tarea, proveedor_sugerido, model_name, descripcion
    """
    t = tarea if isinstance(tarea, TareaModelo) else normalizar_tarea(str(tarea or ""))
    perfil = _PERFILES[t]

    proveedor = MODEL_PROVIDER
    model_name: str | None = None

    if t == TareaModelo.VISION:
        model_name = GEMINI_VISION_MODEL
    elif t == TareaModelo.RAPIDO:
        model_name = GROQ_MODEL if proveedor == "groq" else OPENAI_MODEL
    elif t in (TareaModelo.RAZONAMIENTO, TareaModelo.CODIGO):
        model_name = OPENAI_MODEL if proveedor == "openai" else GEMINI_MODEL
    else:
        model_name = {
            "gemini": GEMINI_MODEL,
            "openai": OPENAI_MODEL,
            "groq": GROQ_MODEL,
        }.get(proveedor, GEMINI_MODEL)

    return {
        "tarea": t.value,
        "descripcion": perfil["descripcion"],
        "proveedor_sugerido": proveedor,
        "model_name": model_name,
    }


def listar_tareas() -> list[dict[str, str]]:
    return [
        {"id": t.value, **info}
        for t, info in _PERFILES.items()
    ]
