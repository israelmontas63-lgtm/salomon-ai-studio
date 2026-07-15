"""
Pipeline de respuesta — punto de extensión para capas (function-calling, etc.).
El núcleo solo llama aquí; los plugins registran manejadores.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from cognicion.llm import chat_con_historial


@dataclass
class ResultadoPipeline:
    texto: str
    metadata: dict[str, Any] = field(default_factory=dict)
    capa: str = "llm"


class ManejadorRespuesta(Protocol):
    def __call__(
        self,
        mensaje: str,
        historial: list[dict],
        system_instruction: str,
        *,
        model_name: str | None = None,
        contexto: dict[str, Any] | None = None,
    ) -> ResultadoPipeline | None: ...


_manejadores: list[tuple[str, ManejadorRespuesta]] = []


def registrar_manejador(nombre: str, manejador: ManejadorRespuesta) -> None:
    _manejadores.append((nombre, manejador))


def listar_manejadores() -> list[str]:
    return [nombre for nombre, _ in _manejadores]


def generar_respuesta(
    mensaje: str,
    historial: list[dict],
    system_instruction: str,
    *,
    model_name: str | None = None,
    contexto: dict[str, Any] | None = None,
) -> ResultadoPipeline:
    """Intenta manejadores registrados por plugins; fallback al LLM estándar."""
    ctx = contexto or {}
    for nombre, manejador in _manejadores:
        try:
            resultado = manejador(
                mensaje,
                historial,
                system_instruction,
                model_name=model_name,
                contexto=ctx,
            )
            if resultado is not None and resultado.texto:
                resultado.metadata.setdefault("capa", nombre)
                return resultado
        except Exception as exc:
            ctx.setdefault("errores_capas", []).append({nombre: type(exc).__name__})

    texto = chat_con_historial(
        mensaje,
        historial,
        system_instruction,
        model_name=model_name,
    )
    return ResultadoPipeline(texto=texto, capa="llm", metadata={"fallback": True})
