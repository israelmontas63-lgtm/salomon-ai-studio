# -*- coding: utf-8 -*-
"""Filtro de Claridad — ruido ↓ · intención central de Israel ↑ (PWA-safe)."""

from __future__ import annotations

import re
from typing import Any, Final

# Umbral mínimo de intención central (caracteres útiles)
_UMBRAL_INTENCION: Final[int] = 12

_RUIDO = re.compile(
    r"\b(por favor|pls|please|eh+|este+|o sea|tipo|literalmente|ok+|vale)\b",
    re.IGNORECASE,
)

# Abreviaturas / modismos donde '.' no corta oración
_ABREV = re.compile(
    r"(?i)\b("
    r"sr|sra|dr|dra|etc|vs|p\.?\s*ej|ej|approx|n[uú]m|vol|cap|"
    r"ud|uds|pág|pag|a\.?\s*m|p\.?\s*m|israel|ia|pwa|api|tts|stt"
    r")\.\s*",
)

# Cortes de oración: . ! ? … ¿ ¡ pero NO dentro de comillas/paréntesis anidados
_RE_CORTE = re.compile(
    r"""
    (?<![\w\.])          # no continuar abreviatura pegada
    (?P<punct>[.!?…]+)   # puntuación terminal
    (?=\s+|["'»”)\]]|$)  # seguido de espacio, cierre o fin
    """,
    re.VERBOSE,
)


def _proteger_abreviaturas(texto: str) -> tuple[str, list[str]]:
    """Sustituye puntos de abreviatura por marcadores para no cortar ahí."""
    slots: list[str] = []

    def _sub(m: re.Match[str]) -> str:
        slots.append(m.group(0))
        return f"§ABR{len(slots) - 1}§"

    return _ABREV.sub(_sub, texto), slots


def _restaurar_abreviaturas(texto: str, slots: list[str]) -> str:
    out = texto
    for i, val in enumerate(slots):
        out = out.replace(f"§ABR{i}§", val)
    return out


def _balance_ok(fragmento: str) -> bool:
    """True si comillas/paréntesis están balanceados (evita cortes anidados)."""
    pairs = (("(", ")"), ("[", "]"), ("{", "}"), ("«", "»"))
    for a, b in pairs:
        if fragmento.count(a) != fragmento.count(b):
            return False
    # Comillas simples/dobles: paridad aproximada
    if fragmento.count('"') % 2 != 0:
        return False
    if fragmento.count("«") != fragmento.count("»"):
        return False
    # Apostrofes tipográficos de apertura/cierre
    if fragmento.count("“") != fragmento.count("”"):
        return False
    return True


def _segmentar_oraciones(texto: str) -> list[str]:
    """Segmenta por puntuación terminal respetando anidación y abreviaturas."""
    protegido, slots = _proteger_abreviaturas(texto)
    partes: list[str] = []
    inicio = 0
    for m in _RE_CORTE.finditer(protegido):
        fin = m.end()
        cand = protegido[inicio:fin].strip()
        if not cand:
            continue
        if not _balance_ok(cand):
            # Puntuación anidada: no cortar; seguir acumulando
            continue
        partes.append(_restaurar_abreviaturas(cand, slots))
        inicio = fin
    cola = protegido[inicio:].strip()
    if cola:
        partes.append(_restaurar_abreviaturas(cola, slots))
    # Si el regex no cortó nada útil, devolver el texto íntegro
    if not partes:
        return [texto.strip()] if texto.strip() else []
    return [p for p in partes if p.strip()]


def _clasificar_deseo(lower: str) -> str:
    if any(
        x in lower
        for x in ("haz", "implementa", "crea", "arregla", "corrige", "deploy", "genera")
    ):
        return "accion"
    if any(
        x in lower
        for x in ("explica", "qué es", "que es", "cómo", "como", "por qué", "por que")
    ):
        return "comprension"
    if any(
        x in lower
        for x in ("busca", "investiga", "tendencia", "mercado", "oportunidad")
    ):
        return "exploracion"
    if any(x in lower for x in ("mal", "error", "equivoc", "no es eso", "otra vez")):
        return "correccion"
    return "informacion"


def filtrar_claridad(mensaje: str) -> dict[str, Any]:
    """
    Extrae intención central y versión enfocada (sin LLM obligatorio).

    Si la intención segmentada es más corta que el umbral, preserva el
    mensaje completo de Israel (sin truncado arbitrario del sentido).
    """
    bruto = (mensaje or "").strip()
    if not bruto:
        return {
            "ok": False,
            "intencion_central": "",
            "enfocado": "",
            "ruido_filtrado": True,
            "deseo": "sin_mensaje",
            "umbral": _UMBRAL_INTENCION,
            "respaldo_contexto": False,
        }

    limpio = _RUIDO.sub(" ", bruto)
    limpio = re.sub(r"\s+", " ", limpio).strip()
    # No strip agresivo de ¿¡ al inicio — preserva modismos de Israel
    limpio = limpio.strip(" \t")
    # Si el filtro de ruido dejó casi nada (p.ej. solo "Ok."), preservar mensaje de Israel
    util = re.sub(r"^[\s.¡!¿?,;:…]+|[\s.¡!¿?,;:…]+$", "", limpio)
    if len(util) < _UMBRAL_INTENCION:
        limpio = bruto
    lower = limpio.lower()
    deseo = _clasificar_deseo(lower)

    partes = _segmentar_oraciones(limpio)
    central = (partes[0] if partes else limpio).strip()
    respaldo = False

    # Si el corte dejó un fragmento demasiado corto, preservar contexto completo
    if len(central) < _UMBRAL_INTENCION:
        respaldo = True
        if len(partes) > 1:
            # Unir primeras oraciones hasta superar umbral, sin pasar del mensaje
            acumulado = central
            for p in partes[1:]:
                acumulado = f"{acumulado} {p}".strip()
                if len(acumulado) >= _UMBRAL_INTENCION:
                    break
            central = acumulado if len(acumulado) >= _UMBRAL_INTENCION else limpio
        else:
            central = limpio

    # Nunca truncar el sentido: si aún es corto, usar mensaje limpio íntegro
    if len(central) < _UMBRAL_INTENCION:
        respaldo = True
        central = limpio

    return {
        "ok": True,
        "intencion_central": central[:800],
        "enfocado": limpio[:1200],
        "ruido_filtrado": limpio != bruto,
        "deseo": deseo,
        "umbral": _UMBRAL_INTENCION,
        "respaldo_contexto": respaldo,
        "oraciones": len(partes),
        "solucion_directa": (
            "Enfócate en la intención central; evita rodeos y listas de capacidades."
        ),
    }
