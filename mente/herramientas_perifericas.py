# -*- coding: utf-8 -*-
"""
Herramientas periféricas — ruido encapsulado FUERA del cerebro principal.

Búsqueda web, disparadores de cámara y logs ruidosos NO intervienen
salvo que el cerebro (Memory Cortex / visión) lo autorice.
"""

from __future__ import annotations

from typing import Any


def busqueda_web_si_autorizada(mensaje: str) -> dict[str, Any]:
    """Solo «Busca en la web sobre…». Nunca películas ni auto-wiki."""
    from config.memory_cortex import pedido_busqueda_explicito
    from cognicion.busqueda.agente import necesita_busqueda_web, responder_con_busqueda

    if not pedido_busqueda_explicito(mensaje) or not necesita_busqueda_web(mensaje):
        return {"activo": False, "motivo": "cortex_bloqueado"}
    try:
        pack = responder_con_busqueda(mensaje)
        return {
            "activo": True,
            "texto": (pack.get("texto") or "")[:2200],
            "motor": pack.get("motor"),
            "exito": bool(pack.get("exito")),
        }
    except Exception as exc:
        return {"activo": False, "motivo": type(exc).__name__}


def log_mente(msg: str, *args: Any) -> None:
    """Log mínimo — sin spam al cerebro."""
    try:
        from cognicion.registro import obtener_logger

        obtener_logger("salomon.mente").info(msg, *args)
    except Exception:
        pass


def encapsular_disparo_camara(*, autorizado: bool) -> dict[str, Any]:
    """La cámara no se dispara sola; solo si el flujo de visión lo pide."""
    return {
        "disparar": bool(autorizado),
        "modulo": "herramientas_perifericas",
        "intervencion_cerebro": False,
    }
