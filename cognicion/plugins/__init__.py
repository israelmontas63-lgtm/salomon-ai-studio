"""Sistema de plugins de Salomón — Level 9 Plug-and-Play."""

from cognicion.plugins.cargador import (
    PLUGINS_DIR,
    activar_plugin,
    desactivar_plugin,
    descubrir_plugins,
    estado_level9,
    hot_plug,
)

__all__ = [
    "PLUGINS_DIR",
    "activar_plugin",
    "desactivar_plugin",
    "descubrir_plugins",
    "estado_level9",
    "hot_plug",
]
