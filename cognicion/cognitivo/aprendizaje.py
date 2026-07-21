# -*- coding: utf-8 -*-
"""
Compat shim — ruta legacy `cognicion.cognitivo.aprendizaje`.

Implementación canónica: `cognicion.aprendizaje_ciclo`
(no confundir con `cognicion.aprendizaje` = motor post-turno).
"""

from __future__ import annotations

from cognicion.aprendizaje_ciclo import (  # noqa: F401
    _inferir_causa,
    inferir_causa_raiz,
    registrar_incidente,
)

__all__ = [
    "inferir_causa_raiz",
    "registrar_incidente",
    "_inferir_causa",
]
