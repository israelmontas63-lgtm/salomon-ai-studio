# -*- coding: utf-8 -*-
"""
Memory Cortex (compat) — delega a config/memory_cortex.py

Web SOLO con: «Busca en la web sobre…»
"""

from __future__ import annotations

from config.memory_cortex import (  # noqa: F401
    es_saludo_o_charla_simple,
    pedido_busqueda_explicito,
)

__all__ = ["pedido_busqueda_explicito", "es_saludo_o_charla_simple"]
