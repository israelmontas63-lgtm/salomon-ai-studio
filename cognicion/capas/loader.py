# -*- coding: utf-8 -*-
"""
Cargador de capas — Level 9 Hot-Plug.

Descubre y activa plugins/ sin apagar el núcleo. Cada plugin se aísla:
una excepción en un módulo corrupto no tumba el arranque.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import threading
import time
from typing import Any

from cognicion.plugins.cargador import activar_plugin, descubrir_plugins, estado_level9
from cognicion.registro import evento, obtener_logger

_log = obtener_logger("capas.loader")
_lock = threading.RLock()
_inicializado = False


def inicializar_capas(app: Any = None, *, force: bool = False) -> dict[str, Any]:
    """
    Activa todos los plugins descubiertos en plugins/.
    Único punto de montaje — app.py lo invoca en startup.
    force=True permite re-scan hot-plug sin reiniciar proceso.

    Retorno: mapa id → bool | detalle de error aislado.
    Compat: callers que esperan dict[str, bool] siguen viendo True/False por id.
    """
    global _inicializado
    with _lock:
        if _inicializado and not force:
            return {"ya_inicializado": True}

        resultados: dict[str, Any] = {}
        errores: dict[str, str] = {}
        t0 = time.perf_counter()

        try:
            plugins = descubrir_plugins()
        except Exception as exc:
            evento(
                _log,
                "capas_descubrimiento_fallo",
                error=type(exc).__name__,
            )
            # Núcleo sigue vivo: sin plugins, no crash
            _inicializado = True
            return {
                "ok": False,
                "error": type(exc).__name__,
                "descubrimiento": False,
            }

        if not isinstance(plugins, list):
            plugins = []

        for plugin in plugins:
            try:
                if not isinstance(plugin, dict):
                    continue
                pid = str(plugin.get("id") or "").strip()
                if not pid:
                    continue
                t_plugin = time.perf_counter()
                try:
                    ok = bool(activar_plugin(pid, app=app, force=force))
                    resultados[pid] = ok
                    if not ok:
                        errores[pid] = "activar_retorno_false"
                except Exception as exc:
                    # Aislamiento Level-9: plugin corrupto no tumba el núcleo
                    resultados[pid] = False
                    errores[pid] = type(exc).__name__
                    evento(
                        _log,
                        "plugin_activacion_aislada",
                        plugin=pid,
                        error=type(exc).__name__,
                        ms=round((time.perf_counter() - t_plugin) * 1000, 2),
                    )
            except Exception as exc:
                # Defensa extra: fallo al leer metadata del plugin
                resultados["_scan_fault"] = False
                errores["_scan_fault"] = type(exc).__name__

        _inicializado = True
        try:
            st = estado_level9()
        except Exception:
            st = {"ok": False, "activos": 0}

        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        evento(
            _log,
            "capas_inicializadas",
            plugins=list(resultados.keys()),
            activos=st.get("activos"),
            level9=st.get("ok"),
            errores=errores or None,
            ms=elapsed,
        )
        # Metadatos no-booleanos aparte para no romper asserts de tests
        if errores:
            resultados["_errores"] = errores
        resultados["_ms"] = elapsed
        resultados["_ok"] = not bool(errores) or any(
            v is True for k, v in resultados.items() if not str(k).startswith("_")
        )
        return resultados


def estado_capas() -> dict[str, Any]:
    try:
        return estado_level9()
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__, "level": 9}


def reiniciar_flag_loader() -> None:
    """Solo tests / hot-reload controlado."""
    global _inicializado
    with _lock:
        _inicializado = False
