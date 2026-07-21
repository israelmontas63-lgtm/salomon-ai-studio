# -*- coding: utf-8 -*-
"""
lib/ — Librerías internas de soporte de Salomón AI.

Hogar canónico de módulos que antes vivían sueltos en la raíz:
  · herramientas   — registry de tools / FC
  · clima          — OpenWeather → contexto LLM
  · system_guard   — integridad / Golden Snapshot
  · web_search     — fachada de búsqueda
  · voice_orchestrator — TTS bridge (tests / legacy)

El núcleo (core / cognicion / app) puede importar `lib.*` o los shims
de raíz (`import herramientas`, `import SystemGuard`) — ambos enlazan aquí.

Puente neuronal: `lib.neural_bridge.conectar_nucleo()`.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "VERSION",
    "estado_lib",
    "conectar_nucleo",
    "modulos",
]

VERSION = "1.0.0"


def modulos() -> dict[str, str]:
    return {
        "herramientas": "lib.herramientas",
        "clima": "lib.clima",
        "system_guard": "lib.system_guard",
        "web_search": "lib.web_search",
        "voice_orchestrator": "lib.voice_orchestrator",
        "neural_bridge": "lib.neural_bridge",
    }


def estado_lib() -> dict[str, Any]:
    from lib.neural_bridge import estado_puente

    return {
        "ok": True,
        "version": VERSION,
        "package": "lib",
        "modulos": modulos(),
        "puente": estado_puente(),
    }


def conectar_nucleo() -> dict[str, Any]:
    """Inicializa y sella el puente lib ↔ core ↔ cognición."""
    from lib.neural_bridge import conectar_nucleo as _conectar

    return _conectar()
