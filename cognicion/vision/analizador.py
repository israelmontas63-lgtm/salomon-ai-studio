"""
Visión — análisis de imágenes con Gemini multimodal.

Modos:
  • escena  — foto del mundo real (objetos, lugar, contexto) — Fase 1
  • ui      — captura de pantalla / auditoría de interfaz
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

from cognicion.config import GEMINI_VISION_MODEL
from cognicion.llm import analizar_imagen_gemini, llm_disponible


@dataclass
class ResultadoVision:
    exito: bool
    contexto: str
    error: str | None = None


_PROMPT_ESCENA = """Eres el sistema de visión de Salomón AI. Analiza esta imagen del mundo real.

Extrae, en español dominicano claro y conciso:
1. Qué se ve en general (escena / lugar).
2. Objetos o personas relevantes.
3. Texto legible si aparece (rótulos, pantallas).
4. Contexto útil (hora del día, interior/exterior, actividad).
5. Cualquier detalle que ayude a responder al usuario.

No inventes lo que no se ve. Si algo es dudoso, dilo.
Responde en 4–8 frases útiles, sin listas técnicas de scores."""


_PROMPT_UI = """Analiza esta captura de pantalla de la interfaz Salomón AI Studio.

Identifica:
1. Errores visuales (alineación, contraste, elementos cortados).
2. Consistencia con la estética negro y oro.
3. Problemas de usabilidad o botones que parezcan inactivos.
4. Cualquier fallo evidente en el diseño.

Responde en español dominicano, de forma concisa y técnica."""


def _correr(
    imagen_base64: str,
    mime_type: str,
    prompt: str,
    contexto_usuario: str,
    etiqueta: str,
    instruccion: str,
) -> ResultadoVision:
    if not imagen_base64:
        return ResultadoVision(False, "", error="imagen_vacia")

    if not llm_disponible():
        return ResultadoVision(False, "", error="llm_no_configurado")

    try:
        imagen_bytes = base64.b64decode(imagen_base64)
        if contexto_usuario.strip():
            prompt = f"{prompt}\n\nContexto del usuario: {contexto_usuario.strip()}"

        texto = analizar_imagen_gemini(
            prompt,
            imagen_bytes,
            mime_type=mime_type,
            model_name=GEMINI_VISION_MODEL,
        )
        if not texto:
            return ResultadoVision(False, "", error="analisis_vacio")

        contexto = f"""[{etiqueta}]
{texto}

Instrucción: {instruccion}"""
        return ResultadoVision(True, contexto)
    except Exception as exc:
        return ResultadoVision(False, "", error=str(type(exc).__name__))


def analizar_escena(
    imagen_base64: str,
    mime_type: str = "image/png",
    contexto_usuario: str = "",
) -> ResultadoVision:
    """Análisis general de foto (Fase 1 — ver de verdad)."""
    return _correr(
        imagen_base64,
        mime_type,
        _PROMPT_ESCENA,
        contexto_usuario,
        "Análisis visual — escena",
        "Usa este análisis como percepción visual interna. "
        "Descríbele a Israel lo esencial en prosa natural; no pegues etiquetas técnicas.",
    )


def analizar_imagen(
    imagen_base64: str,
    mime_type: str = "image/png",
    contexto_usuario: str = "",
) -> ResultadoVision:
    """
    Compatibilidad: por defecto analiza como escena del mundo real.
    Si el contexto pide UI/interfaz, usa el prompt de auditoría.
    """
    t = (contexto_usuario or "").lower()
    if any(x in t for x in ("interfaz", "ui", "pantalla", "layout", "botón", "boton", "captura de pantalla")):
        return _correr(
            imagen_base64,
            mime_type,
            _PROMPT_UI,
            contexto_usuario,
            "Análisis visual — captura de pantalla",
            "Usa este análisis para responder al usuario sobre el estado visual de la interfaz.",
        )
    return analizar_escena(imagen_base64, mime_type=mime_type, contexto_usuario=contexto_usuario)
