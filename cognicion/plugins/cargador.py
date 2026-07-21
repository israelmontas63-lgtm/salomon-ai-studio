# -*- coding: utf-8 -*-
"""
Cargador de plugins — Level 9 Plug-and-Play (FastAPI-native).

Descubre extensiones en plugins/, las activa sin tumbar el núcleo,
persiste estado en data/plugins_state.json y soporta hot-plug seguro.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from settings import ROOT_DIR

if TYPE_CHECKING:
    from fastapi import FastAPI
else:
    # Runtime: tipado flexible si FastAPI aún no está importado en el caller
    try:
        from fastapi import FastAPI
    except Exception:  # pragma: no cover
        FastAPI = Any  # type: ignore[misc, assignment]

_log = logging.getLogger("salomon.plugins.cargador")

PLUGINS_DIR = ROOT_DIR / "plugins"
STATE_PATH = ROOT_DIR / "data" / "plugins_state.json"

# Registro en memoria: id → {manifest, activo, error, modulo}
_REGISTRY: dict[str, dict[str, Any]] = {}


def _cargar_manifest(ruta: Path) -> dict[str, Any] | None:
    manifest = ruta / "manifest.json"
    if not manifest.is_file():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        _log.warning(
            "plugins.manifest_invalido path=%s error=%s",
            manifest,
            type(exc).__name__,
            exc_info=True,
        )
        return None
    if not isinstance(data, dict):
        return None
    data.setdefault("id", ruta.name)
    data.setdefault("version", "0.0.0")
    data.setdefault("entry", "plugin.py")
    data.setdefault("skills", [])
    data.setdefault("capa", "periferica")
    return data


def _leer_estado_disco() -> dict[str, Any]:
    """Lee el snapshot persistido. Nunca lanza hacia el caller."""
    if not STATE_PATH.is_file():
        return {"version": 1, "activos": [], "errores": {}}
    try:
        raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            _log.warning("plugins_state.json: raíz no es dict — reiniciando estado")
            return {"version": 1, "activos": [], "errores": {}}
        activos = raw.get("activos") or []
        if not isinstance(activos, list):
            activos = []
        errores = raw.get("errores") or {}
        if not isinstance(errores, dict):
            errores = {}
        return {
            "version": int(raw.get("version") or 1),
            "activos": [str(x) for x in activos if str(x).strip()],
            "errores": {str(k): str(v) for k, v in errores.items()},
        }
    except Exception:
        _log.warning(
            "plugins_state.json: lectura falló path=%s",
            STATE_PATH,
            exc_info=True,
        )
        return {"version": 1, "activos": [], "errores": {}}


def _guardar_estado_atomico(estado: dict[str, Any]) -> bool:
    """
    Persistencia atómica: escribe a un temporal en el mismo directorio
    y reemplaza el destino (os.replace) para no corromper el JSON.
    """
    payload = {
        "version": int(estado.get("version") or 1),
        "activos": list(estado.get("activos") or []),
        "errores": dict(estado.get("errores") or {}),
    }
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=".plugins_state_",
            suffix=".json.tmp",
            dir=str(STATE_PATH.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, STATE_PATH)
        except Exception:
            try:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
            except OSError:
                pass
            raise
        return True
    except Exception:
        _log.warning(
            "plugins_state.json: escritura atómica falló path=%s",
            STATE_PATH,
            exc_info=True,
        )
        return False


def _persistir_registro() -> bool:
    """Sincroniza ids activos del registro en memoria → disco."""
    activos = sorted(
        pid for pid, reg in _REGISTRY.items() if bool(reg.get("activo"))
    )
    errores = {
        pid: str(reg.get("error"))
        for pid, reg in _REGISTRY.items()
        if reg.get("error")
    }
    return _guardar_estado_atomico(
        {"version": 1, "activos": activos, "errores": errores}
    )


def _resolver_carpeta(plugin_id: str) -> Path | None:
    pid = (plugin_id or "").strip()
    if not pid:
        return None
    carpeta = PLUGINS_DIR / pid
    if carpeta.is_dir():
        return carpeta
    if not PLUGINS_DIR.is_dir():
        return None
    try:
        for c in PLUGINS_DIR.iterdir():
            if not c.is_dir() or c.name.startswith(("_", ".")):
                continue
            m = _cargar_manifest(c)
            if m and str(m.get("id")) == pid:
                return c
    except Exception:
        _log.warning(
            "plugins.resolver_carpeta: fallo al enumerar plugins_dir",
            exc_info=True,
        )
    return None


def descubrir_plugins() -> list[dict[str, Any]]:
    """Lista plugins con manifest.json (estado activo desde registro + disco)."""
    if not PLUGINS_DIR.is_dir():
        return []

    disco = _leer_estado_disco()
    activos_disco = set(disco.get("activos") or [])

    encontrados: list[dict[str, Any]] = []
    try:
        carpetas = sorted(PLUGINS_DIR.iterdir())
    except Exception:
        _log.warning("plugins.descubrir: no se pudo listar %s", PLUGINS_DIR, exc_info=True)
        return []

    for carpeta in carpetas:
        if not carpeta.is_dir() or carpeta.name.startswith(("_", ".")):
            continue
        manifest = _cargar_manifest(carpeta)
        if manifest is None:
            continue
        pid = str(manifest.get("id") or carpeta.name)
        reg = _REGISTRY.get(pid, {})
        activo = bool(reg.get("activo")) or (
            pid in activos_disco and not reg.get("error") and pid not in _REGISTRY
        )
        encontrados.append(
            {
                "id": pid,
                "version": manifest.get("version", "0.0.0"),
                "ruta": str(carpeta.relative_to(ROOT_DIR)).replace("\\", "/"),
                "skills": list(manifest.get("skills") or []),
                "capa": manifest.get("capa", "periferica"),
                "descripcion": manifest.get("descripcion", ""),
                "activo": activo,
                "error": reg.get("error") or (disco.get("errores") or {}).get(pid),
            }
        )
    return encontrados


def _cargar_modulo(plugin_id: str, entry_path: Path) -> Any:
    """importlib aislado — cualquier fallo se propaga al sandbox de activar_plugin."""
    spec = importlib.util.spec_from_file_location(
        f"salomon_plugin_{plugin_id}",
        entry_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"spec_invalido:{plugin_id}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _registrar_rutas_plugin(app: FastAPI | None, resultado: Any, plugin_id: str) -> None:
    """
    Si el plugin devuelve un APIRouter (o dict con 'router'), lo monta
    de forma segura en la app FastAPI sin tumbar el servidor.
    """
    if app is None or resultado is None:
        return
    router = None
    prefix = ""
    if hasattr(resultado, "routes") and hasattr(app, "include_router"):
        router = resultado
    elif isinstance(resultado, dict):
        router = resultado.get("router")
        prefix = str(resultado.get("prefix") or "")
    if router is None:
        return
    try:
        if prefix:
            app.include_router(router, prefix=prefix)
        else:
            app.include_router(router)
        _log.info("plugins.rutas_montadas id=%s prefix=%r", plugin_id, prefix)
    except Exception:
        _log.warning(
            "plugins.rutas_fallo id=%s — el plugin sigue cargado sin rutas",
            plugin_id,
            exc_info=True,
        )


def activar_plugin(
    plugin_id: str,
    app: FastAPI | None = None,
    *,
    force: bool = False,
    persistir: bool = True,
) -> bool:
    """
    Carga el entry point del plugin y llama activar(app=...).

    - `app` tipado como FastAPI para registrar rutas / lifespan hooks.
    - Fallos de importlib o activar() quedan sandboxed (no derriban Uvicorn).
    - Persiste el registro activo en data/plugins_state.json.
    """
    pid = (plugin_id or "").strip()
    if not pid:
        return False

    if not force and _REGISTRY.get(pid, {}).get("activo"):
        return True

    carpeta = _resolver_carpeta(pid)
    if carpeta is None:
        _REGISTRY[pid] = {
            "activo": False,
            "error": "plugin_dir_missing",
            "manifest": None,
        }
        if persistir:
            _persistir_registro()
        return False

    manifest = _cargar_manifest(carpeta)
    if manifest is None:
        _REGISTRY[pid] = {
            "activo": False,
            "error": "manifest_missing",
            "manifest": None,
        }
        if persistir:
            _persistir_registro()
        return False

    entry = str(manifest.get("entry") or "plugin.py")
    entry_path = carpeta / entry
    if not entry_path.is_file():
        _REGISTRY[pid] = {
            "activo": False,
            "error": "entry_missing",
            "manifest": manifest,
        }
        if persistir:
            _persistir_registro()
        return False

    # Sandbox: importlib + activar()
    try:
        modulo = _cargar_modulo(pid, entry_path)
    except Exception as exc:
        err = f"{type(exc).__name__}:{exc}"
        _log.warning(
            "plugins.importlib_fallo id=%s entry=%s error=%s",
            pid,
            entry_path,
            err,
            exc_info=True,
        )
        _REGISTRY[pid] = {
            "activo": False,
            "error": err,
            "manifest": manifest,
        }
        if persistir:
            _persistir_registro()
        return False

    activar = getattr(modulo, "activar", None)
    resultado: Any = None
    ok = True
    if callable(activar):
        try:
            try:
                resultado = activar(app=app)
            except TypeError:
                # Compat plugins antiguos sin firma app=
                resultado = activar()
            ok = True if resultado is None else bool(resultado)
        except Exception as exc:
            err = f"{type(exc).__name__}:{exc}"
            _log.warning(
                "plugins.activar_fallo id=%s error=%s — servidor FastAPI intacto",
                pid,
                err,
                exc_info=True,
            )
            _REGISTRY[pid] = {
                "activo": False,
                "error": err,
                "manifest": manifest,
                "modulo": modulo,
            }
            if persistir:
                _persistir_registro()
            return False

    if ok:
        try:
            _registrar_rutas_plugin(app, resultado, pid)
        except Exception:
            _log.warning(
                "plugins.post_activar_rutas id=%s",
                pid,
                exc_info=True,
            )

    _REGISTRY[pid] = {
        "activo": ok,
        "error": None if ok else "activar_falso",
        "manifest": manifest,
        "modulo": modulo,
    }
    if persistir:
        _persistir_registro()
    return ok


def desactivar_plugin(plugin_id: str, *, persistir: bool = True) -> bool:
    """Llama desactivar() si existe; marca inactivo y persiste estado."""
    pid = (plugin_id or "").strip()
    reg = _REGISTRY.get(pid)
    if not reg:
        # Asegurar persistencia limpia si solo estaba en disco
        disco = _leer_estado_disco()
        if pid in (disco.get("activos") or []):
            disco["activos"] = [x for x in disco["activos"] if x != pid]
            if persistir:
                _guardar_estado_atomico(disco)
        return False
    modulo = reg.get("modulo")
    if modulo is not None:
        desactivar = getattr(modulo, "desactivar", None)
        if callable(desactivar):
            try:
                desactivar()
            except Exception:
                _log.warning(
                    "plugins.desactivar_fallo id=%s",
                    pid,
                    exc_info=True,
                )
    reg["activo"] = False
    if persistir:
        _persistir_registro()
    return True


def restaurar_plugins_persistidos(app: FastAPI | None = None) -> dict[str, Any]:
    """
    Restaura plugins marcados activos en data/plugins_state.json.
    Pensado para el lifespan de FastAPI (startup) — fail-soft por plugin.
    """
    estado = _leer_estado_disco()
    ids = list(estado.get("activos") or [])
    resultados: dict[str, bool] = {}
    for pid in ids:
        try:
            resultados[pid] = activar_plugin(pid, app=app, force=False, persistir=False)
        except Exception:
            _log.warning(
                "plugins.restaurar: fallo inesperado id=%s",
                pid,
                exc_info=True,
            )
            resultados[pid] = False
            _REGISTRY[pid] = {
                **_REGISTRY.get(pid, {}),
                "activo": False,
                "error": "restaurar_excepcion",
            }
    _persistir_registro()
    return {
        "ok": True,
        "restaurados": resultados,
        "total": len(ids),
        "activos": sum(1 for v in resultados.values() if v),
        "state_path": str(STATE_PATH.relative_to(ROOT_DIR)).replace("\\", "/"),
    }


def hot_plug(plugin_id: str, app: FastAPI | None = None) -> dict[str, Any]:
    """Instala/reactiva un plugin sin reiniciar el núcleo FastAPI."""
    ok = activar_plugin(plugin_id, app=app, force=True)
    reg = _REGISTRY.get(plugin_id, {})
    return {
        "ok": ok,
        "id": plugin_id,
        "activo": bool(reg.get("activo")),
        "error": reg.get("error"),
        "hot_plug": True,
        "nucleo": "sin_apagado",
        "persistido": STATE_PATH.is_file(),
    }


def estado_level9() -> dict[str, Any]:
    """Reporte Level 9 — Arquitectura Modular Plug-and-Play."""
    plugins = descubrir_plugins()
    activos = [p for p in plugins if p.get("activo")]
    perifericos = [p for p in plugins if p.get("capa") == "periferica"]
    disco = _leer_estado_disco()
    return {
        "ok": len(activos) > 0,
        "level": 9,
        "habilidad": "Arquitectura Modular Plug-and-Play",
        "motor": "plugins_capas_fastapi",
        "plugins_dir": str(PLUGINS_DIR.relative_to(ROOT_DIR)).replace("\\", "/"),
        "state_path": str(STATE_PATH.relative_to(ROOT_DIR)).replace("\\", "/"),
        "persistidos": list(disco.get("activos") or []),
        "total": len(plugins),
        "activos": len(activos),
        "perifericos": len(perifericos),
        "plugins": plugins,
        "mensaje": (
            f"Level 9 operativo: {len(activos)}/{len(plugins)} plugins activos "
            "(hot-plug FastAPI sin apagar el núcleo)."
            if plugins
            else "Sin plugins descubiertos — falta plugins/*/manifest.json"
        ),
    }


def reiniciar_registro() -> None:
    """Solo tests: limpia estado en memoria (no borra el JSON de disco)."""
    _REGISTRY.clear()
