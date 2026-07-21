# -*- coding: utf-8 -*-
"""
Contexto de petición — ContextVar thread-safe y async-safe (Flask/FastAPI).

Aislamiento estricto: cada petición tiene su propio ContextoPeticion inmutable.
`limpiar_contexto` usa Token.reset para evitar fugas de session_id / api_key
entre workers concurrentes.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

_ctx: ContextVar[ContextoPeticion | None] = ContextVar("salomon_capas_ctx", default=None)
_ctx_token: ContextVar[Token[ContextoPeticion | None] | None] = ContextVar(
    "salomon_capas_ctx_token", default=None
)


@dataclass(frozen=True, slots=True)
class ContextoPeticion:
    """Snapshot inmutable por petición — sin mutación cruzada entre hilos."""

    api_key: str | None = None
    session_id: str | None = None
    request_id: str | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def como_dict(self, *, incluir_secretos: bool = True) -> dict[str, Any]:
        """Dict para plugins. Por defecto incluye api_key (FC / permisos)."""
        out: dict[str, Any] = {
            "session_id": self.session_id,
            "request_id": self.request_id,
        }
        if self.extra:
            out.update(dict(self.extra))
        if incluir_secretos:
            out["api_key"] = self.api_key
        elif self.api_key:
            out["api_key_presente"] = True
        return out

    def como_dict_publico(self) -> dict[str, Any]:
        """Sin secretos — apto para logs / metadata de respuesta."""
        return self.como_dict(incluir_secretos=False)


def establecer_contexto(
    *,
    api_key: str | None = None,
    session_id: str | None = None,
    request_id: str | None = None,
    **extra: Any,
) -> ContextoPeticion:
    """
    Fija el contexto de la petición actual (ContextVar).
    Reemplaza cualquier contexto previo de este task/hilo de forma segura.
    """
    # Limpiar token anterior en el mismo task (evita Token reuse warnings)
    prev = _ctx_token.get()
    if prev is not None:
        try:
            _ctx.reset(prev)
        except (ValueError, LookupError, RuntimeError):
            pass
        _ctx_token.set(None)

    safe_extra = MappingProxyType(dict(extra)) if extra else MappingProxyType({})
    ctx = ContextoPeticion(
        api_key=(api_key.strip() if isinstance(api_key, str) and api_key.strip() else None),
        session_id=(
            session_id.strip()
            if isinstance(session_id, str) and session_id.strip()
            else None
        ),
        request_id=(
            request_id.strip()
            if isinstance(request_id, str) and request_id.strip()
            else None
        ),
        extra=safe_extra,
    )
    token = _ctx.set(ctx)
    _ctx_token.set(token)
    return ctx


def obtener_contexto() -> ContextoPeticion:
    """Contexto actual o vacío aislado (nunca comparte estado mutable)."""
    ctx = _ctx.get()
    if ctx is None:
        return ContextoPeticion()
    return ctx


def limpiar_contexto() -> None:
    """
    Restaura el ContextVar al estado previo vía Token.reset.
    Obligatoria en finally de middleware — previene fugas entre peticiones.
    """
    token = _ctx_token.get()
    if token is not None:
        try:
            _ctx.reset(token)
        except (ValueError, LookupError, RuntimeError):
            try:
                _ctx.set(None)
            except Exception:
                pass
        _ctx_token.set(None)
    else:
        try:
            _ctx.set(None)
        except Exception:
            pass


def contexto_activo() -> bool:
    return _ctx.get() is not None
