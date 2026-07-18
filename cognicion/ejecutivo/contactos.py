# -*- coding: utf-8 -*-
"""
Identificación de contactos / números (fuentes públicas opcionales).

Sin API key: clasificación heurística + búsqueda web del número.
Con NUMVERIFY_API_KEY o ABSTRACT_PHONE_API_KEY: lookup enriquecido.
Nunca inventa identidad de persona.
"""

from __future__ import annotations

import os
import re
from typing import Any

import httpx


def _normalizar_numero(raw: str) -> str:
    digitos = re.sub(r"[^\d+]", "", (raw or "").strip())
    return digitos


def _heuristica(numero: str) -> dict[str, Any]:
    n = numero.lstrip("+")
    etiqueta = "desconocido"
    riesgo = "medio"
    notas: list[str] = []

    # RD móvil típico 1809 / 1829 / 1849
    if n.startswith("1809") or n.startswith("1829") or n.startswith("1849"):
        etiqueta = "posible_rd_local"
        riesgo = "bajo"
        notas.append("Prefijo República Dominicana.")
    elif n.startswith("1800") or n.startswith("1888") or n.startswith("1877"):
        etiqueta = "posible_comercial_tollfree"
        riesgo = "medio"
        notas.append("Línea gratuita / comercial frecuente.")
    elif len(n) < 8:
        etiqueta = "incompleto"
        riesgo = "alto"
        notas.append("Número demasiado corto para clasificar.")

    # Patrones spam comunes (heurística suave)
    if re.search(r"(\d)\1{5,}", n):
        riesgo = "alto"
        notas.append("Patrón repetitivo — revisar con cautela.")

    return {
        "clasificacion_heuristica": etiqueta,
        "nivel_riesgo": riesgo,
        "notas": notas,
    }


def _lookup_numverify(numero: str) -> dict[str, Any] | None:
    key = (os.getenv("NUMVERIFY_API_KEY") or "").strip()
    if not key:
        return None
    try:
        with httpx.Client(timeout=12.0) as client:
            r = client.get(
                "http://apilayer.net/api/validate",
                params={"access_key": key, "number": numero, "format": 1},
            )
        if r.status_code != 200:
            return {"ok": False, "error": f"http_{r.status_code}"}
        data = r.json()
        return {
            "ok": bool(data.get("valid")),
            "proveedor": "numverify",
            "pais": data.get("country_name"),
            "carrier": data.get("carrier"),
            "linea": data.get("line_type"),
            "internacional": data.get("international_format"),
            "raw_ok": True,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:160], "proveedor": "numverify"}


def identificar_contacto(numero: str, *, contexto: str = "") -> dict[str, Any]:
    from cognicion.busqueda.agente import buscar_web
    from cognicion.estado_vivo import responder_con_nucleo
    from cognicion.llm import llm_disponible

    num = _normalizar_numero(numero)
    if not num:
        return {"ok": False, "error": "numero_vacio", "modulo": "contactos"}

    heur = _heuristica(num)
    api = _lookup_numverify(num)

    pack = buscar_web(f"número telefónico {num} spam estafa empresa contacto")
    hallazgos = pack.get("hallazgos") or pack.get("resultados") or []
    web_bits: list[str] = []
    for h in hallazgos[:5]:
        if isinstance(h, dict):
            web_bits.append(
                f"{h.get('titulo') or ''}: {h.get('snippet') or h.get('resumen') or ''}"
            )

    contexto_txt = (
        f"Número: {num}\nHeurística: {heur}\nAPI: {api}\n"
        f"Contexto usuario: {contexto}\nWeb:\n" + "\n".join(web_bits)
    )

    if llm_disponible():
        veredicto = responder_con_nucleo(
            (
                "Clasifica este número para Israel Montas en UNA de: "
                "oportunidad_negocio | contacto_personal | amenaza_spam | desconocido. "
                "No inventes nombre de persona. Sé sobrio. "
                "Incluye recomendación: contestar / ignorar / investigar."
            ),
            contexto=contexto_txt[:3000],
        )
    else:
        veredicto = (
            f"Número {num}. Clasificación preliminar: {heur['clasificacion_heuristica']} "
            f"(riesgo {heur['nivel_riesgo']}). "
            + (" ".join(heur["notas"]) if heur["notas"] else "")
            + " Configura NUMVERIFY_API_KEY para lookup enriquecido."
        )

    categoria = "desconocido"
    baja = veredicto.lower()
    if "amenaza" in baja or "spam" in baja:
        categoria = "amenaza_spam"
    elif "oportunidad" in baja or "negocio" in baja:
        categoria = "oportunidad_negocio"
    elif "personal" in baja:
        categoria = "contacto_personal"

    return {
        "ok": True,
        "modulo": "contactos",
        "numero": num,
        "categoria": categoria,
        "heuristica": heur,
        "lookup": api,
        "analisis": veredicto,
    }
