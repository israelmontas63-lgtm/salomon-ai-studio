"""Orquestación multi-agente de Salomón (Colsub on-demand)."""

from cognicion.orquesta.agentes_paralelos import (
    desplegar_agentes_paralelos,
    necesita_orquesta,
    sintetizar_orquesta,
)
from cognicion.orquesta.colsub import (
    colsub_desplegar,
    puntuacion_complejidad,
    recursos_criticos,
)

__all__ = [
    "desplegar_agentes_paralelos",
    "necesita_orquesta",
    "sintetizar_orquesta",
    "colsub_desplegar",
    "puntuacion_complejidad",
    "recursos_criticos",
]
