"""
Copias de seguridad, recuperación y auto-reparación.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from settings import DATA_DIR, ROOT_DIR, SESIONES_DB

BACKUPS_DIR = DATA_DIR / "seguridad_backups"
MAX_BACKUPS = 10

_ARCHIVOS_CRITICOS = (
    "settings.py",
    "app.py",
    "cerebro.py",
    ".env.example",
)


def _marca_tiempo() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def crear_snapshot(motivo: str = "programado") -> dict[str, Any]:
    """Crea respaldo de archivos críticos y base de sesiones."""
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    marca = _marca_tiempo()
    destino = BACKUPS_DIR / marca
    destino.mkdir(parents=True, exist_ok=True)

    copiados: list[str] = []
    for nombre in _ARCHIVOS_CRITICOS:
        origen = ROOT_DIR / nombre
        if origen.is_file():
            shutil.copy2(origen, destino / nombre)
            copiados.append(nombre)

    if SESIONES_DB.is_file():
        shutil.copy2(SESIONES_DB, destino / "sesiones.db")
        copiados.append("sesiones.db")

    manifest = {
        "marca": marca,
        "motivo": motivo,
        "archivos": copiados,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    (destino / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    _rotar_backups()
    return manifest


def _rotar_backups() -> None:
    if not BACKUPS_DIR.is_dir():
        return
    carpetas = sorted(
        [p for p in BACKUPS_DIR.iterdir() if p.is_dir()],
        key=lambda p: p.name,
        reverse=True,
    )
    for vieja in carpetas[MAX_BACKUPS:]:
        shutil.rmtree(vieja, ignore_errors=True)


def listar_snapshots() -> list[dict[str, Any]]:
    if not BACKUPS_DIR.is_dir():
        return []
    resultado = []
    for carpeta in sorted(BACKUPS_DIR.iterdir(), key=lambda p: p.name, reverse=True):
        manifest_path = carpeta / "manifest.json"
        if manifest_path.is_file():
            try:
                resultado.append(json.loads(manifest_path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                resultado.append({"marca": carpeta.name, "error": "manifest_invalido"})
    return resultado


def restaurar_snapshot(marca: str) -> dict[str, Any]:
    """Restaura archivos de un snapshot (no sobrescribe .env)."""
    origen = BACKUPS_DIR / marca
    if not origen.is_dir():
        return {"exito": False, "error": "Snapshot no encontrado"}

    restaurados: list[str] = []
    for nombre in _ARCHIVOS_CRITICOS:
        if nombre == ".env.example":
            archivo = origen / nombre
            if archivo.is_file():
                shutil.copy2(archivo, ROOT_DIR / nombre)
                restaurados.append(nombre)

    sesiones_backup = origen / "sesiones.db"
    if sesiones_backup.is_file():
        shutil.copy2(sesiones_backup, SESIONES_DB)
        restaurados.append("sesiones.db")

    return {"exito": True, "marca": marca, "restaurados": restaurados}


_degradacion: dict[str, bool] = {}


def marcar_degradado(servicio: str, activo: bool = True) -> None:
    _degradacion[servicio] = activo


def servicio_degradado(servicio: str) -> bool:
    return _degradacion.get(servicio, False)


def intentar_recuperar(servicio: str) -> dict[str, Any]:
    """
    Auto-reparación: intenta restaurar servicio degradado.
    Nunca ejecuta acciones ofensivas — solo recuperación interna.
    """
    acciones: list[str] = []

    if servicio == "llm":
        from cognicion.llm import llm_disponible, proveedor_respaldo_disponible
        if llm_disponible():
            marcar_degradado("llm", False)
            acciones.append("llm_disponible_via_fallback")
        elif proveedor_respaldo_disponible():
            marcar_degradado("llm", True)
            acciones.append("llm_degradado_modo_local")
        else:
            marcar_degradado("llm", True)
            acciones.append("llm_no_disponible")

    elif servicio == "memoria":
        try:
            from cognicion.memoria.vectorial import obtener_memoria
            if obtener_memoria().activa:
                marcar_degradado("memoria", False)
                acciones.append("memoria_reactivada")
            else:
                marcar_degradado("memoria", True)
                acciones.append("memoria_sin_vectorial")
        except Exception:
            marcar_degradado("memoria", True)
            acciones.append("memoria_error")

    else:
        acciones.append(f"servicio_{servicio}_sin_recuperador")

    return {
        "servicio": servicio,
        "degradado": servicio_degradado(servicio),
        "acciones": acciones,
    }


def estado_recuperacion() -> dict[str, Any]:
    return {
        "degradados": {k: v for k, v in _degradacion.items() if v},
        "snapshots": len(listar_snapshots()),
        "ultimo_snapshot": listar_snapshots()[0] if listar_snapshots() else None,
    }
