# -*- coding: utf-8 -*-
"""
Puente neuronal — lib ↔ core ↔ cognición ↔ API.

Registra las librerías de soporte en el bus sináptico y verifica que
herramientas / clima / SystemGuard / búsqueda estén importables desde
el núcleo sin cabos sueltos.
"""

from __future__ import annotations

from typing import Any

_PUENTE_ESTADO: dict[str, Any] = {
    "conectado": False,
    "modulos_ok": {},
    "synapses": [],
    "error": None,
}

# Canal de soporte: capacidades lib → razonamiento (capa 3) y autonomía (6)
LIB_SYNAPSE = {
    "from": 0,
    "to": 3,
    "channel": "lib_support_tools",
    "methods": [
        "ejecutar_herramienta",
        "listar_herramientas",
        "consultar_clima",
        "buscar_web",
        "systemguard_verify",
    ],
    "payload": {"nombre": str, "args": dict},
    "module": "lib/neural_bridge.py",
    "note": "Capa 0 = librerías de soporte (lib/). No muta UI ni visión.",
}


def estado_puente() -> dict[str, Any]:
    return dict(_PUENTE_ESTADO)


def _probe_modulos() -> dict[str, Any]:
    out: dict[str, Any] = {}

    try:
        from lib import herramientas as h

        out["herramientas"] = {
            "ok": True,
            "apis": [
                "listar_herramientas",
                "ejecutar_herramienta",
                "obtener_herramienta",
            ],
            "count": len(h.listar_herramientas(activas_only=False)),
        }
    except Exception as exc:
        out["herramientas"] = {"ok": False, "error": type(exc).__name__}

    try:
        from lib import clima as c

        out["clima"] = {
            "ok": True,
            "apis": ["es_consulta_clima", "preparar_contexto_clima", "obtener_datos_clima"],
            "has_palabras": bool(getattr(c, "PALABRAS_CLIMA", None)),
        }
    except Exception as exc:
        out["clima"] = {"ok": False, "error": type(exc).__name__}

    try:
        from lib import system_guard as sg

        root = str(getattr(sg, "ROOT", ""))
        out["system_guard"] = {
            "ok": True,
            "root_is_repo": root.endswith("SALOMON AI SS") or "salomon" in root.lower(),
            "apis": [
                a
                for a in (
                    "verificar_contra_ledger",
                    "estado",
                    "heal",
                    "verify",
                )
                if hasattr(sg, a)
            ],
        }
    except Exception as exc:
        out["system_guard"] = {"ok": False, "error": type(exc).__name__}

    try:
        from lib import web_search as ws

        st = ws.estado_conectividad() if hasattr(ws, "estado_conectividad") else {}
        out["web_search"] = {"ok": True, "estado": st}
    except Exception as exc:
        out["web_search"] = {"ok": False, "error": type(exc).__name__}

    try:
        import importlib

        vo = importlib.import_module("lib.voice_orchestrator")
        out["voice_orchestrator"] = {
            "ok": True,
            "apis": [a for a in ("emitir_voz",) if hasattr(vo, a)],
        }
    except Exception as exc:
        out["voice_orchestrator"] = {"ok": False, "error": type(exc).__name__}

    # Shims de raíz (compatibilidad)
    try:
        import herramientas as h_root  # noqa: F401
        import clima as c_root  # noqa: F401
        import SystemGuard as sg_root  # noqa: F401

        out["shims_raiz"] = {"ok": True}
    except Exception as exc:
        out["shims_raiz"] = {"ok": False, "error": type(exc).__name__}

    return out


def _registrar_sinapsis() -> list[dict[str, Any]]:
    """Añade el canal lib→razonamiento al bus si aún no está."""
    try:
        from cognicion.capas_inteligencia import synaptic_bus as bus

        existing = bus.list_synapses()
        if any(s.get("channel") == LIB_SYNAPSE["channel"] for s in existing):
            return [s for s in existing if s.get("channel") == LIB_SYNAPSE["channel"]]
        bus.AUTHORIZED_SYNAPSES.append(dict(LIB_SYNAPSE))
        return [dict(LIB_SYNAPSE)]
    except Exception:
        return []


def conectar_nucleo() -> dict[str, Any]:
    """
    Inicializador único: sonda módulos lib, registra sinapsis,
    enlaza con core.MainController si está disponible.
    Fail-soft: nunca tumba el arranque.
    """
    global _PUENTE_ESTADO
    try:
        modulos_ok = _probe_modulos()
        synapses = _registrar_sinapsis()

        core_ok = False
        try:
            from core import LogicEngine, MainController

            _ = LogicEngine
            _ = MainController
            core_ok = True
        except Exception:
            core_ok = False

        cognicion_ok = False
        try:
            from cognicion.errores import CODIGOS  # noqa: F401

            cognicion_ok = True
        except Exception:
            cognicion_ok = False

        todos = all(bool(v.get("ok")) for v in modulos_ok.values())
        _PUENTE_ESTADO = {
            "conectado": bool(todos and core_ok),
            "modulos_ok": modulos_ok,
            "synapses": synapses,
            "core": core_ok,
            "cognicion": cognicion_ok,
            "channel": LIB_SYNAPSE["channel"],
            "error": None if todos else "modulo_lib_fallo",
        }
        return dict(_PUENTE_ESTADO)
    except Exception as exc:
        _PUENTE_ESTADO = {
            "conectado": False,
            "modulos_ok": {},
            "synapses": [],
            "error": type(exc).__name__,
            "detalle": str(exc)[:240],
        }
        return dict(_PUENTE_ESTADO)


def emitir_capacidad(nombre: str, **kwargs: Any) -> dict[str, Any]:
    """
    Despacha una capacidad lib hacia el núcleo (tools / clima / búsqueda).
    Usado por FC y orquestador sin importar rutas sueltas.
    """
    nombre = (nombre or "").strip().lower()
    try:
        if nombre in ("herramienta", "tool", "ejecutar_herramienta"):
            from lib import herramientas as h

            tid = kwargs.get("id") or kwargs.get("herramienta_id") or ""
            return h.ejecutar_herramienta(tid, **{
                k: v for k, v in kwargs.items() if k not in ("id", "herramienta_id")
            })
        if nombre in ("clima", "consultar_clima", "weather"):
            from lib import clima as c

            texto = str(kwargs.get("texto") or kwargs.get("mensaje") or "")
            lat = kwargs.get("lat")
            lon = kwargs.get("lon")
            if hasattr(c, "preparar_contexto_clima"):
                ctx = c.preparar_contexto_clima(texto, lat=lat, lon=lon)
                return {"ok": True, "data": ctx}
            if hasattr(c, "obtener_datos_clima"):
                return {"ok": True, "data": c.obtener_datos_clima(**kwargs)}
            return {"ok": False, "error": "clima_api_ausente", "error_codigo": 25}
        if nombre in ("buscar", "buscar_web", "web_search"):
            from lib import web_search as ws

            return ws.consultar(str(kwargs.get("mensaje") or kwargs.get("q") or ""))
        if nombre in ("systemguard", "integrity", "systemguard_verify"):
            from lib import system_guard as sg

            if hasattr(sg, "verificar_contra_ledger"):
                return {"ok": True, "data": sg.verificar_contra_ledger()}
            return {"ok": False, "error": "systemguard_api_ausente", "error_codigo": 25}
        return {"ok": False, "error": "capacidad_desconocida", "error_codigo": 21}
    except Exception as exc:
        from cognicion.errores import clasificar

        err = clasificar(exc, pista="herramienta")
        return {
            "ok": False,
            "error": type(exc).__name__,
            "error_codigo": err.codigo,
            "error_causa": err.causa,
        }
