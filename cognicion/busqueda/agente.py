"""Agente de búsqueda web — Tavily (preferido) + DuckDuckGo/noticias (respaldo)."""

from __future__ import annotations

import re
from typing import Any

import httpx

from settings import TAVILY_API_KEY


_MARCADORES_LIMITE = (
    "límite de uso",
    "limite de uso",
    "límite de cuota",
    "limite de cuota",
    "quota",
    "gemini está en su límite",
    "motor en la nube está en su límite",
    "motor en la nube esta en su limite",
    "servicio de ia en la nube está en límite",
    "intenta de nuevo en unos minutos",
    "inténtalo otra vez en unos minutos",
    "cuando se restablezca la cuota",
    "servicio de gemini",
    "resource exhausted",
    "rate limit",
)

def necesita_busqueda_web(
    mensaje: str,
    *,
    llm_limitado: bool = False,
    respuesta_previa: str | None = None,
    forzar: bool = False,
) -> bool:
    """Activa web SOLO con pedido explícito de Israel (Memory Cortex)."""
    from cognicion.busqueda.pedido_explicito import (
        es_saludo_o_charla_simple,
        pedido_busqueda_explicito,
    )

    if forzar:
        return True
    # Saludos / charla: NUNCA salir a internet (ni por cuota LLM)
    if es_saludo_o_charla_simple(mensaje):
        return False
    if pedido_busqueda_explicito(mensaje):
        return True
    # Cuota LLM agotada: solo si ya hubo pedido explícito en el mensaje
    # (no inventar búsquedas de películas / Wikipedia)
    _ = llm_limitado
    _ = respuesta_previa
    return False


def respuesta_parece_limite_o_vacia(texto: str) -> bool:
    t = (texto or "").strip().lower()
    if not t:
        return True
    if any(m in t for m in _MARCADORES_LIMITE):
        return True
    if "no tengo información" in t or "no tengo datos" in t:
        return True
    return False


def extraer_consulta(mensaje: str) -> str:
    """Limpia el mensaje a una consulta de búsqueda usable."""
    t = (mensaje or "").strip()
    t = re.sub(
        r"(?i)^(busca(r)?\s+(en\s+(internet|la\s+web)\s+)?|search:\s*)",
        "",
        t,
    ).strip(" .:¿?")
    return t[:240] or (mensaje or "").strip()[:240]


def _buscar_tavily(consulta: str, max_results: int = 5) -> dict[str, Any] | None:
    if not TAVILY_API_KEY:
        return None
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": consulta,
                    "search_depth": "basic",
                    "include_answer": True,
                    "max_results": max_results,
                },
            )
            r.raise_for_status()
            data = r.json()
        resultados = []
        for item in data.get("results") or []:
            resultados.append(
                {
                    "titulo": item.get("title") or "",
                    "url": item.get("url") or "",
                    "snippet": (item.get("content") or "")[:400],
                }
            )
        return {
            "motor": "tavily",
            "consulta": consulta,
            "respuesta_directa": (data.get("answer") or "").strip(),
            "resultados": resultados,
        }
    except Exception as exc:
        return {"motor": "tavily", "error": type(exc).__name__, "consulta": consulta}


def _buscar_respaldo(consulta: str) -> dict[str, Any]:
    from cognicion.conectores import (
        consultar_busqueda_web,
        consultar_noticias,
        consultar_wikipedia,
    )

    resultados: list[dict[str, str]] = []
    respuesta_directa = ""
    motor = "duckduckgo"

    wiki = consultar_wikipedia(consulta)
    if wiki and wiki.contexto and "no encontr" not in (wiki.contexto or "").lower():
        motor = "wikipedia"
        cuerpo = wiki.contexto
        if "Instrucción:" in cuerpo:
            cuerpo = cuerpo.split("Instrucción:")[0].strip()
        # Quitar encabezados de conector
        lineas = [
            ln
            for ln in cuerpo.splitlines()
            if ln.strip() and not ln.strip().startswith("[")
        ]
        respuesta_directa = "\n".join(lineas).strip()[:1500]
        resultados.append(
            {
                "titulo": f"Wikipedia: {consulta[:80]}",
                "url": "",
                "snippet": respuesta_directa[:400],
            }
        )

    busq = consultar_busqueda_web(consulta)
    if busq and busq.contexto and "sin resumen instantáneo" not in (busq.contexto or "").lower():
        cuerpo = busq.contexto
        if "Instrucción:" in cuerpo:
            cuerpo = cuerpo.split("Instrucción:")[0].strip()
        if not respuesta_directa:
            respuesta_directa = cuerpo
            motor = "duckduckgo"
        resultados.append(
            {
                "titulo": f"Web: {consulta[:60]}",
                "url": str((busq.metadata or {}).get("busqueda_fuente") or ""),
                "snippet": cuerpo[:400],
            }
        )

    noticias = consultar_noticias(consulta, max_items=4)
    if noticias and noticias.contexto and "sin titulares" not in (noticias.contexto or "").lower():
        if motor == "duckduckgo":
            motor = "duckduckgo+noticias"
        elif motor == "wikipedia":
            motor = "wikipedia+noticias"
        for linea in (noticias.contexto or "").splitlines():
            if re.match(r"^\d+\.", linea.strip()):
                resultados.append(
                    {
                        "titulo": linea.strip()[:160],
                        "url": "",
                        "snippet": linea.strip()[:300],
                    }
                )

    return {
        "motor": motor,
        "consulta": consulta,
        "respuesta_directa": respuesta_directa,
        "resultados": resultados[:6],
        "error": None if (respuesta_directa or resultados) else "sin_resultados",
    }


def buscar_web(consulta: str) -> dict[str, Any]:
    """Ejecuta búsqueda: Tavily si hay clave; si no, DuckDuckGo/noticias."""
    q = extraer_consulta(consulta)
    if not q:
        return {"exito": False, "error": "consulta_vacia", "resultados": []}

    tavily = _buscar_tavily(q)
    if tavily and not tavily.get("error") and (
        tavily.get("respuesta_directa") or tavily.get("resultados")
    ):
        return {"exito": True, **tavily}

    respaldo = _buscar_respaldo(q)
    if tavily and tavily.get("error"):
        respaldo["aviso_tavily"] = tavily["error"]
    respaldo["exito"] = bool(
        respaldo.get("respuesta_directa") or respaldo.get("resultados")
    )
    return respaldo


def resumir_estilo_salomon(
    consulta: str,
    datos: dict[str, Any],
    *,
    hechos_personales: str = "",
    intentar_llm: bool = False,
) -> str:
    """Resume hallazgos con tono elegante; prioriza hechos sobre 'límites de uso'."""
    hallazgos = []
    if datos.get("respuesta_directa"):
        hallazgos.append(str(datos["respuesta_directa"])[:1200])
    for item in datos.get("resultados") or []:
        tit = item.get("titulo") or ""
        sn = item.get("snippet") or ""
        url = item.get("url") or ""
        hallazgos.append(f"- {tit}: {sn}" + (f" ({url})" if url else ""))

    bloque = "\n".join(hallazgos)[:3500] or "(sin hallazgos detallados)"

    if intentar_llm:
        try:
            from cognicion.llm import generar_texto, llm_disponible

            if llm_disponible():
                prompt = f"""Eres Salomón. Estilo: elegante, claro, negro y oro. Español natural.
NO menciones límites de uso, cuotas ni fallos de API.
Presenta lo encontrado en la web de forma útil y breve.

Consulta del usuario: {consulta}

Hallazgos:
{bloque}

Estructura:
1) Apertura corta (1 frase)
2) Lo esencial (3–6 frases o bullets cortos)
3) Cierre con una pregunta suave
Sin meta-comentarios."""
                texto = (generar_texto(prompt) or "").strip()
                if texto and not respuesta_parece_limite_o_vacia(texto):
                    return texto
        except Exception:
            pass

    # Resumen local elegante (rápido, sin depender de cuota LLM)
    lineas = [
        "Consulté fuentes en vivo para darte una respuesta útil.",
        "",
    ]
    if datos.get("respuesta_directa"):
        lineas.append(str(datos["respuesta_directa"]).strip()[:900])
        lineas.append("")
    elif datos.get("resultados"):
        lineas.append("Esto es lo más relevante:")
        for item in (datos.get("resultados") or [])[:4]:
            tit = (item.get("titulo") or "").strip()
            sn = (item.get("snippet") or "").strip()
            if tit or sn:
                lineas.append(f"• {tit or sn[:120]}")
                if tit and sn and sn[:80] not in tit:
                    lineas.append(f"  {sn[:180]}")
        lineas.append("")
    else:
        lineas.append(
            f"No hallé un resumen sólido para «{consulta}». "
            "Puedes afinar la pregunta y lo intento de nuevo."
        )
        lineas.append("")

    motor = datos.get("motor") or "web"
    lineas.append(f"Fuente operativa: {motor}. ¿Quieres que profundice en algún punto?")
    return "\n".join(lineas).strip()


def responder_con_busqueda(
    mensaje: str,
    *,
    hechos_personales: str = "",
) -> dict[str, Any]:
    """Pipeline completo: buscar → resumir estilo Salomón."""
    datos = buscar_web(mensaje)
    texto = resumir_estilo_salomon(
        extraer_consulta(mensaje),
        datos,
        hechos_personales=hechos_personales,
    )
    return {
        "exito": bool(datos.get("exito")),
        "texto": texto,
        "busqueda": datos,
        "motor": datos.get("motor"),
    }
