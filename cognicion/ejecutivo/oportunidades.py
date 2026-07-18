# -*- coding: utf-8 -*-
"""Monitoreo de empleo e ingresos online alineados al perfil de Israel."""

from __future__ import annotations

from typing import Any

PERFIL_DEFAULT = (
    "Israel Montas — Salomón AI Studio: IA, contenido educativo, "
    "desarrollo web, marca personal, monetización digital, República Dominicana"
)


def escanear_oportunidades(
    perfil: str = "",
    *,
    consulta: str = "",
) -> dict[str, Any]:
    from cognicion.busqueda.agente import buscar_web
    from cognicion.estado_vivo import responder_con_nucleo
    from cognicion.llm import llm_disponible

    p = (perfil or PERFIL_DEFAULT).strip()
    q = (consulta or "").strip() or (
        "empleos remoto IA contenido creador freelance "
        "oportunidades ingreso online República Dominicana"
    )
    pack = buscar_web(f"{q} {p}")
    hallazgos = pack.get("hallazgos") or pack.get("resultados") or []
    items: list[dict[str, str]] = []
    for h in hallazgos[:8]:
        if isinstance(h, dict):
            items.append(
                {
                    "titulo": str(h.get("titulo") or h.get("title") or "")[:200],
                    "snippet": str(h.get("snippet") or h.get("resumen") or "")[:400],
                    "url": str(h.get("url") or h.get("enlace") or "")[:400],
                }
            )

    contexto = "\n".join(
        f"- {i['titulo']}: {i['snippet']} {i['url']}" for i in items
    ) or str(pack)[:1500]

    if llm_disponible():
        plan = responder_con_nucleo(
            (
                "Israel Montas pide oportunidades de ingreso/empleo alineadas a su perfil. "
                "Filtra ruido. Por cada oportunidad sólida: encaje, por qué, "
                "plan de acción en 3 pasos (aplicar / crear / contactar). "
                "Si no hay encaje real, dilo con honestidad."
            ),
            contexto=f"Perfil:\n{p}\n\nHallazgos:\n{contexto[:3000]}",
        )
    else:
        plan = (
            "Israel, oportunidades detectadas (síntesis local):\n\n"
            f"{contexto[:2200]}\n\n"
            "Prioriza las que digan remoto / freelance / IA / contenido."
        )

    return {
        "ok": True,
        "modulo": "oportunidades",
        "perfil": p[:300],
        "consulta": q,
        "candidatos_n": len(items),
        "candidatos": items,
        "plan_accion": plan,
        "notificacion": bool(items),
    }
