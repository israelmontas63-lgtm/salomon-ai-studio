# -*- coding: utf-8 -*-
"""Cognitive Core & Coding Engine — superficie pública."""

from cognicion.codigo.guardrails import InformeGuardrails, analizar_respuesta_codigo
from cognicion.codigo.motor_universal import (
    ResultadoMotorCodigo,
    bloque_motor_codigo,
    requiere_motor_codigo,
)

__all__ = [
    "InformeGuardrails",
    "ResultadoMotorCodigo",
    "analizar_respuesta_codigo",
    "bloque_motor_codigo",
    "requiere_motor_codigo",
]
