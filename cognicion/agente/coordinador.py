# -*- coding: utf-8 -*-
"""
Coordinador Multi-Agente v80 — zero-overlap + lazy RAM para Render.

Roles exclusivos:
- Agent_Coder  → Python/JS
- Agent_Visual → búsqueda/generación visual
- Agent_Guard  → integridad + deps + GC
"""

from __future__ import annotations

from typing import Any, Literal

RolAgente = Literal["coder", "visual", "guard", "ninguno"]

_MARCAS_CODER = (
    "código", "codigo", "python", "javascript", "refactor", "función", "funcion",
    "bug", "parche", "implementa", "endpoint", "fastapi", "debug", "c++",
)
_MARCAS_VISUAL = (
    "imagen", "foto", "boceto", "dibuja", "ilustra", "video", "genera una imagen",
    "busca imagen", "hd", "dall-e", "flux", "render visual",
)
_MARCAS_GUARD = (
    "integridad", "checksum", "systemguard", "desmembramiento", "golden",
    "dependencia", "requirements", "librería", "libreria", "instalar paquete",
)


def clasificar_rol(mensaje: str) -> RolAgente:
    """Un solo agente por turno — evita solapamiento."""
    t = (mensaje or "").lower()
    # Guard tiene prioridad sobre instalaciones / integridad
    if any(m in t for m in _MARCAS_GUARD):
        return "guard"
    # Visual antes que coder si hay señales claras de media
    if any(m in t for m in _MARCAS_VISUAL):
        return "visual"
    if any(m in t for m in _MARCAS_CODER):
        return "coder"
    return "ninguno"


def coordinar(mensaje: str, **kwargs: Any) -> dict[str, Any]:
    """
    Despacha al agente correcto (lazy). Libera RAM al terminar.
    Nunca instala pip en runtime — solo valida deps vía Guard.
    """
    rol = clasificar_rol(mensaje)
    meta: dict[str, Any] = {
        "coordinador": True,
        "protocolo": "MULTI_AGENT_DEPLOY",
        "version": "80.0.0",
        "rol": rol,
        "overlap": False,
    }

    if rol == "ninguno":
        return {**meta, "exito": True, "delegado": False, "nota": "sin_agente_especializado"}

    if rol == "guard":
        from cognicion.agente.guard import ejecutar_guard, validar_dependencia_render

        # Si pide instalar X, validar sin pip install
        lower = mensaje.lower()
        if "instalar" in lower or "requirements" in lower or "paquete" in lower:
            # Extraer última palabra candidata simple
            tokens = [w.strip(",.;") for w in mensaje.replace("\n", " ").split() if w]
            candidato = ""
            for i, w in enumerate(tokens):
                if w.lower() in {"instalar", "paquete", "librería", "libreria", "dependency"}:
                    if i + 1 < len(tokens):
                        candidato = tokens[i + 1]
            if not candidato and tokens:
                candidato = tokens[-1]
            val = validar_dependencia_render(candidato)
            return {**meta, "exito": val.get("ok"), "agente": "Agent_Guard", "resultado": val}

        out = ejecutar_guard(kwargs.get("accion") or "integridad")
        return {**meta, "exito": out.get("ok"), "agente": "Agent_Guard", "resultado": out}

    if rol == "visual":
        from cognicion.agente.visual import ejecutar_visual

        out = ejecutar_visual(mensaje, modo=kwargs.get("modo") or "auto")
        return {**meta, "exito": out.get("exito"), "agente": "Agent_Visual", "resultado": out}

    # coder
    from cognicion.agente.coder import ejecutar_coder

    out = ejecutar_coder(
        mensaje,
        error_consola=kwargs.get("error_consola"),
        solo_razonamiento=bool(kwargs.get("solo_razonamiento", True)),
    )
    return {**meta, "exito": out.get("exito"), "agente": "Agent_Coder", "resultado": out}


def estado_multiagente() -> dict[str, Any]:
    from cognicion.agente.registro import listar_agentes
    from settings import COLSUB_MAX_AGENTES, COLSUB_MAX_WORKERS, COLSUB_RAM_CRITICO

    return {
        "protocol": "MULTI_AGENT_DEPLOY",
        "version": "80.0.0",
        "parent_protocol": "MULTIMODAL_CORE",
        "active": True,
        "agentes": {
            "Agent_Coder": {"id": "coder", "rol": "python_js", "lazy": True},
            "Agent_Visual": {"id": "visual", "rol": "media_apis", "lazy": True},
            "Agent_Guard": {"id": "guard", "rol": "integridad_deps", "lazy": True},
            "Coordinador": {"id": "coordinador", "rol": "orquestacion", "zero_overlap": True},
        },
        "registrados": [
            {"id": a.id, "rol": a.rol, "activo": a.activo, "nombre": a.nombre}
            for a in listar_agentes(activos_only=False)
        ],
        "render": {
            "workers_gunicorn": 1,
            "colsub_max_agentes": COLSUB_MAX_AGENTES,
            "colsub_max_workers": COLSUB_MAX_WORKERS,
            "ram_critico_pct": COLSUB_RAM_CRITICO,
            "apis_via_env": True,
            "pip_runtime_prohibido": True,
        },
        "apis_imagen_listas": True,
        "nota": "Agentes lazy: se activan solo bajo demanda y liberan RAM con GC suave.",
    }
