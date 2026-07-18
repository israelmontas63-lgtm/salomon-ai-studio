# -*- coding: utf-8 -*-
"""Estratega de contenido y crecimiento (tendencias → guion / hashtags)."""

from __future__ import annotations

from typing import Any


def estratega_contenido(
    tema: str = "",
    *,
    plataforma: str = "shorts",
) -> dict[str, Any]:
    from cognicion.busqueda.agente import buscar_web
    from cognicion.estado_vivo import responder_con_nucleo
    from cognicion.llm import llm_disponible

    t = (tema or "").strip() or "tendencias virales contenido educativo ciencia marca personal"
    pack = buscar_web(f"tendencias virales {t} hashtags crecimiento {plataforma}")
    hallazgos = pack.get("hallazgos") or pack.get("resultados") or []
    hechos: list[str] = []
    for h in hallazgos[:6]:
        if isinstance(h, dict):
            hechos.append(
                f"{h.get('titulo') or h.get('title') or ''}: "
                f"{h.get('snippet') or h.get('resumen') or ''}"
            )
        else:
            hechos.append(str(h))
    contexto = "\n".join(hechos) if hechos else str(pack)[:1500]

    prompt = (
        f"Eres estratega de contenido de Salomón AI Studio para Israel Montas. "
        f"Plataforma: {plataforma}. Tema: {t}. "
        "Entrega: 1) Ángulo viral 2) Guion corto (gancho-idea-ejemplo-CTA) "
        "3) 12 hashtags 4) Plan de crecimiento 7 días. "
        "Tono negro y oro, español dominicano natural, sin hype vacío."
    )

    if llm_disponible():
        plan = responder_con_nucleo(prompt, contexto=contexto[:3000])
    else:
        plan = (
            f"Israel, barrido de tendencias para «{t}» ({plataforma}):\n\n"
            f"{contexto[:2000]}\n\n"
            "Hashtags base: #SalomonAI #CienciaClara #MarcaPersonal #RD "
            "#ContenidoQueEnseña #NegroYOro\n"
            "Activa el LLM para guion optimizado completo."
        )

    return {
        "ok": True,
        "modulo": "contenido",
        "tema": t,
        "plataforma": plataforma,
        "estrategia": plan,
    }
