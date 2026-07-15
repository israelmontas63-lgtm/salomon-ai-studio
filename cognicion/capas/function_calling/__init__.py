"""Capa de function-calling — puente seguro LLM ↔ herramientas."""

from cognicion.capas.function_calling.detector import debe_usar_function_calling
from cognicion.capas.function_calling.puente import (
    ResultadoFunctionCalling,
    chat_con_herramientas,
    estado_capa,
)
from cognicion.capas.function_calling.schemas import construir_esquemas_openai, listar_para_api

__all__ = [
    "ResultadoFunctionCalling",
    "chat_con_herramientas",
    "construir_esquemas_openai",
    "debe_usar_function_calling",
    "estado_capa",
    "listar_para_api",
]
