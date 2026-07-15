"""
Cola de tareas en segundo plano — aprendizaje post-turno sin bloquear respuesta.
"""

from __future__ import annotations

import atexit
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from cognicion.registro import evento, obtener_logger

_executor: ThreadPoolExecutor | None = None
_pendientes = 0
_cond = threading.Condition()
_log = obtener_logger("cola")


def _obtener_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="salomon-cola")
    return _executor


def encolar(func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    """Ejecuta func en un hilo de fondo."""
    global _pendientes

    def _tarea() -> None:
        global _pendientes
        try:
            func(*args, **kwargs)
        except Exception:
            _log.exception("tarea_fallida accion=%s", getattr(func, "__name__", "anon"))
        finally:
            with _cond:
                _pendientes -= 1
                _cond.notify_all()

    with _cond:
        _pendientes += 1
    _obtener_executor().submit(_tarea)


def encolar_aprendizaje(
    callback: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> None:
    """Encola aprendizaje post-turno y registra el resultado."""

    def _ejecutar() -> None:
        resultado = callback(*args, **kwargs)
        evento(
            _log,
            "aprendizaje_completado",
            procesado=getattr(resultado, "procesado", None),
            recuerdos=len(getattr(resultado, "recuerdos", []) or []),
        )

    encolar(_ejecutar)


def pendientes() -> int:
    with _cond:
        return _pendientes


def esperar_vacio(timeout: float = 5.0) -> bool:
    """Espera a que la cola quede vacía (útil en tests)."""
    with _cond:
        return _cond.wait_for(lambda: _pendientes == 0, timeout=timeout)


def cerrar_cola() -> None:
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=False, cancel_futures=True)
        _executor = None


atexit.register(cerrar_cola)
