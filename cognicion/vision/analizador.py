"""
Visión — análisis de capturas de pantalla con Gemini multimodal.
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


def analizar_imagen(
    imagen_base64: str,
    mime_type: str = "image/png",
    contexto_usuario: str = "",
) -> ResultadoVision:
    """Analiza una captura y devuelve contexto para el chat."""
    if not imagen_base64:
        return ResultadoVision(False, "", error="imagen_vacia")

    if not llm_disponible():
        return ResultadoVision(
            False,
            "",
            error="llm_no_configurado",
        )

    try:
        imagen_bytes = base64.b64decode(imagen_base64)
        prompt = """Analiza esta captura de pantalla de la interfaz Salomón AI Studio.

Identifica:
1. Errores visuales (alineación, contraste, elementos cortados).
2. Consistencia con la estética negro y oro.
3. Problemas de usabilidad o botones que parezcan inactivos.
4. Cualquier fallo evidente en el diseño.

Responde en español dominicano, de forma concisa y técnica."""

        if contexto_usuario.strip():
            prompt += f"\n\nContexto del usuario: {contexto_usuario}"

        texto = analizar_imagen_gemini(
            prompt,
            imagen_bytes,
            mime_type=mime_type,
            model_name=GEMINI_VISION_MODEL,
        )
        if not texto:
            return ResultadoVision(False, "", error="analisis_vacio")

        contexto = f"""[Análisis visual — captura de pantalla]
{texto}

Instrucción: Usa este análisis para responder al usuario sobre el estado visual de la interfaz."""
        return ResultadoVision(True, contexto)

    except Exception as exc:
        return ResultadoVision(False, "", error=str(type(exc).__name__))
