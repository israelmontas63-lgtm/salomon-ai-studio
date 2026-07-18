# -*- coding: utf-8 -*-
"""
Mapa semántico de la mente de Salomón — una sola entidad, hilos con contexto.

Áreas (lógicas, no módulos aislados):
  voz · visión · razonamiento · memoria · hilos
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from settings import ROOT_DIR

MENTE_ROOT = Path(ROOT_DIR) / "data" / "mente"
HILOS_DIR = MENTE_ROOT / "hilos"
VOZ_DIR = MENTE_ROOT / "voz"
VISION_DIR = MENTE_ROOT / "vision"
RAZON_DIR = MENTE_ROOT / "razonamiento"
MEMORIA_DIR = MENTE_ROOT / "memoria"


AREAS_SEMANTICAS = (
    "voz",
    "vision",
    "razonamiento",
    "memoria",
    "hilos",
)


def asegurar_estructura() -> dict[str, str]:
    """Crea el árbol semántico en disco (idempotente)."""
    paths = {
        "raiz": MENTE_ROOT,
        "hilos": HILOS_DIR,
        "voz": VOZ_DIR,
        "vision": VISION_DIR,
        "razonamiento": RAZON_DIR,
        "memoria": MEMORIA_DIR,
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
        keep = p / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")
    return {k: str(v) for k, v in paths.items()}


def mapa_mente() -> dict[str, Any]:
    asegurar_estructura()
    return {
        "entidad": "Salomon",
        "dueno": "Israel Monta",
        "areas": list(AREAS_SEMANTICAS),
        "paths": asegurar_estructura(),
        "principio": (
            "Una sola voz. Razonamiento > búsqueda. "
            "Cada hilo guarda su propio contexto. "
            "Hardware (mic/cámara) alimenta el mismo cerebro."
        ),
    }
