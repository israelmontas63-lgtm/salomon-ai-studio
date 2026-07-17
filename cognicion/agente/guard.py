# -*- coding: utf-8 -*-
"""
Agent_Guard — sistema inmune: integridad (checksum) + memoria + deps Render.
"""

from __future__ import annotations

from typing import Any


# Bibliotecas pesadas / inestables en Render Starter — bloqueadas por defecto
LIBS_BLOQUEADAS_RENDER = frozenset({
    "torch", "tensorflow", "transformers", "diffusers", "onnxruntime-gpu",
    "opencv-python", "opencv-contrib-python", "paddlepaddle", "detectron2",
    "llama-cpp-python", "vllm", "bitsandbytes", "xformers",
})

# Alternativas ligeras preferidas
ALTERNATIVAS_LIGERAS = {
    "torch": "usar APIs remotas (Flux/DALL·E/Gemini) vía httpx — sin peso local",
    "tensorflow": "usar proveedor cloud vía OPENAI_API_KEY / GEMINI_API_KEY",
    "opencv-python": "Pillow + httpx (ya en requirements)",
    "transformers": "Gemini/OpenAI remoto — no cargar pesos en Render",
    "diffusers": "Flux/MJ/DALL·E gateway (MEDIA_* env)",
}


def validar_dependencia_render(paquete: str) -> dict[str, Any]:
    """Agent_Guard: bloquea libs que colapsan Render Starter."""
    nombre = (paquete or "").strip().lower().split("==")[0].split(">=")[0].split("[")[0].strip()
    if not nombre:
        return {"ok": False, "error": "paquete_vacio", "agente": "Agent_Guard"}
    if nombre in LIBS_BLOQUEADAS_RENDER:
        return {
            "ok": False,
            "bloqueado": True,
            "paquete": nombre,
            "motivo": "inestable_o_pesado_para_render_starter",
            "alternativa": ALTERNATIVAS_LIGERAS.get(
                nombre, "usar API externa vía variable de entorno"
            ),
            "agente": "Agent_Guard",
        }
    return {
        "ok": True,
        "paquete": nombre,
        "bloqueado": False,
        "nota": "Añadir manualmente a requirements.txt tras revisión; nunca pip install en runtime Live.",
        "agente": "Agent_Guard",
    }


def supervisar_integridad(raise_on_drift: bool = False) -> dict[str, Any]:
    """Checksum ledger + SystemGuard (lazy import)."""
    import SystemGuard as sg

    rep = sg.verificar_contra_ledger(raise_on_drift=raise_on_drift)
    return {
        "ok": rep.get("ok"),
        "checked": rep.get("checked"),
        "drift": rep.get("drift"),
        "protocol": "MULTI_AGENT_DEPLOY",
        "agente": "Agent_Guard",
    }


def autorizar_escritura(ruta: str, *, autorizado: bool = False) -> dict[str, Any]:
    """Niega escritura a Core sin AUTORIZADO."""
    import SystemGuard as sg

    try:
        sg.assert_writable(ruta, autorizado=autorizado)
        return {"ok": True, "ruta": ruta, "agente": "Agent_Guard"}
    except sg.IntegrityViolation as exc:
        return {
            "ok": False,
            "ruta": ruta,
            "error": str(exc),
            "agente": "Agent_Guard",
            "integrity_violation": True,
        }


def liberar_memoria_suave() -> dict[str, Any]:
    """Libera RAM no crítica tras una acción de agente (best-effort)."""
    import gc

    recolectados = gc.collect()
    return {
        "ok": True,
        "gc_collect": recolectados,
        "agente": "Agent_Guard",
        "lazy": True,
    }


def ejecutar_guard(accion: str = "integridad", **kwargs: Any) -> dict[str, Any]:
    """Entrada única lazy del Agent_Guard."""
    if accion == "deps":
        return validar_dependencia_render(kwargs.get("paquete") or "")
    if accion == "escritura":
        return autorizar_escritura(
            kwargs.get("ruta") or "",
            autorizado=bool(kwargs.get("autorizado")),
        )
    if accion == "gc":
        return liberar_memoria_suave()
    return supervisar_integridad(raise_on_drift=bool(kwargs.get("raise_on_drift")))
