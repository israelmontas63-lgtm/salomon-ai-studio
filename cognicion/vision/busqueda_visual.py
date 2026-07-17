# -*- coding: utf-8 -*-
"""
Agentes de Recuperación Visual — búsqueda activa de imágenes HD.
Analiza intención → rastrea web → filtra por resolución/relevancia →
entrega mejor opción o genera si no hay match perfecto.
"""

from __future__ import annotations

import re
from typing import Any

from cognicion.seguridad.sandbox import ejecutar_aislado


_MARCAS_BUSQUEDA_VISUAL = (
    "busca imagen",
    "buscar imagen",
    "encuentra imagen",
    "foto de",
    "imágenes de",
    "imagenes de",
    "reference image",
    "referencia visual",
    "stock de",
    "muéstrame una imagen",
    "muestrame una imagen",
    "busca una foto",
)


def es_busqueda_visual(texto: str) -> bool:
    t = (texto or "").lower()
    return any(m in t for m in _MARCAS_BUSQUEDA_VISUAL)


def _consulta_semantica(texto: str) -> str:
    t = (texto or "").strip()
    t = re.sub(
        r"(?i)^(busca|buscar|encuentra|muéstrame|muestrame)\s+(una\s+)?(imagen|foto|imágenes|imagenes)\s+(de\s+)?",
        "",
        t,
    ).strip()
    return t or (texto or "").strip()


def _filtrar_resultados(items: list[dict[str, Any]], consulta: str) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    tokens = {w for w in consulta.lower().split() if len(w) > 2}
    for it in items:
        titulo = str(it.get("title") or it.get("titulo") or "")
        url = str(it.get("url") or it.get("enlace") or "")
        snippet = str(it.get("content") or it.get("snippet") or "")
        blob = f"{titulo} {snippet} {url}".lower()
        score = 0.0
        for tok in tokens:
            if tok in blob:
                score += 1.0
        # Preferir URLs de imagen / CDNs
        if any(ext in url.lower() for ext in (".jpg", ".jpeg", ".png", ".webp", ".avif")):
            score += 3.0
        if any(h in url.lower() for h in ("unsplash", "pexels", "pixabay", "wikimedia", "imgur")):
            score += 2.5
        if "high" in blob or "hd" in blob or "4k" in blob or "resolution" in blob:
            score += 1.0
        if score > 0:
            scored.append((score, {
                "titulo": titulo,
                "url": url,
                "snippet": snippet[:240],
                "score": score,
            }))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s[1] for s in scored[:5]]


def buscar_visual(consulta: str, *, max_resultados: int = 5) -> dict[str, Any]:
    """Despliega agente de búsqueda visual (Tavily/DDG vía agente de búsqueda)."""
    q = _consulta_semantica(consulta)
    if not q:
        return {"exito": False, "error": "consulta_vacia", "agente": "visual_scraper"}

    def _run() -> dict[str, Any]:
        from cognicion.busqueda.agente import buscar_web

        pack = buscar_web(f"{q} high resolution image photo HD")
        raw_items: list[dict[str, Any]] = []
        if isinstance(pack, dict):
            for item in pack.get("resultados") or []:
                if isinstance(item, dict):
                    raw_items.append({
                        "title": item.get("titulo") or item.get("title") or "",
                        "url": item.get("url") or item.get("enlace") or "",
                        "content": item.get("snippet") or item.get("content") or "",
                    })
            if pack.get("respuesta_directa"):
                raw_items.append({
                    "title": q,
                    "url": "",
                    "content": str(pack.get("respuesta_directa"))[:400],
                })
        filtrados = _filtrar_resultados(raw_items, q)[:max_resultados]
        mejor = filtrados[0] if filtrados else None
        return {
            "exito": bool(mejor or (pack or {}).get("exito")),
            "consulta": q,
            "intencion": "recuperacion_visual",
            "mejor": mejor,
            "candidatos": filtrados,
            "motor_busqueda": (pack or {}).get("motor") if isinstance(pack, dict) else None,
            "agente": "visual_scraper",
            "protocolo": "MULTIMODAL_CORE",
        }

    sand = ejecutar_aislado(_run, timeout_seg=8)
    if not sand.exito:
        return {
            "exito": False,
            "error": sand.error or "sandbox_fail",
            "agente": "visual_scraper",
            "consulta": q,
        }
    return sand.resultado  # type: ignore[return-value]


def recuperar_o_generar(consulta: str) -> dict[str, Any]:
    """
    Busca primero; si no hay match fuerte, genera HD con Prompt Enhancer.
    """
    busq = buscar_visual(consulta)
    mejor = (busq or {}).get("mejor") or {}
    score = float(mejor.get("score") or 0)
    if busq.get("exito") and score >= 3.0 and mejor.get("url"):
        return {
            **busq,
            "accion": "recuperado",
            "generado": False,
        }

    # Generar si no hay perfecto
    from cognicion.media.media_engine import bridge_colsub_media

    gen = bridge_colsub_media(consulta, hint="imagen_hd")
    return {
        "exito": bool(gen.get("exito")),
        "accion": "generado_fallback",
        "generado": True,
        "busqueda": busq,
        "generacion": gen,
        "agente": "visual_scraper+hd_generator",
        "protocolo": "MULTIMODAL_CORE",
    }
