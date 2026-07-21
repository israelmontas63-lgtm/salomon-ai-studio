# -*- coding: utf-8 -*-
"""
Tiempo local — fecha/hora sin API externa (evita Error 40–49 en reloj).

Zona canónica de Israel / Salomón: América/Santo_Domingo (AST, UTC−4).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

TZ_NAME = "America/Santo_Domingo"

try:
    from zoneinfo import ZoneInfo

    _TZ = ZoneInfo(TZ_NAME)
except Exception:  # Windows sin tzdata / entorno mínimo
    from datetime import timedelta

    _TZ = timezone(timedelta(hours=-4))

_MESES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
_DIAS = (
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
)

# Consultas puras de reloj (fast-path, sin LLM)
_RE_FECHA_HORA = re.compile(
    r"(?ix)^\s*"
    r"(?:por\s+favor[, ]*)?"
    r"(?:dime|dime\s+por\s+favor|cual|cu[aá]l|me\s+dices)?\s*"
    r"(?:"
    r"(?:qu[eé]\s+)?"
    r"(?:"
    r"fecha\s+y\s+(?:la\s+)?hora|"
    r"hora\s+y\s+(?:la\s+)?fecha|"
    r"(?:la\s+)?fecha|"
    r"(?:la\s+)?hora|"
    r"(?:el\s+)?d[ií]a"
    r")"
    r"(?:\s+(?:es|son|tenemos|hay))?"
    r"(?:\s+(?:hoy|ahora|actual(?:mente)?))?"
    r"|"
    r"hoy\s+(?:qu[eé]\s+)?(?:d[ií]a|fecha)\s+(?:es|tenemos)"
    r"|"
    r"what\s+time\s+is\s+it"
    r"|"
    r"what(?:'?s|\s+is)\s+the\s+(?:date|time)"
    r"|"
    r"current\s+(?:date|time)"
    r")"
    r"\s*[\?¿.!]*\s*$"
)

# Señal débil: inyectar bloque de tiempo al enriquecer (aún puede ir al LLM)
_RE_MENCION_TIEMPO = re.compile(
    r"(?i)\b("
    r"hora|fecha|reloj|calendario|timezone|zona\s+horaria|"
    r"qu[eé]\s+d[ií]a|hoy\s+es|ahora\s+mismo"
    r")\b"
)


def ahora_rd() -> datetime:
    return datetime.now(_TZ)


def bloque_tiempo_sistema() -> str:
    """Contexto corto para system/enrich — ancla factual al modelo."""
    n = ahora_rd()
    utc = datetime.now(timezone.utc)
    return (
        f"[Tiempo real — {TZ_NAME}]\n"
        f"Fecha local: {_DIAS[n.weekday()]} {n.day} de {_MESES[n.month - 1]} de {n.year}.\n"
        f"Hora local: {n.strftime('%H:%M:%S')} (AST, UTC−4).\n"
        f"UTC: {utc.strftime('%Y-%m-%d %H:%M:%S')}Z.\n"
        "Usa SOLO estos datos si preguntan la hora o la fecha; no inventes."
    )


def es_consulta_fecha_hora(texto: str) -> bool:
    t = (texto or "").strip()
    if not t or len(t) > 120:
        return False
    return bool(_RE_FECHA_HORA.match(t))


def menciona_fecha_hora(texto: str) -> bool:
    return bool(_RE_MENCION_TIEMPO.search(texto or ""))


def respuesta_fecha_hora(texto: str = "") -> dict[str, Any]:
    """
    Respuesta inmediata sin proveedor LLM.
    Cubre fecha, hora o ambas según la pregunta.
    """
    n = ahora_rd()
    t = (texto or "").lower()
    fecha = f"{_DIAS[n.weekday()]} {n.day} de {_MESES[n.month - 1]} de {n.year}"
    hora = n.strftime("%H:%M")
    solo_hora = bool(re.search(r"(?i)\bhora\b", t)) and not re.search(
        r"(?i)\b(fecha|d[ií]a)\b", t
    )
    solo_fecha = bool(re.search(r"(?i)\b(fecha|d[ií]a)\b", t)) and not re.search(
        r"(?i)\bhora\b", t
    )
    if solo_hora:
        frase = f"Israel, son las {hora} (hora de República Dominicana, AST)."
    elif solo_fecha:
        frase = f"Israel, hoy es {fecha}."
    else:
        frase = f"Israel, hoy es {fecha} y son las {hora} (AST, República Dominicana)."
    return {
        "texto": frase,
        "exito": True,
        "metadata": {
            "cognicion": {
                "fast_path": "fecha_hora",
                "timezone": TZ_NAME,
                "iso_local": n.isoformat(),
                "fuente": "cognicion.tiempo_local",
            }
        },
    }
