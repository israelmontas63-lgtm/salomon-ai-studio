"""
Permisos de function-calling — valida SALOMON_ADMIN_KEY para herramientas sensibles.
"""

from __future__ import annotations

from cognicion.seguridad.secretos import obtener_secreto

_HERRAMIENTAS_ADMIN = frozenset({
    "seguridad",
    "backup_export",
})


def requiere_admin(tool_id: str) -> bool:
    return tool_id in _HERRAMIENTAS_ADMIN


def puede_ejecutar(tool_id: str, api_key: str | None = None) -> tuple[bool, str]:
    """
    Valida si la herramienta puede ejecutarse con la clave dada.
    Si SALOMON_ADMIN_KEY no está configurada, permite (modo desarrollo).
    """
    if tool_id not in _HERRAMIENTAS_ADMIN:
        return True, ""

    admin_key = obtener_secreto("SALOMON_ADMIN_KEY")
    if not admin_key:
        return True, ""

    if api_key and api_key == admin_key:
        return True, ""

    return False, "Requiere SALOMON_ADMIN_KEY (rol administrador)"
