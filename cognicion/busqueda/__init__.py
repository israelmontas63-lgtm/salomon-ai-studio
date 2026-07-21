# -*- coding: utf-8 -*-
"""Agente de búsqueda web de Salomón."""

from cognicion.busqueda.agente import (
    buscar_web,
    estado_circuit_breakers,
    extraer_consulta,
    necesita_busqueda_web,
    responder_con_busqueda,
    resumir_estilo_salomon,
    respuesta_parece_limite_o_vacia,
)

__all__ = [
    "buscar_web",
    "estado_circuit_breakers",
    "extraer_consulta",
    "necesita_busqueda_web",
    "responder_con_busqueda",
    "resumir_estilo_salomon",
    "respuesta_parece_limite_o_vacia",
]
