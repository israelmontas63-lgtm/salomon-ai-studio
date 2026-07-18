# -*- coding: utf-8 -*-
"""LogicEngine — prioriza razonamiento local; bloquea web no canónica."""

from __future__ import annotations

from typing import Any


class LogicEngine:
    _locked = True

    @classmethod
    def lockLocalAgents(cls) -> bool:
        cls._locked = True
        return True

    @classmethod
    def locked(cls) -> bool:
        return cls._locked

    @classmethod
    def permite_web(cls, mensaje: str) -> bool:
        from config.memory_cortex import pedido_busqueda_explicito, web_agentes_autorizados

        if not cls._locked:
            return True
        if pedido_busqueda_explicito(mensaje):
            return True
        # Despliegue neuronal: agentes autorizados + necesidad real de búsqueda
        if web_agentes_autorizados():
            try:
                from cognicion.busqueda.agente import necesita_busqueda_web

                return necesita_busqueda_web(mensaje)
            except Exception:
                return True
        return False

    @classmethod
    def estado(cls) -> dict[str, Any]:
        from config.memory_cortex import web_agentes_autorizados

        return {
            "locked": cls._locked,
            "web_policy": (
                "agentes_autorizados+Busca en la web sobre…"
                if web_agentes_autorizados()
                else "Busca en la web sobre…"
            ),
            "web_agentes": web_agentes_autorizados(),
            "razonamiento_primero": True,
        }
