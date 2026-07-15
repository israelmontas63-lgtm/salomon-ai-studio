"""
Cargador de plugins — descubre extensiones en plugins/ (Fase 2+).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from settings import ROOT_DIR

PLUGINS_DIR = ROOT_DIR / "plugins"


def _cargar_manifest(ruta: Path) -> dict[str, Any] | None:
    manifest = ruta / "manifest.json"
    if not manifest.is_file():
        return None
    try:
        return json.loads(manifest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def descubrir_plugins() -> list[dict[str, Any]]:
    if not PLUGINS_DIR.is_dir():
        return []

    encontrados: list[dict[str, Any]] = []
    for carpeta in sorted(PLUGINS_DIR.iterdir()):
        if not carpeta.is_dir():
            continue
        manifest = _cargar_manifest(carpeta)
        if manifest is None:
            continue
        encontrados.append(
            {
                "id": manifest.get("id", carpeta.name),
                "version": manifest.get("version", "0.0.0"),
                "ruta": str(carpeta.relative_to(ROOT_DIR)),
                "skills": manifest.get("skills", []),
                "activo": False,
            }
        )
    return encontrados


def activar_plugin(plugin_id: str) -> bool:
    """Carga entry point del plugin si existe."""
    carpeta = PLUGINS_DIR / plugin_id
    manifest = _cargar_manifest(carpeta)
    if manifest is None:
        return False

    entry = manifest.get("entry", "plugin.py")
    entry_path = carpeta / entry
    if not entry_path.is_file():
        return False

    spec = importlib.util.spec_from_file_location(f"plugin_{plugin_id}", entry_path)
    if spec is None or spec.loader is None:
        return False

    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    activar = getattr(modulo, "activar", None)
    if callable(activar):
        activar()
    return True
