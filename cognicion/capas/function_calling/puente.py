"""
Puente LLM ↔ herramientas — loop de function-calling (OpenAI/Groq).
Capa independiente; no modifica cognicion/llm.py.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from settings import (
    FUNCTION_CALLING_MAX_ITER,
    GROQ_API_KEY,
    GROQ_MODEL,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)

from cognicion.capas.function_calling.detector import debe_usar_function_calling
from cognicion.capas.function_calling.ejecutor import ejecutar_llamada, resultado_para_llm
from cognicion.capas.function_calling.schemas import construir_esquemas_openai
from cognicion.registro import evento, obtener_logger

_log = obtener_logger("fc.puente")


@dataclass
class ResultadoFunctionCalling:
    usado: bool
    texto: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def _proveedor_disponible() -> str | None:
    if OPENAI_API_KEY:
        return "openai"
    if GROQ_API_KEY:
        return "groq"
    return None


def _cliente_openai():
    from openai import OpenAI

    if OPENAI_API_KEY:
        kwargs: dict[str, str] = {"api_key": OPENAI_API_KEY}
        if OPENAI_BASE_URL:
            kwargs["base_url"] = OPENAI_BASE_URL
        return OpenAI(**kwargs), OPENAI_MODEL
    if GROQ_API_KEY:
        return OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1"), GROQ_MODEL
    raise RuntimeError("Sin proveedor compatible con function-calling")


def _historial_a_mensajes(
    historial: list[dict],
    mensaje: str,
    system_instruction: str,
) -> list[dict[str, Any]]:
    mensajes: list[dict[str, Any]] = [{"role": "system", "content": system_instruction}]
    for item in historial:
        rol = "user" if item.get("role") == "user" else "assistant"
        parts = item.get("parts") or []
        if parts:
            mensajes.append({"role": rol, "content": str(parts[0])})
    mensajes.append({"role": "user", "content": mensaje})
    return mensajes


def _extraer_tool_calls(message: Any) -> list[Any]:
    calls = getattr(message, "tool_calls", None)
    return list(calls) if calls else []


def chat_con_herramientas(
    mensaje: str,
    historial: list[dict],
    system_instruction: str,
    *,
    model_name: str | None = None,
    contexto_extra: dict[str, Any] | None = None,
) -> ResultadoFunctionCalling:
    """
    Intenta responder usando function-calling.
    Si no aplica o falla, devuelve usado=False para fallback al chat normal.
    """
    activar, sugeridas = debe_usar_function_calling(mensaje)
    if not activar:
        return ResultadoFunctionCalling(usado=False)

    proveedor = _proveedor_disponible()
    if not proveedor:
        return ResultadoFunctionCalling(usado=False, metadata={"motivo": "sin_proveedor_fc"})

    tools = construir_esquemas_openai()
    if not tools:
        return ResultadoFunctionCalling(usado=False, metadata={"motivo": "sin_herramientas"})

    instruccion = system_instruction + (
        "\n\nTienes herramientas disponibles. Úsalas cuando el usuario pida "
        "corregir, traducir, resumir, analíticas, ayuda, planes, seguridad, "
        "optimizar, solar o exportar backup. Responde en español tras usarlas."
    )

    try:
        client, modelo_defecto = _cliente_openai()
        modelo = model_name or modelo_defecto
        mensajes = _historial_a_mensajes(historial, mensaje, instruccion)
        herramientas_usadas: list[dict[str, Any]] = []

        for iteracion in range(FUNCTION_CALLING_MAX_ITER):
            respuesta = client.chat.completions.create(
                model=modelo,
                messages=mensajes,
                tools=tools,
                tool_choice="auto",
            )
            choice = respuesta.choices[0]
            msg = choice.message

            tool_calls = _extraer_tool_calls(msg)
            if not tool_calls:
                texto = (msg.content or "").strip()
                if texto:
                    return ResultadoFunctionCalling(
                        usado=True,
                        texto=texto,
                        metadata={
                            "proveedor": proveedor,
                            "modelo": modelo,
                            "iteraciones": iteracion + 1,
                            "herramientas_usadas": herramientas_usadas,
                            "sugeridas": sugeridas,
                        },
                    )
                break

            mensajes.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            })

            for tc in tool_calls:
                nombre = tc.function.name
                ejecucion = ejecutar_llamada(nombre, tc.function.arguments)
                herramientas_usadas.append({
                    "id": nombre,
                    "exito": ejecucion.exito,
                })
                mensajes.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": resultado_para_llm(ejecucion),
                })

            evento(_log, "fc_iteracion", iteracion=iteracion + 1, tools=len(tool_calls))

        return ResultadoFunctionCalling(
            usado=False,
            metadata={"motivo": "sin_respuesta_final", "herramientas_usadas": herramientas_usadas},
        )

    except Exception as exc:
        evento(_log, "fc_error", error=type(exc).__name__)
        return ResultadoFunctionCalling(
            usado=False,
            metadata={"motivo": "error", "error": type(exc).__name__},
        )


def estado_capa() -> dict[str, Any]:
    from settings import FUNCTION_CALLING_HABILITADO, FUNCTION_CALLING_SIEMPRE

    return {
        "capa": "function_calling",
        "habilitado": FUNCTION_CALLING_HABILITADO,
        "siempre": FUNCTION_CALLING_SIEMPRE,
        "proveedor": _proveedor_disponible(),
        "herramientas": len(construir_esquemas_openai()),
        "max_iteraciones": FUNCTION_CALLING_MAX_ITER,
    }
