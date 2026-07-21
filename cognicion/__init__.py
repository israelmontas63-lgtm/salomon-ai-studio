"""
Cognicion — exports diferidos.

IMPORTANTE (Render): no importar orquestador/vision aqui.
Cualquier import pesado en este archivo obliga a cargar numpy al arrancar.

Rutas cognitivas canónicas (lazy):
  - episodica → cognicion.episodica
  - aprendizaje_ciclo → cognicion.aprendizaje_ciclo
  - aprendizaje → cognicion.aprendizaje (motor post-turno; distinto)
"""

from __future__ import annotations

__all__ = [
    "MotorCognicion",
    "OrquestadorCognitivo",
    "AgenteAutonomo",
    "ResultadoAgente",
    "episodica",
    "aprendizaje_ciclo",
    "aprendizaje",
]


def __getattr__(name: str):
    if name in ("MotorCognicion", "OrquestadorCognitivo"):
        from cognicion.orquestador import MotorCognicion, OrquestadorCognitivo

        return MotorCognicion if name == "MotorCognicion" else OrquestadorCognitivo
    if name in ("AgenteAutonomo", "ResultadoAgente"):
        from cognicion.agente import AgenteAutonomo, ResultadoAgente

        return AgenteAutonomo if name == "AgenteAutonomo" else ResultadoAgente
    if name == "episodica":
        import cognicion.episodica as _m

        return _m
    if name == "aprendizaje_ciclo":
        import cognicion.aprendizaje_ciclo as _m

        return _m
    if name == "aprendizaje":
        import cognicion.aprendizaje as _m

        return _m
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
