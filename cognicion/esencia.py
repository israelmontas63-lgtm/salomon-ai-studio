# -*- coding: utf-8 -*-
"""
Protocolo de Esencia y Autosostenibilidad (Nivel 2026+).

Leyes: Inteligencia · Protección · Evolución.
Regeneración: SystemGuard (hash + Golden Snapshot + heal).
Agentes recursivos: Arquitecto → Ejecutores → micro-agentes efímeros.
Aprendizaje ontológico: patrones de entorno → ledger de esencia.
"""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
LEDGER_ESENCIA = ROOT / "salomon_esencia_ledger.jsonl"

LEYES = ("inteligencia", "proteccion", "evolucion")
PROTOCOLO = "ESENCIA_AUTOSOSTENIBILIDAD_2026"
VERSION = "2026.7.18"

ProgressFn = Callable[[str, dict[str, Any]], None]

_lock = threading.Lock()


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append(entry: dict[str, Any]) -> None:
    row = {**entry, "at": _utc(), "protocol": PROTOCOLO, "version": VERSION}
    with _lock:
        with LEDGER_ESENCIA.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def leyes_fundamentales() -> dict[str, str]:
    return {
        "inteligencia": "Comprender, sintetizar y decidir con utilidad para Israel.",
        "proteccion": "Preservar núcleo, marca y estabilidad Free Tier.",
        "evolucion": "Crecer con criterio SCE; nunca por inyección ciega.",
    }


def aprendizaje_ontologico(
    senal: str,
    *,
    categoria: str = "entorno",
    origen: str = "runtime",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    No descarta información: la categoriza y extrae un patrón mínimo.
    Persistencia ligera (jsonl) — apta para Render Free Tier.
    """
    texto = (senal or "").strip()
    if not texto:
        return {"ok": False, "error": "senal_vacia"}

    lower = texto.lower()
    patron = "general"
    if any(x in lower for x in ("error", "exception", "traceback", "oom", "drift")):
        patron = "riesgo_operativo"
    elif any(x in lower for x in ("deploy", "render", "build", "restart")):
        patron = "ciclo_despliegue"
    elif any(x in lower for x in ("israel", "saludo", "chat", "mensaje")):
        patron = "interaccion_humana"
    elif any(x in lower for x in ("tts", "cartesia", "vision", "busqueda")):
        patron = "capacidad_sensorial"

    tokens = re.findall(r"[a-záéíóúñ]{4,}", lower)
    # Top señales léxicas (sin pesos pesados)
    freq: dict[str, int] = {}
    for t in tokens[:80]:
        freq[t] = freq.get(t, 0) + 1
    top = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:8]

    entry = {
        "tipo": "aprendizaje_ontologico",
        "categoria": categoria,
        "origen": origen,
        "patron": patron,
        "senal_preview": texto[:280],
        "lexico_top": top,
        "meta": meta or {},
        "leyes": list(LEYES),
    }
    _append(entry)
    return {"ok": True, "patron": patron, "lexico_top": top}


def protocolo_resiliencia(*, auto_heal: bool = True) -> dict[str, Any]:
    """Autochequeo hash + regeneración segura desde Golden Snapshot."""
    import SystemGuard as sg

    mapping = sg.mapear_integridad()
    report = sg.verificar_contra_ledger(raise_on_drift=False)
    heal = None
    if not report.get("ok") and auto_heal:
        paths = [d.get("path") for d in (report.get("drift") or []) if d.get("path")]
        safe = [
            p
            for p in paths
            if p
            and (
                "camera" in p.replace("\\", "/")
                or p.endswith("index.html")
                or p.endswith("salomon-security-kernel.js")
            )
        ]
        if safe:
            heal = sg.auto_reparar(safe)
            report = sg.verificar_contra_ledger(raise_on_drift=False)

    _append(
        {
            "tipo": "resiliencia",
            "integrity_ok": bool(report.get("ok")),
            "checked": report.get("checked"),
            "drift_n": len(report.get("drift") or []),
            "healed": bool((heal or {}).get("healed")),
        }
    )
    return {
        "activo": True,
        "protocolo": "RESILIENCIA_SYSTEMGUARD",
        "integrity_ok": bool(report.get("ok")),
        "checked": report.get("checked"),
        "drift": report.get("drift") or [],
        "heal": heal,
        "mapping_files": list((mapping.get("files") or {}).keys()),
        "leyes": list(LEYES),
    }


def _micro_busqueda(tarea: str) -> dict[str, Any]:
    try:
        from cognicion.orquesta.agentes_paralelos import desplegar_agentes_paralelos

        pack = desplegar_agentes_paralelos(tarea, agentes=["web"], max_workers=1)
        return {
            "rol": "micro_busqueda",
            "ok": True,
            "hallazgos": pack.get("total_hallazgos") or 0,
            "resumen": (pack.get("informes") or [{}])[0].get("resumen")
            if pack.get("informes")
            else "",
        }
    except Exception as exc:
        return {"rol": "micro_busqueda", "ok": False, "error": str(exc)[:160]}


def _micro_analisis(tarea: str, contexto: str = "") -> dict[str, Any]:
    texto = f"{tarea}\n{contexto}".strip()
    riesgo = any(
        x in texto.lower()
        for x in ("borrar", "rm -rf", "camera-engine", "bypass", "desactivar systemguard")
    )
    return {
        "rol": "micro_analisis",
        "ok": True,
        "viable": not riesgo,
        "patron": "riesgo" if riesgo else "viable",
        "nota": "bloqueo preventivo" if riesgo else "vía libre con criterio",
    }


def _micro_defensa() -> dict[str, Any]:
    try:
        from cognicion.agente.guard import supervisar_integridad

        rep = supervisar_integridad(raise_on_drift=False)
        return {
            "rol": "micro_defensa",
            "ok": bool(rep.get("ok")),
            "checked": rep.get("checked"),
            "drift": rep.get("drift") or [],
        }
    except Exception as exc:
        return {"rol": "micro_defensa", "ok": False, "error": str(exc)[:160]}


def arquitecto_desplegar(
    tarea: str,
    *,
    on_progress: ProgressFn | None = None,
    con_busqueda: bool = True,
) -> dict[str, Any]:
    """
    Red dinámica: Arquitecto → Ejecutores → micro-agentes.
    Al terminar, fusiona hallazgos en memoria central (ledger esencia).
    """
    tid = uuid4().hex[:12]
    if on_progress:
        on_progress("arquitecto", {"mensaje": "Arquitecto coordinando micro-agentes…", "id": tid})

    micros: list[dict[str, Any]] = []
    # Defensa siempre (Protección)
    micros.append(_micro_defensa())
    # Análisis siempre (Inteligencia)
    micros.append(_micro_analisis(tarea))
    # Búsqueda bajo demanda (Evolución / conocimiento)
    if con_busqueda and len((tarea or "").strip()) >= 12:
        if on_progress:
            on_progress("micro_busqueda", {"mensaje": "Micro-agente de búsqueda activo…"})
        micros.append(_micro_busqueda(tarea))

    fusion = {
        "tarea": (tarea or "")[:240],
        "micros_ok": sum(1 for m in micros if m.get("ok")),
        "micros_total": len(micros),
        "defensa_ok": next((m.get("ok") for m in micros if m.get("rol") == "micro_defensa"), None),
        "viable": next(
            (m.get("viable") for m in micros if m.get("rol") == "micro_analisis"),
            True,
        ),
    }
    aprendizaje_ontologico(
        f"mision:{tarea[:200]} fusion={fusion}",
        categoria="malla_agentes",
        origen="arquitecto",
        meta={"id": tid, "micros": [m.get("rol") for m in micros]},
    )
    if on_progress:
        on_progress("fusion", {"mensaje": "Micro-agentes fusionados en memoria central.", "id": tid})

    return {
        "ok": True,
        "id": tid,
        "arquitecto": "Agent_Arquitecto",
        "micros": micros,
        "fusion": fusion,
        "voz": "Salomon",  # una sola voz hacia Israel
        "leyes": list(LEYES),
        "protocolo": PROTOCOLO,
    }


def auditoria_esencia(*, auto_heal: bool = True) -> dict[str, Any]:
    """Auditoría interna: leyes en núcleo + regeneración activa + malla."""
    from cerebro import SalomonAI

    nucleo = SalomonAI.INSTRUCCION_SISTEMA
    en_nucleo = {
        "esencia_bloque": "Protocolo de Esencia 2026+" in nucleo,
        "leyes_inteligencia": "Inteligencia" in nucleo and "Protección" in nucleo,
        "leyes_evolucion": "Evolución" in nucleo,
        "estado_vivo": "Estado Vivo" in nucleo and "HD Cognitiva" in nucleo,
        "systemguard_ref": "SystemGuard" in nucleo,
        "aprendizaje_ontologico": "Aprendizaje ontológico" in nucleo,
        "agentes_recursivos": "micro-agentes" in nucleo,
    }
    resiliencia = protocolo_resiliencia(auto_heal=auto_heal)
    malla = arquitecto_desplegar(
        "auditoría de esencia — verificación de malla sin carga externa",
        con_busqueda=False,
    )

    ok = (
        all(en_nucleo.values())
        and resiliencia.get("activo") is True
        and malla.get("ok") is True
    )
    report = {
        "ok": ok,
        "protocolo": PROTOCOLO,
        "version": VERSION,
        "fecha_anclaje": "2026-07-18",
        "leyes": leyes_fundamentales(),
        "nucleo": en_nucleo,
        "regeneracion": {
            "activo": resiliencia.get("activo"),
            "integrity_ok": resiliencia.get("integrity_ok"),
            "checked": resiliencia.get("checked"),
            "drift_n": len(resiliencia.get("drift") or []),
            "heal": resiliencia.get("heal"),
        },
        "malla_agentes": {
            "arquitecto": malla.get("arquitecto"),
            "micros": [m.get("rol") for m in (malla.get("micros") or [])],
            "fusion": malla.get("fusion"),
        },
        "estado_vivo": True,
    }
    _append({"tipo": "auditoria_esencia", "ok": ok, "resumen": {
        "integrity_ok": resiliencia.get("integrity_ok"),
        "nucleo": en_nucleo,
    }})
    return report
