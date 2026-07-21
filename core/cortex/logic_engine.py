# -*- coding: utf-8 -*-
"""LogicEngine — prioriza razonamiento local; web solo vía Memory Cortex."""

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
    def permite_web(cls, mensaje: str, *, origen: str = "usuario") -> bool:
        """
        Gate absoluto: config.memory_cortex.autoriza_web.
        Nunca abre web por desbloqueo interno ni por heurística factual.
        """
        from config.memory_cortex import autoriza_web

        # Incluso si _locked=False, el cortex manda (soberanía del núcleo).
        return bool(autoriza_web(mensaje or "", origen=origen))

    @classmethod
    def estado(cls) -> dict[str, Any]:
        from config.memory_cortex import cortex_status, web_agentes_autorizados

        c = cortex_status()
        return {
            "locked": cls._locked,
            "web_policy": "autoriza_web+frase_canonica",
            "web_agentes": web_agentes_autorizados(),
            "busqueda_web_auto": c.get("busqueda_web_auto"),
            "razonamiento_primero": True,
            "master_neural": True,
            "cortex_gate": c.get("gate"),
            "politica": c.get("politica"),
        }
