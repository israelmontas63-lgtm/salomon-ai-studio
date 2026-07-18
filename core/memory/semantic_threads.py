# -*- coding: utf-8 -*-
"""SemanticThreads — alias de mente.hilos."""

from __future__ import annotations

from mente.hilos import clasificar_area, contexto_hilo, cargar_hilo


class SemanticThreads:
    contexto = staticmethod(contexto_hilo)
    clasificar = staticmethod(clasificar_area)
    cargar = staticmethod(cargar_hilo)
