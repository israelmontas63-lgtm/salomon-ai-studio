"""
Gestor de modelos — Smart Router multi-modelo por tarea.
"""

from __future__ import annotations

from enum import Enum

from settings import (
    CEREBRAS_API_KEY,
    CEREBRAS_MODEL,
    DEEPSEEK_API_KEY,
    DEEPSEEK_MODEL,
    GEMINI_MODEL,
    GEMINI_VISION_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
    MISTRAL_API_KEY,
    MISTRAL_MODEL,
    MODEL_PROVIDER,
    OPENAI_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
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
    "debug": TareaModelo.CODIGO,
    "codigo": TareaModelo.CODIGO,
    "code": TareaModelo.CODIGO,
    "rapido": TareaModelo.RAPIDO,
    "fast": TareaModelo.RAPIDO,
}


def normalizar_tarea(valor: str | None) -> TareaModelo:
    if not valor:
        return TareaModelo.CHAT
    return _ALIASES.get(valor.strip().lower(), TareaModelo.CHAT)


def _key(val: str | None) -> bool:
    return bool((val or "").strip())


def resolver_modelo(tarea: str | TareaModelo | None = None) -> dict[str, str | None]:
    """Resuelve proveedor y modelo según la tarea (Smart Router)."""
    t = tarea if isinstance(tarea, TareaModelo) else normalizar_tarea(str(tarea or ""))
    perfil = _PERFILES[t]

    proveedor = (MODEL_PROVIDER or "gemini").strip().lower()
    model_name: str | None = None

    if t == TareaModelo.VISION:
        model_name = GEMINI_VISION_MODEL
        proveedor = "gemini"
    elif t == TareaModelo.RAPIDO:
        if _key(GROQ_API_KEY):
            proveedor = "groq"
            model_name = GROQ_MODEL
        elif _key(CEREBRAS_API_KEY):
            proveedor = "cerebras"
            model_name = CEREBRAS_MODEL
        else:
            model_name = OPENAI_MODEL if proveedor == "openai" else GROQ_MODEL
    elif t in (TareaModelo.RAZONAMIENTO, TareaModelo.CODIGO):
        if _key(DEEPSEEK_API_KEY):
            proveedor = "deepseek"
            model_name = DEEPSEEK_MODEL
        elif _key(OPENROUTER_API_KEY):
            proveedor = "openrouter"
            model_name = OPENROUTER_MODEL
        elif _key(CEREBRAS_API_KEY):
            proveedor = "cerebras"
            model_name = CEREBRAS_MODEL
        elif _key(MISTRAL_API_KEY):
            proveedor = "mistral"
            model_name = MISTRAL_MODEL
        elif proveedor == "openai":
            model_name = OPENAI_MODEL
        else:
            model_name = GEMINI_MODEL
    else:
        model_name = {
            "gemini": GEMINI_MODEL,
            "deepseek": DEEPSEEK_MODEL,
            "openrouter": OPENROUTER_MODEL,
            "cerebras": CEREBRAS_MODEL,
            "mistral": MISTRAL_MODEL,
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
    return [{"id": t.value, **info} for t, info in _PERFILES.items()]
