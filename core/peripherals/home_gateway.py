# -*- coding: utf-8 -*-
"""HomeGateway — rutas canónicas del núcleo."""

from __future__ import annotations


class HomeGateway:
    RUTAS = {
        "chat": "/api/chat",
        "nuevo": "/api/chat/nuevo",
        "mente": "/api/mente/conexion",
        "kernel": "/api/core/kernel",
        "tts": "/api/tts",
    }
