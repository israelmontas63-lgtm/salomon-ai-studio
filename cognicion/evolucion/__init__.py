# -*- coding: utf-8 -*-
"""
Evolución Salomón — reexporta SCE (v102) y contrato 30-X.

Implementación canónica: `cognicion.evolucion.sce`
Catálogo: `cognicion.evolucion.habilidades_30x`
"""

from __future__ import annotations

from cognicion.evolucion.sce import (
    LEDGER_EVOL,
    MSG_ACEPTADA,
    MSG_ACEPTADA_LEGACY,
    MSG_RECHAZADA,
    SCE_VERSION,
    ROOT,
    analizar_valor,
    bloque_contexto_sce,
    es_propuesta_evolucion,
    estado_sce,
    estado_sistema_inmune,
)

__all__ = [
    "LEDGER_EVOL",
    "MSG_ACEPTADA",
    "MSG_ACEPTADA_LEGACY",
    "MSG_RECHAZADA",
    "ROOT",
    "SCE_VERSION",
    "analizar_valor",
    "bloque_contexto_sce",
    "es_propuesta_evolucion",
    "estado_sce",
    "estado_sistema_inmune",
]
