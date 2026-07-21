# -*- coding: utf-8 -*-
"""
Memory Cortex (compat) — delega a config/memory_cortex.py

Web: frase canónica o agente con SBI (ver autoriza_web).
"""

from __future__ import annotations

from config.memory_cortex import (  # noqa: F401
    autoriza_web,
    es_saludo_o_charla_simple,
    pedido_busqueda_explicito,
)

__all__ = [
    "autoriza_web",
    "pedido_busqueda_explicito",
    "es_saludo_o_charla_simple",
]
