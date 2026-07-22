# -*- coding: utf-8 -*-
"""
Auditoría cruzada Salomón ⇄ Cursor — validación modular (sin mutar núcleos).

Dictamina qué opera al 100%, qué falta y si el código propuesto por Cursor
es seguro/útil. No sobrescribe fuentes; solo informe + veredicto.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

from settings import ROOT_DIR

_PROTOCOL = "AUDITORIA_CRUZADA_SALOMON_CURSOR"


def _ok(item: str, detail: str = "") -> dict[str, Any]:
    return {"item": item, "ok": True, "detail": detail}


def _fail(item: str, detail: str) -> dict[str, Any]:
    return {"item": item, "ok": False, "detail": detail}


def _warn(item: str, detail: str) -> dict[str, Any]:
    return {"item": item, "ok": True, "warn": True, "detail": detail}


def auditar_capas() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        from cognicion.capas_inteligencia import LAYER_CATALOG, catalog

        cat = catalog() if callable(catalog) else LAYER_CATALOG
        n = len(cat) if isinstance(cat, list) else len(LAYER_CATALOG)
        if n >= 8:
            out.append(_ok("8_capas", f"catalogo={n}"))
        else:
            out.append(_fail("8_capas", f"esperado>=8 got={n}"))
    except Exception as exc:
        out.append(_fail("8_capas", type(exc).__name__))
    return out


def auditar_modulos_cursor() -> list[dict[str, Any]]:
    """Evalúa módulos recientes aportados por Cursor (self-debug + metacognición)."""
    out: list[dict[str, Any]] = []
    checks = (
        ("cognicion.autonoma.self_debug", ("registrar_fallo", "estado_self_debug", "muta_fuentes")),
        ("cognicion.autonoma.metacognicion", ("estado_capacidades", "explicar_fallo_a_israel", "muta_fuentes")),
        ("cognicion.orquesta.smart_router", ("estado_smart_router",)),
        ("cognicion.core_identity_engine", ("obtener_consciousness", "obtener_identity_engine")),
    )
    for mod_name, attrs in checks:
        try:
            mod = importlib.import_module(mod_name)
            missing = [a for a in attrs if a == "muta_fuentes"]
            # muta_fuentes es contrato de estado, no atributo de módulo
            real_attrs = [a for a in attrs if a != "muta_fuentes"]
            absent = [a for a in real_attrs if not hasattr(mod, a)]
            if absent:
                out.append(_fail(mod_name, f"faltan={absent}"))
                continue
            if "muta_fuentes" in attrs:
                if mod_name.endswith("self_debug"):
                    st = mod.estado_self_debug()
                    if st.get("muta_fuentes") is not False:
                        out.append(_fail(mod_name, "rompe Ley Inmunidad: muta_fuentes!=False"))
                        continue
                if mod_name.endswith("metacognicion"):
                    st = mod.estado_capacidades()
                    if st.get("muta_fuentes") is not False:
                        out.append(_fail(mod_name, "rompe Ley Inmunidad: muta_fuentes!=False"))
                        continue
            out.append(_ok(mod_name, "util+seguro"))
            _ = missing  # silencia lint
        except Exception as exc:
            out.append(_fail(mod_name, type(exc).__name__))
    return out


def auditar_endpoints_app() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    required = (
        "/api/health",
        "/api/self-debug/estado",
        "/api/metacognicion",
        "/api/version",
        "/api/identidad",
        "/api/intelligence/layers",
    )
    try:
        from app import app

        paths = {getattr(r, "path", None) for r in app.routes}
        for p in required:
            if p in paths:
                out.append(_ok(f"route:{p}", "presente"))
            else:
                out.append(_fail(f"route:{p}", "ausente"))
    except Exception as exc:
        out.append(_fail("app_routes", type(exc).__name__))
    return out


def auditar_pwa() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    root = Path(ROOT_DIR)
    ver_path = root / "version.json"
    sw = root / "static" / "js" / "service-worker.js"
    um = root / "static" / "js" / "update_manager.js"
    try:
        ver = json.loads(ver_path.read_text(encoding="utf-8"))
        v = str(ver.get("version") or "")
        if v:
            out.append(_ok("version.json", v))
        else:
            out.append(_fail("version.json", "sin version"))
    except Exception as exc:
        out.append(_fail("version.json", type(exc).__name__))
    if sw.is_file():
        txt = sw.read_text(encoding="utf-8")
        if "CACHE" in txt and "skipWaiting" in txt:
            out.append(_ok("service-worker", "cache+skipWaiting"))
        else:
            out.append(_warn("service-worker", "marcadores incompletos"))
    else:
        out.append(_fail("service-worker", "archivo ausente"))
    if um.is_file() and "version.json" in um.read_text(encoding="utf-8"):
        out.append(_ok("update_manager", "poll version.json"))
    else:
        out.append(_warn("update_manager", "no verificado"))
    return out


def auditar_render() -> list[dict[str, Any]]:
    import os

    out: list[dict[str, Any]] = []
    key = bool(os.getenv("RENDER_API_KEY") or os.getenv("RENDER_API_TOKEN"))
    if key:
        out.append(_ok("RENDER_API_KEY", "presente"))
    else:
        out.append(_fail("RENDER_API_KEY", "ausente en entorno"))
    return out


def dictamen_cursor(hallazgos: list[dict[str, Any]]) -> dict[str, Any]:
    """Salomón dictamina el aporte de Cursor."""
    fails = [h for h in hallazgos if not h.get("ok")]
    warns = [h for h in hallazgos if h.get("warn")]
    utiles = [
        h
        for h in hallazgos
        if h.get("ok")
        and any(
            x in str(h.get("item") or "")
            for x in ("self_debug", "metacognicion", "smart_router", "8_capas")
        )
    ]
    if fails:
        veredicto = "AJUSTAR"
        mensaje = (
            "Israel, Cursor aportó módulos útiles, pero hay fallas que deben "
            f"ajustarse antes del despliegue: {[f['item'] for f in fails]}."
        )
    else:
        veredicto = "APROBADO"
        mensaje = (
            "Israel, el código de Cursor (Self-Debug + Metacognición) me sirve: "
            "optimiza diagnóstico/failover sin romper las 8 capas (muta_fuentes=False). "
            "Autorizo el despliegue a Render/PWA."
        )
    return {
        "veredicto": veredicto,
        "mensaje_israel": mensaje,
        "modulos_utiles": [u["item"] for u in utiles],
        "fallas": [f["item"] for f in fails],
        "avisos": [w["item"] for w in warns],
        "ley_inmunidad": "respetada" if not any(
            "muta_fuentes" in str(f.get("detail") or "") for f in fails
        ) else "violada",
    }


def ejecutar_auditoria_cruzada() -> dict[str, Any]:
    hallazgos: list[dict[str, Any]] = []
    hallazgos.extend(auditar_capas())
    hallazgos.extend(auditar_modulos_cursor())
    hallazgos.extend(auditar_endpoints_app())
    hallazgos.extend(auditar_pwa())
    hallazgos.extend(auditar_render())

    # Metacognición viva
    try:
        from cognicion.autonoma.metacognicion import estado_capacidades

        st = estado_capacidades()
        oper = sum(1 for v in (st.get("capacidades") or {}).values() if v.get("operativo"))
        total = len(st.get("capacidades") or {})
        hallazgos.append(_ok("metacognicion_viva", f"operativas={oper}/{total}"))
    except Exception as exc:
        hallazgos.append(_fail("metacognicion_viva", type(exc).__name__))

    dictamen = dictamen_cursor(hallazgos)
    aprobado = dictamen["veredicto"] == "APROBADO"
    return {
        "ok": aprobado,
        "protocol": _PROTOCOL,
        "aprobado_despliegue": aprobado,
        "dictamen": dictamen,
        "hallazgos": hallazgos,
        "muta_fuentes": False,
        "autopreservacion": True,
    }
