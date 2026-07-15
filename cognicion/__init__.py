"""
Módulo de cognición avanzada de Salomón AI.

Pilares:
- memoria: RAG vectorial con ChromaDB
- razonamiento: Chain of Thought para tareas técnicas
- vision: análisis de capturas con Gemini
- autocorreccion: ciclo proactivo ante errores de consola
- agente: correcciones autónomas en archivos del proyecto
"""

from cognicion.agente import AgenteAutonomo, ResultadoAgente
from cognicion.orquestador import MotorCognicion, OrquestadorCognitivo

__all__ = [
    "MotorCognicion",
    "OrquestadorCognitivo",
    "AgenteAutonomo",
    "ResultadoAgente",
]
