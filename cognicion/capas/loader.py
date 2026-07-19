# -*- coding: utf-8 -*-
"""
Cargador de capas — Level 9: activa plugins/ sin apagar el núcleo.
"""

from __future__ import annotations

from typing import Any

from cognicion.plugins.cargador import activar_plugin, descubrir_plugins, estado_level9
from cognicion.registro import evento, obtener_logger

_log = obtener_logger("capas.loader")
_inicializado = False


def inicializar_capas(app: Any = None, *, force: bool = False) -> dict[str, bool]:
    """
    Activa todos los plugins descubiertos en plugins/.
    Único punto de montaje — app.py lo invoca en startup.
    force=True permite re-scan hot-plug sin reiniciar proceso.
    """
    global _inicializado
    if _inicializado and not force:
        return {"ya_inicializado": True}

    resultados: dict[str, bool] = {}
    for plugin in descubrir_plugins():
        pid = str(plugin["id"])
        resultados[pid] = activar_plugin(pid, app=app, force=force)

    _inicializado = True
    st = estado_level9()
    evento(
        _log,
        "capas_inicializadas",
        plugins=list(resultados.keys()),
        activos=st.get("activos"),
        level9=st.get("ok"),
    )
    return resultados


def estado_capas() -> dict[str, Any]:
    return estado_level9()
