# -*- coding: utf-8 -*-
"""
Memory Cortex — contexto local / conversación.
Web SOLO con: «Busca en la web sobre …»
"""

from __future__ import annotations

import re

# Única familia permitida (pedido explícito de Israel Monta)
_RE_BUSCA_WEB_SOBRE = re.compile(
    r"(?i)\b("
    r"busca\s+en\s+la\s+web\s+sobre|"
    r"buscar\s+en\s+la\s+web\s+sobre|"
    r"busca\s+en\s+internet\s+sobre|"
    r"buscar\s+en\s+internet\s+sobre|"
    r"busca\s+en\s+wikipedia\s+sobre|"
    r"buscar\s+en\s+wikipedia\s+sobre"
    r")\b"
)


def pedido_busqueda_explicito(mensaje: str) -> bool:
    """True únicamente ante «Busca en la web sobre…» (o variante canónica)."""
    t = (mensaje or "").strip()
    if not t:
        return False
    return bool(_RE_BUSCA_WEB_SOBRE.search(t))


def es_saludo_o_charla_simple(mensaje: str) -> bool:
    t = (mensaje or "").strip().lower()
    if not t or len(t) < 3:
        return True
    saludos = (
        "hola",
        "hi",
        "hey",
        "buenas",
        "saludos",
        "qué tal",
        "que tal",
        "cómo estás",
        "como estas",
        "buenos días",
        "buenos dias",
        "buenas tardes",
        "buenas noches",
        "israel",
        "salomón",
        "salomon",
    )
    if t in saludos:
        return True
    return any(t.startswith(s + " ") or t.startswith(s + ",") for s in saludos)


def web_agentes_autorizados() -> bool:
    """
    En modo ejecución + SBI_ENABLED, los agentes usan APIs web (Tavily/etc.).
    El usuario casual sigue pudiendo forzar con «Busca en la web sobre…».
    """
    try:
        from settings import MODO_EJECUCION, SBI_ENABLED

        return bool(MODO_EJECUCION) and bool(SBI_ENABLED)
    except Exception:
        return False


def cortex_status() -> dict:
    agentes = web_agentes_autorizados()
    return {
        "externo_bloqueado": not agentes,
        "modo": "ejecucion_neuronal" if agentes else "contexto_usuario_y_hilo",
        "web_solo_si": "Busca en la web sobre..." if not agentes else "agentes_autorizados+frase_explicita",
        "web_agentes": agentes,
        "identidad_primaria": "Israel Monta",
        "alucinacion_web": "prohibida_sin_fuente",
    }
