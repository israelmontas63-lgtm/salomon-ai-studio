"""
Contexto de petición — thread-safe para capas modulares (api_key, sesión).
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

_ctx: ContextVar["ContextoPeticion | None"] = ContextVar("capas_ctx", default=None)


@dataclass
class ContextoPeticion:
    api_key: str | None = None
    session_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def como_dict(self) -> dict[str, Any]:
        return {
            "api_key": self.api_key,
            "session_id": self.session_id,
            **self.extra,
        }


def establecer_contexto(
    *,
    api_key: str | None = None,
    session_id: str | None = None,
    **extra: Any,
) -> ContextoPeticion:
    ctx = ContextoPeticion(api_key=api_key, session_id=session_id, extra=extra)
    _ctx.set(ctx)
    return ctx


def obtener_contexto() -> ContextoPeticion:
    ctx = _ctx.get()
    if ctx is None:
        return ContextoPeticion()
    return ctx


def limpiar_contexto() -> None:
    _ctx.set(None)
