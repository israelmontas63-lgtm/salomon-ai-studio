"""
Orquestador multi-agente — despliega agentes especializados en paralelo.

Agentes:
- web: Tavily / DuckDuckGo / noticias
- academico: Wikipedia + Wikidata
- mercado: señales de precios / commodities vía fuentes públicas ligeras

Si un agente falla, los demás continúan (fail-soft).
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from cognicion.busqueda.agente import buscar_web, extraer_consulta

_MARCADORES_ORQUESTA = (
    "orquesta",
    "multiagente",
    "multi-agente",
    "investiga a fondo",
    "investigación",
    "investigacion",
    "compara fuentes",
    "análisis completo",
    "analisis completo",
    "académico",
    "academico",
    "paper",
    "mercado",
    "precio",
    "cotización",
    "cotizacion",
    "tendencia",
    "desde varios ángulos",
    "varios angulos",
)


def necesita_orquesta(
    mensaje: str,
    *,
    forzar: bool = False,
    hechos_personales: str = "",
) -> bool:
    """Consulta compleja o memoria insuficiente → desplegar orquesta."""
    if forzar:
        return True
    t = (mensaje or "").strip().lower()
    if not t:
        return False
    if any(m in t for m in _MARCADORES_ORQUESTA):
        return True
    # Complejidad: largo + pregunta, o varias interrogaciones
    if len(t) >= 140 and ("?" in t or t.count(",") >= 2):
        return True
    if t.count("?") >= 2:
        return True
    # Memoria personal pobre ante pregunta factual abierta
    hechos = (hechos_personales or "").strip()
    factual = any(
        p in t
        for p in ("qué es", "que es", "quién", "quien", "cómo funciona", "como funciona", "por qué")
    )
    if factual and len(t) >= 40 and len(hechos) < 80:
        return True
    return False


def _agente_web(consulta: str) -> dict[str, Any]:
    try:
        datos = buscar_web(consulta)
        return {
            "agente": "web",
            "exito": bool(datos.get("exito")),
            "motor": datos.get("motor"),
            "resumen": (datos.get("respuesta_directa") or "")[:1200],
            "hallazgos": [
                {
                    "titulo": i.get("titulo"),
                    "snippet": (i.get("snippet") or "")[:300],
                    "url": i.get("url"),
                }
                for i in (datos.get("resultados") or [])[:4]
            ],
            "error": datos.get("error"),
        }
    except Exception as exc:
        return {"agente": "web", "exito": False, "error": type(exc).__name__, "hallazgos": []}


def _agente_academico(consulta: str) -> dict[str, Any]:
    try:
        from cognicion.conectores import consultar_wikipedia, consultar_wikidata

        hallazgos: list[dict[str, str]] = []
        resumen_parts: list[str] = []

        wiki = consultar_wikipedia(consulta)
        if wiki and wiki.contexto:
            cuerpo = wiki.contexto
            if "Instrucción:" in cuerpo:
                cuerpo = cuerpo.split("Instrucción:")[0]
            lineas = [
                ln.strip()
                for ln in cuerpo.splitlines()
                if ln.strip() and not ln.strip().startswith("[")
            ]
            texto = "\n".join(lineas)[:900]
            if texto and "no encontr" not in texto.lower():
                resumen_parts.append(texto)
                hallazgos.append({"titulo": "Wikipedia", "snippet": texto[:300], "url": ""})

        wiki_d = consultar_wikidata(consulta)
        if wiki_d and wiki_d.contexto:
            cuerpo = wiki_d.contexto
            if "Instrucción:" in cuerpo:
                cuerpo = cuerpo.split("Instrucción:")[0]
            lineas = [
                ln.strip()
                for ln in cuerpo.splitlines()
                if ln.strip() and not ln.strip().startswith("[")
            ]
            texto = "\n".join(lineas)[:500]
            if texto:
                resumen_parts.append(texto)
                hallazgos.append({"titulo": "Wikidata", "snippet": texto[:300], "url": ""})

        ok = bool(resumen_parts)
        return {
            "agente": "academico",
            "exito": ok,
            "motor": "wikipedia+wikidata",
            "resumen": "\n\n".join(resumen_parts)[:1500],
            "hallazgos": hallazgos,
            "error": None if ok else "sin_fuente_academica",
        }
    except Exception as exc:
        return {
            "agente": "academico",
            "exito": False,
            "error": type(exc).__name__,
            "hallazgos": [],
        }


def _agente_mercado(consulta: str) -> dict[str, Any]:
    """Señales de mercado / precios vía búsqueda orientada (fail-soft)."""
    try:
        q = f"{consulta} precio mercado tendencia"
        # Si la consulta no parece de mercado, aún aporta contexto económico ligero
        t = consulta.lower()
        if not any(
            x in t
            for x in (
                "precio",
                "mercado",
                "dólar",
                "dolar",
                "acción",
                "accion",
                "crypto",
                "bitcoin",
                "oro",
                "petróleo",
                "petroleo",
                "inflación",
                "inflacion",
                "cotiz",
                "venta",
                "monetiz",
            )
        ):
            q = f"contexto económico {consulta}"

        datos = buscar_web(q)
        hallazgos = [
            {
                "titulo": i.get("titulo"),
                "snippet": (i.get("snippet") or "")[:300],
                "url": i.get("url"),
            }
            for i in (datos.get("resultados") or [])[:4]
        ]
        resumen = (datos.get("respuesta_directa") or "")[:1000]
        if not resumen and hallazgos:
            resumen = "\n".join(
                f"- {h.get('titulo')}: {h.get('snippet')}" for h in hallazgos[:3]
            )
        return {
            "agente": "mercado",
            "exito": bool(resumen or hallazgos),
            "motor": datos.get("motor") or "mercado_web",
            "resumen": resumen,
            "hallazgos": hallazgos,
            "error": datos.get("error") if not (resumen or hallazgos) else None,
        }
    except Exception as exc:
        return {
            "agente": "mercado",
            "exito": False,
            "error": type(exc).__name__,
            "hallazgos": [],
        }


_AGENTES: dict[str, Callable[[str], dict[str, Any]]] = {
    "web": _agente_web,
    "academico": _agente_academico,
    "mercado": _agente_mercado,
}


def desplegar_agentes_paralelos(
    consulta: str,
    *,
    agentes: list[str] | None = None,
    max_workers: int = 3,
) -> dict[str, Any]:
    """
    Lanza agentes en paralelo. Un fallo no detiene a los demás.
    """
    q = extraer_consulta(consulta)
    elegidos = agentes or list(_AGENTES.keys())
    informes: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futuros = {
            pool.submit(_AGENTES[nombre], q): nombre
            for nombre in elegidos
            if nombre in _AGENTES
        }
        for fut in as_completed(futuros):
            nombre = futuros[fut]
            try:
                informes.append(fut.result())
            except Exception as exc:
                informes.append(
                    {
                        "agente": nombre,
                        "exito": False,
                        "error": type(exc).__name__,
                        "hallazgos": [],
                    }
                )

    # Orden estable
    orden = {n: i for i, n in enumerate(_AGENTES)}
    informes.sort(key=lambda x: orden.get(x.get("agente", ""), 99))

    exitosos = [i for i in informes if i.get("exito")]
    return {
        "exito": bool(exitosos),
        "consulta": q,
        "informes": informes,
        "agentes_ok": [i["agente"] for i in exitosos],
        "agentes_fallidos": [i["agente"] for i in informes if not i.get("exito")],
        "total_hallazgos": sum(len(i.get("hallazgos") or []) for i in informes),
    }


def consolidar_hallazgos_texto(pack: dict[str, Any]) -> str:
    """Texto plano para el nodo de razonamiento (sin redundancias burdas)."""
    vistos: set[str] = set()
    bloques: list[str] = []
    for inf in pack.get("informes") or []:
        agente = inf.get("agente", "?")
        if not inf.get("exito"):
            bloques.append(f"[{agente}] (sin datos: {inf.get('error') or 'fallo'})")
            continue
        resumen = (inf.get("resumen") or "").strip()
        clave = re.sub(r"\s+", " ", resumen[:160].lower())
        if clave and clave in vistos:
            continue
        if clave:
            vistos.add(clave)
        lineas = [f"[{agente.upper()} — {inf.get('motor') or 'fuente'}]"]
        if resumen:
            lineas.append(resumen[:900])
        for h in (inf.get("hallazgos") or [])[:3]:
            sn = (h.get("snippet") or "").strip()
            tit = (h.get("titulo") or "").strip()
            frag = f"{tit}: {sn}".strip(": ")
            frag_k = re.sub(r"\s+", " ", frag[:120].lower())
            if frag_k and frag_k not in vistos:
                vistos.add(frag_k)
                lineas.append(f"• {frag[:280]}")
        bloques.append("\n".join(lineas))
    return "\n\n".join(bloques)


def sintetizar_orquesta(
    consulta: str,
    pack: dict[str, Any],
    *,
    hechos_personales: str = "",
    intentar_llm: bool = False,
) -> str:
    """Síntesis elegante Salomón a partir de informes multi-agente."""
    cuerpo = consolidar_hallazgos_texto(pack)
    if not cuerpo.strip():
        return (
            f"Israel, desplegué la orquesta de agentes sobre «{consulta}», "
            "pero aún no obtuve hallazgos sólidos. Afina el enfoque y lo intento de nuevo."
        )

    # Síntesis local primero (estable bajo cuota; sin reintentos LLM)
    lineas = [
        f"Israel, reuní varias fuentes en paralelo sobre «{consulta}».",
        "",
        cuerpo[:2800],
        "",
    ]
    ok = pack.get("agentes_ok") or []
    fail = pack.get("agentes_fallidos") or []
    if ok:
        lineas.append(f"Agentes que aportaron: {', '.join(ok)}.")
    if fail:
        lineas.append(
            f"Agentes sin datos (el resto continuó): {', '.join(fail)}."
        )
    lineas.append(
        "¿Quieres que profundice en el ángulo web, académico o de mercado?"
    )
    local = "\n".join(lineas)

    if not intentar_llm:
        return local

    try:
        from cognicion.llm import generar_texto, llm_disponible

        if not llm_disponible():
            return local
        prompt = f"""Eres Salomón. Estilo negro y oro: elegante, profundo, claro.
Consolida los informes. Elimina redundancias. No menciones cuotas ni fallos de API.

Consulta: {consulta}

Informes:
{cuerpo[:3500]}

Entrega apertura breve, síntesis unificada, matices y una pregunta de cierre."""
        texto = (generar_texto(prompt) or "").strip()
        baja = texto.lower()
        if (
            len(texto) > 80
            and "eres salomón" not in baja
            and "consolida los informes" not in baja
            and "no hallé un resumen sólido para «eres" not in baja
        ):
            return texto
    except Exception:
        pass
    return local
