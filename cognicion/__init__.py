"""
Cognicion — exports diferidos.

IMPORTANTE (Render): no importar orquestador/vision aqui.
Cualquier import pesado en este archivo obliga a cargar numpy al arrancar.
"""

from __future__ import annotations

__all__ = [
    "MotorCognicion",
    "OrquestadorCognitivo",
    "AgenteAutonomo",
    "ResultadoAgente",
]


def __getattr__(name: str):
    if name in ("MotorCognicion", "OrquestadorCognitivo"):
        from cognicion.orquestador import MotorCognicion, OrquestadorCognitivo

        return MotorCognicion if name == "MotorCognicion" else OrquestadorCognitivo
    if name in ("AgenteAutonomo", "ResultadoAgente"):
        from cognicion.agente import AgenteAutonomo, ResultadoAgente

        return AgenteAutonomo if name == "AgenteAutonomo" else ResultadoAgente
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
