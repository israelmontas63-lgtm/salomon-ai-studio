# -*- coding: utf-8 -*-
"""
Capas adicionales del OS — extensiones sin modificar el núcleo.

API pública: contexto (ContextVar), loader Level-9, pipeline de respuesta.
"""

from __future__ import annotations

from cognicion.capas.contexto import (
    ContextoPeticion,
    contexto_activo,
    establecer_contexto,
    limpiar_contexto,
    obtener_contexto,
)
from cognicion.capas.loader import estado_capas, inicializar_capas
from cognicion.capas.pipeline import (
    ManejadorRespuesta,
    ResultadoPipeline,
    desregistrar_manejador,
    generar_respuesta,
    listar_manejadores,
    registrar_manejador,
)

__all__ = [
    "ContextoPeticion",
    "ManejadorRespuesta",
    "ResultadoPipeline",
    "contexto_activo",
    "desregistrar_manejador",
    "establecer_contexto",
    "estado_capas",
    "generar_respuesta",
    "inicializar_capas",
    "limpiar_contexto",
    "listar_manejadores",
    "obtener_contexto",
    "registrar_manejador",
]
