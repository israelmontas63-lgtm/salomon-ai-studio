"""
Plugin externo function-calling — delega al integrador interno.
Permite desactivar/reemplazar la capa desde plugins/ sin tocar el núcleo.
"""

from __future__ import annotations

from typing import Any


def activar(app: Any = None) -> bool:
    from cognicion.capas.function_calling.integrador import activar as activar_integrador

    return activar_integrador(app)
