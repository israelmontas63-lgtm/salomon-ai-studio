# -*- coding: utf-8 -*-
"""
Gestión de errores de grado profesional — captura sin tumbar el flujo.

Uso: envolver operaciones de borde (red, LLM, disco) antes de afectar al chat.
"""

from __future__ import annotations

import traceback
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def seguro(
    fn: Callable[[], T],
    *,
    fallback: T,
    etiqueta: str = "operacion",
) -> tuple[T, dict[str, Any] | None]:
    """Ejecuta fn; ante excepción devuelve fallback + meta de error (nunca raise)."""
    try:
        return fn(), None
    except Exception as exc:
        return fallback, {
            "etiqueta": etiqueta,
            "error": type(exc).__name__,
            "detalle": str(exc)[:240],
            "traceback_tail": traceback.format_exc()[-500:],
        }


def meta_error_api(exc: BaseException, *, codigo: str = "error_interno") -> dict[str, Any]:
    return {
        "ok": False,
        "error": codigo,
        "tipo": type(exc).__name__,
        "detalle": str(exc)[:240],
    }
