# -*- coding: utf-8 -*-
"""
Compat shim — ruta legacy `cognicion.cognitivo.episodica`.

Implementación canónica: `cognicion.episodica`.
"""

from __future__ import annotations

from cognicion.episodica import (  # noqa: F401
    CAPA,
    FRASE_APRENDIZAJE,
    es_correccion_usuario,
    estado_cache_ram,
    guardar_episodio,
    recuperar_lecciones,
)

__all__ = [
    "CAPA",
    "FRASE_APRENDIZAJE",
    "es_correccion_usuario",
    "estado_cache_ram",
    "guardar_episodio",
    "recuperar_lecciones",
]
