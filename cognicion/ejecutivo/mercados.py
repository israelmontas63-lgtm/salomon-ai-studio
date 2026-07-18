# -*- coding: utf-8 -*-
"""Escaneo de mercados / tendencias (fuentes abiertas vía búsqueda web)."""

from __future__ import annotations

from typing import Any


def escanear_mercados(
    consulta: str = "",
    *,
    profundidad: str = "ejecutivo",
) -> dict[str, Any]:
    """
    Informe ejecutivo de mercados y tendencias.
    No opera corretaje ni toca cuentas bancarias.
    """
    from cognicion.busqueda.agente import buscar_web
    from cognicion.estado_vivo import responder_con_nucleo
    from cognicion.llm import llm_disponible

    foco = (consulta or "").strip() or (
        "mercados bursátiles tendencias inversión oportunidades "
        "economía República Dominicana y global hoy"
    )
    pack = buscar_web(foco)
    hallazgos = pack.get("hallazgos") or pack.get("resultados") or []
    # Normalizar texto de hallazgos
    lineas: list[str] = []
    for h in hallazgos[:8]:
        if isinstance(h, dict):
            t = h.get("titulo") or h.get("title") or ""
            s = h.get("snippet") or h.get("resumen") or h.get("contenido") or ""
            u = h.get("url") or h.get("enlace") or ""
            lineas.append(f"- {t}: {s} ({u})".strip())
        else:
            lineas.append(f"- {h}")

    bruto = "\n".join(lineas) if lineas else (pack.get("resumen") or str(pack)[:1200])

    if llm_disponible() and bruto.strip():
        informe = responder_con_nucleo(
            (
                "Israel pide un INFORME EJECUTIVO de mercados (bolsa, tendencias, "
                "oportunidades). Sé sobrio, accionable, sin inventar cifras. "
                "Estructura: 1) Panorama 2) Señales 3) Riesgos 4) Próximos pasos. "
                f"Profundidad: {profundidad}."
            ),
            contexto=bruto[:3500],
        )
    else:
        informe = (
            "Israel, esto es el barrido de fuentes abiertas (síntesis local):\n\n"
            f"{bruto[:2500]}\n\n"
            "Cuando el motor LLM esté activo, entrego el formato ejecutivo completo."
        )

    return {
        "ok": True,
        "modulo": "mercados",
        "consulta": foco,
        "fuentes_n": len(hallazgos) if isinstance(hallazgos, list) else 0,
        "informe": informe,
        "raw_preview": bruto[:800],
    }
