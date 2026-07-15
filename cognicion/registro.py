"""
Registro estructurado mínimo — logging centralizado del núcleo cognitivo.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from settings import LOG_LEVEL

from cognicion.seguridad.utilidades import enmascarar_secreto

_CONFIGURADO = False
_FORMATO = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configurar_registro(nivel: str | None = None) -> None:
    """Configura logging una sola vez (idempotente)."""
    global _CONFIGURADO
    if _CONFIGURADO:
        return

    nivel_efectivo = (nivel or LOG_LEVEL).upper()
    logging.basicConfig(
        level=getattr(logging, nivel_efectivo, logging.INFO),
        format=_FORMATO,
        stream=sys.stdout,
        force=True,
    )
    _CONFIGURADO = True


def obtener_logger(nombre: str = "salomon") -> logging.Logger:
    """Devuelve un logger del namespace salomon.*."""
    configurar_registro()
    return logging.getLogger(f"salomon.{nombre}")


def evento(logger: logging.Logger, accion: str, **campos: Any) -> None:
    """Log de evento con pares clave=valor en una línea."""
    extras = " ".join(
        f"{k}={enmascarar_secreto(str(v))!r}" for k, v in campos.items() if v is not None
    )
    logger.info("%s %s", accion, extras)
