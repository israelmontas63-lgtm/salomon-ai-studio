# -*- coding: utf-8 -*-
"""
Estado Vivo — puente de integridad entre agentes y el núcleo (cerebro).

Garantiza que rutas paralelas (Fase 1, orquesta) usen la misma
INSTRUCCION_SISTEMA HD Cognitiva que /api/chat.
"""

from __future__ import annotations


def instruccion_sistema() -> str:
    """Personalidad operativa canónica (cerebro)."""
    from cerebro import SalomonAI

    return SalomonAI.INSTRUCCION_SISTEMA


_INFRA_LEAK = (
    "motor en la nube",
    "cuota",
    "respaldo local",
    "intenta en unos minutos",
    "límite de uso",
    "limite de uso",
)


def _es_saludo(texto: str) -> bool:
    t = (texto or "").strip().lower()
    if not t or len(t) > 80:
        return False
    claves = (
        "hola", "hi", "hey", "buenas", "saludos", "buenos días", "buenos dias",
        "buenas tardes", "buenas noches", "qué tal", "que tal", "cómo estás",
        "como estas",
    )
    return any(t == k or t.startswith(k + " ") or t.startswith(k + ",") for k in claves)


def _sin_fuga_infra(texto: str) -> bool:
    baja = (texto or "").lower()
    return not any(x in baja for x in _INFRA_LEAK)


def responder_con_nucleo(
    mensaje: str,
    *,
    contexto: str = "",
    historial: list[dict] | None = None,
) -> str:
    """
    Respuesta unificada bajo INSTRUCCION_SISTEMA.
    Si el LLM no está disponible, devolución local sobria.
    """
    from cognicion.llm import chat_con_historial, llm_disponible
    from cognicion.salida_limpia import sanitizar_salida_chat

    msg = (mensaje or "").strip()
    if not msg:
        return (
            "Israel, aquí estoy. Cuando quieras, entramos al punto — "
            "una sola línea de pensamiento, sin ruido."
        )

    # Saludos cortos: voz HD Cognitiva local (evita fugas de infraestructura)
    if _es_saludo(msg) and not contexto.strip():
        return (
            "Israel, aquí estoy. Mientras afinaba el hilo, dejé listo el ritmo "
            "de hoy. Cuando quieras, entramos directo a lo que importa."
        )

    prompt = msg
    if contexto.strip():
        prompt = (
            f"{msg}\n\n[Contexto interno — no lo cites como lista]\n"
            f"{contexto.strip()[:3500]}"
        )

    if llm_disponible():
        try:
            texto = chat_con_historial(
                prompt,
                historial or [],
                instruccion_sistema(),
            )
            if (texto or "").strip() and _sin_fuga_infra(texto):
                return sanitizar_salida_chat(texto.strip())
        except Exception:
            pass

    # Fallback local: tono HD Cognitiva, sin voz de “equipo” ni infra
    return sanitizar_salida_chat(
        f"Israel, te escucho. Sobre «{mensaje.strip()[:120]}»: "
        "déjame el ángulo exacto y lo trabajo con una sola línea de pensamiento."
    )
