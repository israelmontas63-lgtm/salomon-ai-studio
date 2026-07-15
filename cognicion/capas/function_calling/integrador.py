"""
Integrador del plugin function-calling — registra pipeline y rutas sin tocar el núcleo.
"""

from __future__ import annotations

from typing import Any

from settings import FUNCTION_CALLING_HABILITADO

from cognicion.capas.pipeline import ResultadoPipeline, registrar_manejador
from cognicion.capas.function_calling.puente import chat_con_herramientas
from cognicion.capas.contexto import obtener_contexto
from cognicion.registro import evento, obtener_logger

_log = obtener_logger("fc.integrador")
_activo = False


def _manejador_fc(
    mensaje: str,
    historial: list[dict],
    system_instruction: str,
    *,
    model_name: str | None = None,
    contexto: dict[str, Any] | None = None,
) -> ResultadoPipeline | None:
    ctx = obtener_contexto()
    fc = chat_con_herramientas(
        mensaje,
        historial,
        system_instruction,
        model_name=model_name,
        contexto_extra=ctx.como_dict(),
    )
    if not fc.usado or not fc.texto:
        return None
    return ResultadoPipeline(
        texto=fc.texto,
        metadata={"function_calling": fc.metadata},
        capa="function_calling",
    )


def activar(app: Any = None) -> bool:
    """Activa el plugin: registra manejador en pipeline y monta rutas."""
    global _activo
    if _activo:
        return True
    if not FUNCTION_CALLING_HABILITADO:
        evento(_log, "fc_desactivado", motivo="FUNCTION_CALLING_HABILITADO=false")
        return False

    registrar_manejador("function_calling", _manejador_fc)

    if app is not None:
        from cognicion.capas.function_calling.rutas import router

        app.include_router(router)

    _activo = True
    evento(_log, "fc_plugin_activado")
    return True


def esta_activo() -> bool:
    return _activo
