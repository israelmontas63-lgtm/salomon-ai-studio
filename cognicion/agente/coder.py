# -*- coding: utf-8 -*-
"""
Agent_Coder — lógica Python / JS exclusiva (parche seguro + motor de código).
Lazy: no carga el autónomo hasta la primera petición.
"""

from __future__ import annotations

from typing import Any

_autonomo = None


def _obtener_autonomo():
    global _autonomo
    if _autonomo is None:
        from cognicion.agente.autonomo import AgenteAutonomo

        _autonomo = AgenteAutonomo()
    return _autonomo


def ejecutar_coder(
    tarea: str,
    *,
    error_consola: str | None = None,
    solo_razonamiento: bool = False,
) -> dict[str, Any]:
    """
    Agent_Coder: corrige/genera lógica. Delega a AgenteAutonomo + UCE.
    No toca visión ni CameraEngine.
    """
    from cognicion.agente.guard import autorizar_escritura, liberar_memoria_suave

    # Guard previo: cualquier mención a camera-engine queda bloqueada
    lower = (tarea or "").lower()
    if "camera-engine" in lower or "studio/dist/camera" in lower:
        return {
            "exito": False,
            "agente": "Agent_Coder",
            "error": "bloqueado_por_Agent_Guard_golden_camera",
            "guard": autorizar_escritura("studio/dist/camera-engine.js", autorizado=False),
        }

    if solo_razonamiento:
        from cognicion.codigo.motor_universal import bloque_motor_codigo

        uce = bloque_motor_codigo(tarea)
        liberar_memoria_suave()
        return {
            "exito": True,
            "agente": "Agent_Coder",
            "modo": "razonamiento",
            "universal_code_engine": uce.to_dict(),
            "contexto": uce.bloque_contexto,
        }

    agente = _obtener_autonomo()
    resultado = agente.corregir(tarea, error=error_consola)
    liberar_memoria_suave()
    return {
        "exito": bool(getattr(resultado, "exito", False) or getattr(resultado, "ejecutado", False)),
        "agente": "Agent_Coder",
        "modo": "parche",
        "resultado": resultado.to_dict() if hasattr(resultado, "to_dict") else str(resultado),
    }
