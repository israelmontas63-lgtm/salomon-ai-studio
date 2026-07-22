"""Orquestación multi-agente de Salomón (Colsub on-demand + Smart Router)."""

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
from cognicion.orquesta.smart_router import (
    estado_smart_router,
    generar_imagen_con_failover,
    generar_video_con_failover,
    hablar_con_failover,
    razonar_con_failover,
)

__all__ = [
    "desplegar_agentes_paralelos",
    "necesita_orquesta",
    "sintetizar_orquesta",
    "colsub_desplegar",
    "puntuacion_complejidad",
    "recursos_criticos",
    "estado_smart_router",
    "generar_imagen_con_failover",
    "generar_video_con_failover",
    "hablar_con_failover",
    "razonar_con_failover",
]
