# -*- coding: utf-8 -*-
"""
Puente directo al núcleo de Salomón — sin middleware de cámara/menús.
"""

from core.brain_connector.bridge import send_visual_to_core, bridge_status

__all__ = ["send_visual_to_core", "bridge_status"]
