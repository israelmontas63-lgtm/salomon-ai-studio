"""
Capas de memoria — tipos estandarizados sobre ChromaDB y SQLite.
"""

from __future__ import annotations

from enum import Enum


class TipoMemoria(str, Enum):
    """Capas de memoria del sistema."""

    INMEDIATA = "inmediata"
    TEMPORAL = "temporal"
    PERMANENTE = "permanente"
    PROYECTO = "proyecto"
    PREFERENCIAS = "preferencias"
    CONTEXTO = "contexto"
    APRENDIZAJE = "aprendizaje"
    EPISODICA = "episodica"


CAPAS_RAG: tuple[TipoMemoria, ...] = (
    TipoMemoria.PREFERENCIAS,
    TipoMemoria.APRENDIZAJE,
    TipoMemoria.EPISODICA,
    TipoMemoria.PERMANENTE,
    TipoMemoria.PROYECTO,
    TipoMemoria.CONTEXTO,
    TipoMemoria.TEMPORAL,
)
