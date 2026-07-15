"""
Ejecutor seguro — invoca herramientas del registry vía sandbox existente.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import herramientas
from cognicion.capas.function_calling.schemas import herramientas_permitidas
from cognicion.registro import evento, obtener_logger

_log = obtener_logger("fc.ejecutor")


@dataclass
class ResultadoEjecucion:
    herramienta_id: str
    exito: bool
    resultado: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


def ejecutar_llamada(nombre: str, argumentos: str | dict[str, Any]) -> ResultadoEjecucion:
    """Ejecuta una tool call del LLM de forma segura."""
    if nombre not in herramientas_permitidas():
        return ResultadoEjecucion(
            herramienta_id=nombre,
            exito=False,
            error=f"Herramienta no permitida para LLM: {nombre}",
        )

    if isinstance(argumentos, str):
        try:
            args = json.loads(argumentos) if argumentos.strip() else {}
        except json.JSONDecodeError:
            return ResultadoEjecucion(
                herramienta_id=nombre,
                exito=False,
                error="Argumentos JSON inválidos",
            )
    else:
        args = argumentos

    if not isinstance(args, dict):
        args = {}

    evento(_log, "ejecutar_herramienta", id=nombre, args=list(args.keys()))
    resultado = herramientas.ejecutar_herramienta(nombre, **args)
    exito = bool(resultado.get("exito", True)) and "error" not in resultado

    return ResultadoEjecucion(
        herramienta_id=nombre,
        exito=exito,
        resultado=resultado,
        error=resultado.get("error"),
    )


def resultado_para_llm(ejecucion: ResultadoEjecucion) -> str:
    """Serializa resultado para el siguiente turno del LLM."""
    payload = {
        "herramienta": ejecucion.herramienta_id,
        "exito": ejecucion.exito,
        "datos": ejecucion.resultado,
    }
    if ejecucion.error:
        payload["error"] = ejecucion.error
    return json.dumps(payload, ensure_ascii=False, default=str)
