# -*- coding: utf-8 -*-
"""
Prompt Enhancer — expande peticiones visuales a prompts HD
(iluminación, estilo, composición, realismo) antes de generar.
"""

from __future__ import annotations

from typing import Any

from settings import MEDIA_PROMPT_ENHANCER


_SUFIJO_HD = (
    "high-definition, sharp detail, cinematic lighting, balanced composition, "
    "depth of field, professional color grading, photorealistic materials, "
    "clean background hierarchy, no illegible text, premium quality"
)

_SUFIJO_MARCA = (
    "elegant black and gold aesthetic when appropriate, refined contrast, "
    "Salomon AI Studio visual language"
)


def _mejorar_heuristico(prompt: str, *, video: bool = False) -> str:
    base = (prompt or "").strip()
    if not base:
        return base
    lower = base.lower()
    partes = [base]
    if "ilumin" not in lower and "light" not in lower:
        partes.append("soft key light with subtle rim light")
    if "estilo" not in lower and "style" not in lower:
        partes.append("cohesive art direction")
    if "compos" not in lower:
        partes.append("rule-of-thirds composition")
    if video:
        partes.append("smooth motion, stable camera, natural pacing")
    else:
        partes.append(_SUFIJO_HD)
    if "negro" not in lower and "oro" not in lower and "gold" not in lower:
        partes.append(_SUFIJO_MARCA)
    return ", ".join(partes)


def mejorar_prompt(
    prompt: str,
    *,
    video: bool = False,
    usar_llm: bool = True,
) -> dict[str, Any]:
    """
    Expande el prompt del usuario. Si el LLM falla, usa heurística HD.
    """
    original = (prompt or "").strip()
    if not original:
        return {
            "exito": False,
            "prompt_original": original,
            "prompt_mejorado": original,
            "motor": "none",
        }

    if not MEDIA_PROMPT_ENHANCER:
        mejorado = _mejorar_heuristico(original, video=video)
        return {
            "exito": True,
            "prompt_original": original,
            "prompt_mejorado": mejorado,
            "motor": "heuristico_off_flag",
        }

    if usar_llm:
        try:
            from cognicion.llm import chat_con_historial, llm_disponible

            if llm_disponible():
                sistema = (
                    "Eres el Prompt Enhancer de Salomón AI. Reescribe el prompt del usuario "
                    "para generación visual HD. Añade iluminación, estilo, composición y "
                    "realismo. Responde SOLO con el prompt mejorado en inglés técnico de arte, "
                    "sin comillas ni explicación. Máximo 80 palabras."
                )
                if video:
                    sistema += " Incluye motion y cámara."
                out = chat_con_historial(
                    f"Prompt usuario: {original}",
                    [],
                    sistema,
                )
                texto = (out or "").strip() if isinstance(out, str) else str(out or "").strip()
                if texto and len(texto) > 12 and "error" not in texto.lower()[:40]:
                    # Limpiar cercas markdown
                    texto = texto.strip("`").strip()
                    if texto.lower().startswith("prompt"):
                        texto = texto.split(":", 1)[-1].strip()
                    return {
                        "exito": True,
                        "prompt_original": original,
                        "prompt_mejorado": texto[:600],
                        "motor": "llm",
                    }
        except Exception as exc:
            heur = _mejorar_heuristico(original, video=video)
            return {
                "exito": True,
                "prompt_original": original,
                "prompt_mejorado": heur,
                "motor": "heuristico_fallback",
                "aviso": type(exc).__name__,
            }

    mejorado = _mejorar_heuristico(original, video=video)
    return {
        "exito": True,
        "prompt_original": original,
        "prompt_mejorado": mejorado,
        "motor": "heuristico",
    }
