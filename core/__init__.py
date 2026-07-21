# -*- coding: utf-8 -*-
"""
Kernel Python — espejo de /core (cortex · peripherals · memory).
Reexporta mente/ + config/ como una sola fachada.
"""

from __future__ import annotations

from core.cortex.main_controller import MainController
from core.cortex.logic_engine import LogicEngine

__all__ = ["MainController", "LogicEngine", "estado_kernel", "conectar_lib"]


def estado_kernel() -> dict:
    return MainController.estado()


def conectar_lib() -> dict:
    """Atajo kernel → puente lib/ (herramientas, clima, SystemGuard)."""
    from lib import conectar_nucleo

    return conectar_nucleo()
