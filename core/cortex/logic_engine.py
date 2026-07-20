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
        from config.memory_cortex import pedido_busqueda_explicito

        if not cls._locked:
            return True
        if pedido_busqueda_explicito(mensaje):
            return True
        # Motor neuronal maestro: vacíos factuales → enjambre autónomo
        try:
            from cognicion.core_salomon_master_neural_engine import obtener_master_neural

            return obtener_master_neural().should_search_web(mensaje)
        except Exception:
            try:
                from config.memory_cortex import web_agentes_autorizados
                from cognicion.busqueda.agente import necesita_busqueda_web

                if web_agentes_autorizados():
                    return necesita_busqueda_web(mensaje)
            except Exception:
                pass
            return False

    @classmethod
    def estado(cls) -> dict[str, Any]:
        from config.memory_cortex import web_agentes_autorizados

        return {
            "locked": cls._locked,
            "web_policy": "master_neural_auto_swarm+Busca en la web sobre…",
            "web_agentes": web_agentes_autorizados(),
            "razonamiento_primero": True,
            "master_neural": True,
        }
