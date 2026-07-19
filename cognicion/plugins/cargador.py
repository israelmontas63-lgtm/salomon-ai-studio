# -*- coding: utf-8 -*-
"""
Cargador de plugins — Level 9 Plug-and-Play (habilidad 30-X #9).

Descubre extensiones en plugins/, las activa sin apagar el núcleo
y permite hot-plug en caliente.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from settings import ROOT_DIR

PLUGINS_DIR = ROOT_DIR / "plugins"

# Registro en memoria: id → {manifest, activo, error, modulo}
_REGISTRY: dict[str, dict[str, Any]] = {}


def _cargar_manifest(ruta: Path) -> dict[str, Any] | None:
    manifest = ruta / "manifest.json"
    if not manifest.is_file():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    data.setdefault("id", ruta.name)
    data.setdefault("version", "0.0.0")
    data.setdefault("entry", "plugin.py")
    data.setdefault("skills", [])
    data.setdefault("capa", "periferica")
    return data


def descubrir_plugins() -> list[dict[str, Any]]:
    """Lista plugins con manifest.json (estado activo desde el registro)."""
    if not PLUGINS_DIR.is_dir():
        return []

    encontrados: list[dict[str, Any]] = []
    for carpeta in sorted(PLUGINS_DIR.iterdir()):
        if not carpeta.is_dir() or carpeta.name.startswith(("_", ".")):
            continue
        manifest = _cargar_manifest(carpeta)
        if manifest is None:
            continue
        pid = str(manifest.get("id") or carpeta.name)
        reg = _REGISTRY.get(pid, {})
        encontrados.append(
            {
                "id": pid,
                "version": manifest.get("version", "0.0.0"),
                "ruta": str(carpeta.relative_to(ROOT_DIR)).replace("\\", "/"),
                "skills": list(manifest.get("skills") or []),
                "capa": manifest.get("capa", "periferica"),
                "descripcion": manifest.get("descripcion", ""),
                "activo": bool(reg.get("activo")),
                "error": reg.get("error"),
            }
        )
    return encontrados


def _cargar_modulo(plugin_id: str, entry_path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(
        f"salomon_plugin_{plugin_id}", entry_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"spec_invalido:{plugin_id}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def activar_plugin(plugin_id: str, app: Any = None, *, force: bool = False) -> bool:
    """
    Carga el entry point del plugin y llama activar(app=...).
    Idempotente salvo force=True.
    """
    pid = (plugin_id or "").strip()
    if not pid:
        return False

    if not force and _REGISTRY.get(pid, {}).get("activo"):
        return True

    carpeta = PLUGINS_DIR / pid
    # Permitir id distinto al nombre de carpeta vía discovery
    if not carpeta.is_dir():
        for c in PLUGINS_DIR.iterdir() if PLUGINS_DIR.is_dir() else []:
            if not c.is_dir():
                continue
            m = _cargar_manifest(c)
            if m and str(m.get("id")) == pid:
                carpeta = c
                break

    manifest = _cargar_manifest(carpeta)
    if manifest is None:
        _REGISTRY[pid] = {"activo": False, "error": "manifest_missing", "manifest": None}
        return False

    entry = str(manifest.get("entry") or "plugin.py")
    entry_path = carpeta / entry
    if not entry_path.is_file():
        _REGISTRY[pid] = {
            "activo": False,
            "error": "entry_missing",
            "manifest": manifest,
        }
        return False

    try:
        modulo = _cargar_modulo(pid, entry_path)
        activar = getattr(modulo, "activar", None)
        if callable(activar):
            try:
                resultado = activar(app=app)
            except TypeError:
                resultado = activar()
            ok = True if resultado is None else bool(resultado)
        else:
            ok = True
        _REGISTRY[pid] = {
            "activo": ok,
            "error": None if ok else "activar_falso",
            "manifest": manifest,
            "modulo": modulo,
        }
        return ok
    except Exception as exc:
        _REGISTRY[pid] = {
            "activo": False,
            "error": f"{type(exc).__name__}:{exc}",
            "manifest": manifest,
        }
        return False


def desactivar_plugin(plugin_id: str) -> bool:
    """Llama desactivar() si existe; marca inactivo en registro."""
    pid = (plugin_id or "").strip()
    reg = _REGISTRY.get(pid)
    if not reg:
        return False
    modulo = reg.get("modulo")
    if modulo is not None:
        desactivar = getattr(modulo, "desactivar", None)
        if callable(desactivar):
            try:
                desactivar()
            except Exception:
                pass
    reg["activo"] = False
    return True


def hot_plug(plugin_id: str, app: Any = None) -> dict[str, Any]:
    """Instala/reactiva un plugin sin reiniciar el núcleo."""
    ok = activar_plugin(plugin_id, app=app, force=True)
    reg = _REGISTRY.get(plugin_id, {})
    return {
        "ok": ok,
        "id": plugin_id,
        "activo": bool(reg.get("activo")),
        "error": reg.get("error"),
        "hot_plug": True,
        "nucleo": "sin_apagado",
    }


def estado_level9() -> dict[str, Any]:
    """Reporte Level 9 — Arquitectura Modular Plug-and-Play."""
    plugins = descubrir_plugins()
    activos = [p for p in plugins if p.get("activo")]
    perifericos = [p for p in plugins if p.get("capa") == "periferica"]
    return {
        "ok": len(activos) > 0,
        "level": 9,
        "habilidad": "Arquitectura Modular Plug-and-Play",
        "motor": "plugins_capas",
        "plugins_dir": str(PLUGINS_DIR.relative_to(ROOT_DIR)).replace("\\", "/"),
        "total": len(plugins),
        "activos": len(activos),
        "perifericos": len(perifericos),
        "plugins": plugins,
        "mensaje": (
            f"Level 9 operativo: {len(activos)}/{len(plugins)} plugins activos "
            "(hot-plug sin apagar el núcleo)."
            if plugins
            else "Sin plugins descubiertos — falta plugins/*/manifest.json"
        ),
    }


def reiniciar_registro() -> None:
    """Solo tests: limpia estado en memoria."""
    _REGISTRY.clear()
