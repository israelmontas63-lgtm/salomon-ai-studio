"""
Gestión de identidad y permisos — roles y autorización.
"""

from __future__ import annotations

from typing import Any

from cognicion.seguridad.tipos import Actor, RolAcceso
from cognicion.seguridad.secretos import obtener_secreto

_PERMISOS: dict[RolAcceso, frozenset[str]] = {
    RolAcceso.ANON: frozenset({"salud", "manifest", "estatico"}),
    RolAcceso.USUARIO: frozenset({
        "salud", "chat", "historial", "tts", "cognicion", "herramientas",
        "nucleo_lectura", "media", "sbi", "ejecutivo",
    }),
    RolAcceso.SERVICIO: frozenset({
        "salud", "chat", "historial", "tts", "cognicion", "herramientas",
        "nucleo_lectura", "agente", "media", "sbi", "ejecutivo",
    }),
    RolAcceso.ADMIN: frozenset({
        "salud", "chat", "historial", "tts", "cognicion", "herramientas",
        "nucleo_lectura", "agente", "seguridad", "auditoria", "recuperacion",
        "admin", "media", "sbi", "ejecutivo",
    }),
}

_RUTAS_PUBLICAS = frozenset({
    "/api/salud",
    "/api/nucleo/estado",
    "/api/sbi/estado",
    "/api/sbi/challenge",
    "/api/ejecutivo/estado",
    "/api/cognitivo/estado",
    "/manifest.webmanifest",
    "/favicon.svg",
    "/favicon-v2.ico",
    "/favicon-v2.svg",
    "/icon-v2.svg",
    "/icon-192-v2.png",
    "/icon-512-v2.png",
    "/apple-touch-icon-v2.png",
    "/icons.svg",
    "/media-panel.js",
    "/voice-orchestrator.css",
    "/header-logo-spec.css",
    "/thinking-animation-spec.css",
    "/salomon-ui-shield.css",
    "/salomon-ui-shield.js",
    "/salomon-orchestrator-bridge.js",
})


_RUTAS_ADMIN = (
    "/api/seguridad/",
)


def _clasificar_ruta(path: str) -> str:
    if path.startswith("/api/sbi/"):
        return "sbi"
    if path.startswith("/api/ejecutivo"):
        return "ejecutivo"
    if path.startswith("/api/cognitivo"):
        return "cognicion"
    if path.startswith("/api/seguridad/"):
        return "seguridad"
    if path.startswith("/api/cognicion/agente"):
        return "agente"
    if path.startswith("/api/grafo/"):
        return "cognicion"
    if path.startswith("/api/orquesta"):
        return "cognicion"
    if path.startswith("/api/busqueda"):
        return "cognicion"
    if path.startswith("/api/media/"):
        return "media"
    if path.startswith("/media/"):
        return "estatico"
    if path.startswith("/api/nucleo/"):
        return "nucleo_lectura"
    if path == "/api/herramientas" or path.startswith("/api/herramientas/"):
        return "herramientas"
    if path.startswith("/api/cognicion/"):
        return "cognicion"
    if path in ("/api/chat", "/api/chat/nuevo"):
        return "chat"
    if path == "/api/historial":
        return "historial"
    if path == "/api/tts" or path.startswith("/api/acciones/"):
        return "tts"
    if path == "/api/salud":
        return "salud"
    return "estatico"


def resolver_actor(
    api_key: str | None,
    ip: str = "",
    user_agent: str = "",
) -> Actor:
    admin_key = obtener_secreto("SALOMON_ADMIN_KEY")
    user_key = obtener_secreto("SALOMON_API_KEY")

    if admin_key and api_key == admin_key:
        return Actor(RolAcceso.ADMIN, "admin", ip=ip, user_agent=user_agent)
    if user_key and api_key == user_key:
        return Actor(RolAcceso.USUARIO, "usuario-api", ip=ip, user_agent=user_agent)
    if user_key and not api_key:
        return Actor(RolAcceso.ANON, "anon", ip=ip, user_agent=user_agent)
    if not user_key:
        return Actor(RolAcceso.USUARIO, "local", ip=ip, user_agent=user_agent)
    return Actor(RolAcceso.ANON, "no-autenticado", ip=ip, user_agent=user_agent)


def puede_acceder(actor: Actor, path: str, metodo: str = "GET") -> tuple[bool, str]:
    if path in _RUTAS_PUBLICAS:
        return True, "ruta_publica"

    permiso = _clasificar_ruta(path)
    permisos = set(_PERMISOS.get(actor.rol, frozenset()))

    # Sin clave admin configurada, usuario local puede consultar panel de seguridad
    if permiso == "seguridad" and not obtener_secreto("SALOMON_ADMIN_KEY"):
        if actor.rol in (RolAcceso.USUARIO, RolAcceso.SERVICIO):
            return True, "seguridad_abierta_sin_admin"

    if permiso in permisos:
        return True, "autorizado"

    if actor.rol == RolAcceso.ANON and path.startswith("/api/"):
        return False, "requiere_autenticacion"

    return False, f"rol_{actor.rol.value}_sin_permiso_{permiso}"


def requiere_admin(path: str) -> bool:
    return any(path.startswith(p) for p in _RUTAS_ADMIN)


def describir_permisos() -> dict[str, Any]:
    return {
        rol.value: sorted(_PERMISOS[rol])
        for rol in RolAcceso
    }
