# -*- coding: utf-8 -*-
"""
Kernel Python — espejo de /core (cortex · peripherals · memory).
Reexporta mente/ + config/ como una sola fachada.
"""

from __future__ import annotations

from core.cortex.main_controller import MainController
from core.cortex.logic_engine import LogicEngine

__all__ = [
    "MainController",
    "LogicEngine",
    "estado_kernel",
    "conectar_lib",
    "format_error_response",
    "get_error_info",
]


def estado_kernel() -> dict:
    return MainController.estado()


def conectar_lib() -> dict:
    """Atajo kernel → puente lib/ (herramientas, clima, SystemGuard)."""
    from lib import conectar_nucleo

    return conectar_nucleo()


def format_error_response(*args, **kwargs):
    from core.error_codes import format_error_response as _fmt

    return _fmt(*args, **kwargs)


def get_error_info(code):
    from core.error_codes import get_error_info as _info

    return _info(code)