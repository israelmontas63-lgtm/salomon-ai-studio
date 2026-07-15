"""
Cargador de capas — activa plugins del sistema vía plugins/.
"""

from __future__ import annotations

from typing import Any

from cognicion.plugins.cargador import activar_plugin, descubrir_plugins
from cognicion.registro import evento, obtener_logger

_log = obtener_logger("capas.loader")
_inicializado = False


def inicializar_capas(app: Any = None) -> dict[str, bool]:
    """
    Activa plugins en plugins/ (incluye function_calling).
    Único punto de montaje — app.py solo invoca esto en startup.
    """
    global _inicializado
    if _inicializado:
        return {"ya_inicializado": True}

    resultados: dict[str, bool] = {}
    for plugin in descubrir_plugins():
        pid = plugin["id"]
        resultados[pid] = activar_plugin(pid, app=app)

    _inicializado = True
    evento(_log, "capas_inicializadas", plugins=list(resultados.keys()))
    return resultados
