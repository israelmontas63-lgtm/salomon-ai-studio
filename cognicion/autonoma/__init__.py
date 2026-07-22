# -*- coding: utf-8 -*-
"""Salomón autónomo — Fase 1 · Estado Vivo · Self-Debug · Metacognición."""

from cognicion.autonoma.auditoria_cruzada import ejecutar_auditoria_cruzada
from cognicion.autonoma.fase1 import ejecutar_fase1, iter_eventos_fase1
from cognicion.autonoma.metacognicion import (
    bloque_sistema_metacognicion,
    es_pregunta_metacognitiva,
    estado_capacidades,
    explicar_fallo_a_israel,
    registrar_y_explicar,
    respuesta_autoconciencia,
)
from cognicion.autonoma.self_debug import (
    ciclo_autodiagnostico,
    estado_self_debug,
    health_motores,
    registrar_fallo,
)

__all__ = [
    "ejecutar_fase1",
    "iter_eventos_fase1",
    "ciclo_autodiagnostico",
    "estado_self_debug",
    "health_motores",
    "registrar_fallo",
    "bloque_sistema_metacognicion",
    "es_pregunta_metacognitiva",
    "estado_capacidades",
    "explicar_fallo_a_israel",
    "registrar_y_explicar",
    "respuesta_autoconciencia",
    "ejecutar_auditoria_cruzada",
]
