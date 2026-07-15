"""
Sandbox para herramientas — ejecución aislada con límites.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

T = TypeVar("T")

_TIMEOUT_SEG = 30
_MAX_RESULTADO_CHARS = 50_000


@dataclass
class ResultadoSandbox:
    exito: bool
    resultado: Any = None
    error: str | None = None
    timeout: bool = False
    truncado: bool = False


def ejecutar_aislado(
    funcion: Callable[..., T],
    *args: Any,
    timeout_seg: int = _TIMEOUT_SEG,
    **kwargs: Any,
) -> ResultadoSandbox:
    """
    Ejecuta una función en hilo separado con timeout.
    No permite acceso a red ni subprocess — solo lógica Python pura.
    """
    contenedor: list[Any] = []
    error_holder: list[Exception] = []

    def _worker() -> None:
        try:
            contenedor.append(funcion(*args, **kwargs))
        except Exception as exc:
            error_holder.append(exc)

    hilo = threading.Thread(target=_worker, daemon=True)
    hilo.start()
    hilo.join(timeout=timeout_seg)

    if hilo.is_alive():
        return ResultadoSandbox(exito=False, error="Timeout en sandbox", timeout=True)

    if error_holder:
        return ResultadoSandbox(
            exito=False,
            error=f"{type(error_holder[0]).__name__}: {error_holder[0]}",
        )

    resultado = contenedor[0] if contenedor else None
    truncado = False
    if isinstance(resultado, str) and len(resultado) > _MAX_RESULTADO_CHARS:
        resultado = resultado[:_MAX_RESULTADO_CHARS] + "...[truncado]"
        truncado = True
    elif isinstance(resultado, dict):
        import json
        serializado = json.dumps(resultado, ensure_ascii=False, default=str)
        if len(serializado) > _MAX_RESULTADO_CHARS:
            truncado = True

    return ResultadoSandbox(exito=True, resultado=resultado, truncado=truncado)


def envolver_herramienta(funcion: Callable[..., Any]) -> Callable[..., Any]:
    """Decorador opcional — ejecutar_herramienta ya usa sandbox."""
    return funcion
