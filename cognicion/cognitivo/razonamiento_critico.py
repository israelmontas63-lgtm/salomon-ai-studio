# -*- coding: utf-8 -*-
"""
Razonamiento Crítico — ¿Es correcto? ¿Qué aprendí del error anterior?
"""

from __future__ import annotations

from typing import Any

from cognicion.razonamiento.cadena import pensamiento_critico_viable


def evaluar_pre_tarea(
    mensaje: str,
    *,
    lecciones_previas: list[str] | None = None,
) -> dict[str, Any]:
    """
    Antes de ejecutar: viabilidad + lecciones episódicas.
    """
    viable = pensamiento_critico_viable(mensaje)
    lecciones = [x for x in (lecciones_previas or []) if x.strip()][:5]

    preguntas = [
        "¿Es esto correcto y seguro para el núcleo?",
        "¿Qué aprendí de mi error anterior?",
        "¿Cuál es la vía más directa para Israel?",
    ]
    correccion_proceso = None
    if not viable.get("viable"):
        correccion_proceso = (
            "Proceso ajustado: rechazar operación de riesgo y proponer alternativa segura."
        )
    elif lecciones:
        correccion_proceso = (
            "Proceso ajustado con lecciones previas: "
            + " | ".join(lecciones[:2])
        )

    return {
        "ok": True,
        "viable": bool(viable.get("viable")),
        "riesgos": viable.get("riesgos"),
        "alcance": viable.get("alcance"),
        "preguntas_internas": preguntas,
        "lecciones_aplicadas": lecciones,
        "correccion_proceso": correccion_proceso,
        "listo_para_ejecutar": bool(viable.get("viable")),
    }
