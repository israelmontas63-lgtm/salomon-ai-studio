"""
Respuesta local — cuando los LLM en la nube fallan por cuota.
Prioriza búsqueda / conectores en vivo; nunca abre con mensajes de límite.
"""

from __future__ import annotations

import re


# Solo hechos presentables al usuario (NUNCA memoria/RAG cruda).
_MARCADORES = (
    "[Datos de clima",
    "[Wikipedia",
    "[Wikidata",
    "[Búsqueda web",
    "[Noticias",
    "[Contexto de visión",
)


def _extraer_pregunta(mensaje: str) -> str:
    if "Pregunta del usuario:" in mensaje:
        return mensaje.split("Pregunta del usuario:")[-1].strip()
    return mensaje.strip()


def _extraer_bloques(mensaje: str) -> list[str]:
    bloques: list[str] = []
    for marcador in _MARCADORES:
        inicio = mensaje.find(marcador)
        if inicio < 0:
            continue
        resto = mensaje[inicio:]
        fin = len(resto)
        for otro in _MARCADORES:
            if otro == marcador:
                continue
            pos = resto.find(otro, len(marcador))
            if pos > 0:
                fin = min(fin, pos)
        if "Pregunta del usuario:" in resto:
            fin = min(fin, resto.find("Pregunta del usuario:"))
        bloque = resto[:fin].strip()
        if bloque and bloque not in bloques:
            bloques.append(bloque)
    return bloques


def _limpiar_bloque(texto: str) -> str:
    lineas = []
    for ln in texto.splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith("Instrucción:"):
            break
        if s.startswith("[") and s.endswith("]"):
            continue
        s = re.sub(r"\s*\(relevancia:\s*[0-9.]+\)", "", s, flags=re.IGNORECASE)
        lineas.append(s)
    return "\n".join(lineas[:14])


def respuesta_local_chat(
    mensaje: str,
    historial: list[dict],
    system_instruction: str = "",
) -> str:
    """Genera respuesta útil sin LLM externo — búsqueda/conectores primero."""
    from settings import BUSQUEDA_WEB_AUTO

    pregunta = _extraer_pregunta(mensaje)
    bloques = [_limpiar_bloque(b) for b in _extraer_bloques(mensaje)]
    bloques = [b for b in bloques if b and "sin resumen instantáneo" not in b.lower()]

    # 1) Si ya hay hechos enriquecidos, presentarlos con estilo (sin hablar de cuota)
    if bloques:
        from cognicion.salida_limpia import sanitizar_salida_chat

        cuerpo = sanitizar_salida_chat("\n\n".join(bloques))
        if cuerpo:
            return (
                f"Israel, esto es lo esencial sobre tu consulta:\n\n"
                f"{cuerpo}\n\n"
                f"Si quieres, profundizo en «{pregunta[:100]}» o busco otro ángulo."
            )

    # 2) Respaldo principal: agente de búsqueda web
    if BUSQUEDA_WEB_AUTO and pregunta:
        try:
            from cognicion.busqueda import responder_con_busqueda

            pack = responder_con_busqueda(pregunta)
            if pack.get("texto"):
                return pack["texto"]
        except Exception:
            pass

    contexto = pregunta
    if not contexto:
        for item in reversed(historial):
            if item.get("role") == "user":
                parts = item.get("parts") or []
                if parts:
                    contexto = str(parts[0]).strip()
                    break
    contexto = re.sub(r"\s+", " ", (contexto or "tu consulta"))[:200]

    return (
        f"Israel, todavía no tengo un resumen sólido para «{contexto}».\n\n"
        "Prueba con una pregunta más concreta, por ejemplo:\n"
        "• «¿Cómo está el clima?»\n"
        "• «Busca en Wikipedia sobre el núcleo de la Tierra»\n"
        "• «Últimas noticias de ciencia»\n\n"
        "Así activo conectores en vivo y te respondo con claridad."
    )
