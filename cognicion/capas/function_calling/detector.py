"""
Detector — decide cuándo activar function-calling sin bloquear el chat normal.
"""

from __future__ import annotations

import re

from settings import FUNCTION_CALLING_HABILITADO, FUNCTION_CALLING_SIEMPRE

_PALABRAS_HERRAMIENTA: dict[str, frozenset[str]] = {
    "corregir": frozenset({"corrige", "corregir", "ortografía", "ortografia", "typo", "error ortográfico"}),
    "traducir": frozenset({"traduce", "traducir", "translate", "inglés", "ingles", "español"}),
    "ayuda": frozenset({"ayuda", "help", "cómo funciona", "como funciona", "tutorial"}),
    "analiticas": frozenset({"analíticas", "analiticas", "estadísticas", "estadisticas", "métricas", "metricas"}),
    "planes": frozenset({"planes", "suscripción", "suscripcion", "premium", "plan"}),
    "seguridad": frozenset({"seguridad", "yiiot", "protección", "proteccion"}),
    "optimizar": frozenset({"optimizar", "rendimiento", "diagnóstico", "diagnostico"}),
    "solar": frozenset({"solar", "fotovoltaico", "paneles", "energía solar"}),
    "resumir": frozenset({"resume", "resumir", "resumen", "archivo", "documento"}),
    "backup_export": frozenset({"backup", "exportar", "respaldo", "guardar historial"}),
}


def debe_usar_function_calling(mensaje: str) -> tuple[bool, list[str]]:
    """
    Returns:
        (activar, herramientas_sugeridas)
    """
    if not FUNCTION_CALLING_HABILITADO:
        return False, []

    if FUNCTION_CALLING_SIEMPRE:
        return True, []

    texto = (mensaje or "").lower()
    sugeridas: list[str] = []

    for tool_id, palabras in _PALABRAS_HERRAMIENTA.items():
        if any(p in texto for p in palabras):
            sugeridas.append(tool_id)

    # Preguntas de acción explícita
    if re.search(r"\b(qué puedes hacer|que puedes hacer|herramientas disponibles)\b", texto):
        sugeridas.append("ayuda")

    return bool(sugeridas), sugeridas
