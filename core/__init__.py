# -*- coding: utf-8 -*-
"""
Kernel Python — espejo de /core (cortex · peripherals · memory).
Reexporta mente/ + config/ como una sola fachada.
"""

from __future__ import annotations

from core.cortex.main_controller import MainController
from core.cortex.logic_engine import LogicEngine

__all__ = ["MainController", "LogicEngine", "estado_kernel"]


def estado_kernel() -> dict:
    return MainController.estado()
