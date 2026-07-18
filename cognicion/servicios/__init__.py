# -*- coding: utf-8 -*-
"""Servicios externos — ServiceManager (única ruta neuronal)."""

from cognicion.servicios.manager import ServiceManager, obtener_manager, obtener_registry
from cognicion.servicios.registry import ServiceRegistry, boot_proveedores

__all__ = [
    "ServiceManager",
    "ServiceRegistry",
    "obtener_manager",
    "obtener_registry",
    "boot_proveedores",
]
