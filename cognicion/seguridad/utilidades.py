"""Utilidades base — enmascaramiento y rutas sensibles."""

from __future__ import annotations

import re

_PATRONES_SECRETO = (
    re.compile(r"sk-[a-zA-Z0-9_-]{10,}"),
    re.compile(r"sk-proj-[a-zA-Z0-9_-]{10,}"),
    re.compile(r"gsk_[a-zA-Z0-9_-]{10,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{10,}"),
    re.compile(r"AQ\.[0-9A-Za-z_-]{10,}"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)['\"]?[a-zA-Z0-9._-]{8,}"),
)

_RUTAS_BLOQUEADAS = (
    "/.env",
    ".env",
    "/.git",
    "secrets/",
    "id_rsa",
    "credentials",
    "/etc/passwd",
    "/proc/",
    "seguridad.db",
)

_PATRONES_INYECCION = (
    re.compile(r"(?i)(union\s+select|drop\s+table|;\s*--|or\s+1\s*=\s*1)"),
    re.compile(r"(?i)(<script|javascript:|onerror\s*=)"),
    re.compile(r"\.\./"),
    re.compile(r"(?i)(cmd\.exe|/bin/sh|powershell\s+-)"),
)


def enmascarar_secreto(texto: str) -> str:
    """Oculta claves API u otros secretos embebidos en texto."""
    if not texto:
        return texto
    resultado = texto
    for patron in _PATRONES_SECRETO:
        if patron.groups:
            resultado = patron.sub(r"\1[REDACTED]", resultado)
        else:
            resultado = patron.sub("[REDACTED]", resultado)
    return resultado


def ruta_sensible(path: str) -> bool:
    """True si la ruta no debe servirse públicamente."""
    normalizada = (path or "").lower().replace("\\", "/")
    return any(fragmento in normalizada for fragmento in _RUTAS_BLOQUEADAS)


def contiene_patron_sospechoso(texto: str) -> bool:
    """Detecta patrones típicos de inyección o path traversal."""
    if not texto:
        return False
    return any(p.search(texto) for p in _PATRONES_INYECCION)
