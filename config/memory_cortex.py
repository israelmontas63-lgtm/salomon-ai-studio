# -*- coding: utf-8 -*-
"""
Memory Cortex — contexto local / conversación (PWA).

Web SOLO con:
  • frase canónica «Busca en la web sobre …», o
  • origen=agente cuando SBI + MODO_EJECUCION.

Prohíbe alucinación web sin fuente. Alineado con config.providers (estado).
"""

from __future__ import annotations

import re
from typing import Any

# Única familia permitida (pedido explícito de Israel Monta)
_RE_BUSCA_WEB_SOBRE = re.compile(
    r"(?i)\b("
    r"busca\s+en\s+la\s+web\s+sobre|"
    r"buscar\s+en\s+la\s+web\s+sobre|"
    r"busca\s+en\s+internet\s+sobre|"
    r"buscar\s+en\s+internet\s+sobre|"
    r"busca\s+en\s+wikipedia\s+sobre|"
    r"buscar\s+en\s+wikipedia\s+sobre"
    r")\b"
)


def pedido_busqueda_explicito(mensaje: str) -> bool:
    """True únicamente ante «Busca en la web sobre…» (o variante canónica)."""
    t = (mensaje or "").strip()
    if not t:
        return False
    return bool(_RE_BUSCA_WEB_SOBRE.search(t))


def es_saludo_o_charla_simple(mensaje: str) -> bool:
    t = (mensaje or "").strip().lower()
    if not t or len(t) < 3:
        return True
    saludos = (
        "hola",
        "hi",
        "hey",
        "buenas",
        "saludos",
        "qué tal",
        "que tal",
        "cómo estás",
        "como estas",
        "buenos días",
        "buenos dias",
        "buenas tardes",
        "buenas noches",
        "israel",
        "salomón",
        "salomon",
    )
    if t in saludos:
        return True
    return any(t.startswith(s + " ") or t.startswith(s + ",") for s in saludos)


def web_agentes_autorizados() -> bool:
    """
    En modo ejecución + SBI_ENABLED, los agentes pueden usar APIs web.
    El usuario casual sigue pudiendo forzar con «Busca en la web sobre…».
    """
    try:
        from settings import MODO_EJECUCION, SBI_ENABLED

        return bool(MODO_EJECUCION) and bool(SBI_ENABLED)
    except Exception:
        return False


def autoriza_web(consulta: str, *, origen: str = "usuario") -> bool:
    """
    Única puerta de web para orquestador, motor neuronal y periféricos.

    Política absoluta (PWA / identidad Israel):
    - Usuario / chat: SOLO frase canónica «Busca en la web sobre…».
    - Agente: frase canónica, o (origen agente + SBI + MODO_EJECUCION
      + BUSQUEDA_WEB_AUTO) para herramientas deliberadas — nunca heurística
      factual suelta desde el orquestador de chat.
    """
    q = (consulta or "").strip()
    if not q:
        return False
    if pedido_busqueda_explicito(q):
        return True
    origen_l = (origen or "usuario").strip().lower()
    if origen_l not in ("agente", "agent", "swarm", "supervisor", "forzar"):
        return False
    if not web_agentes_autorizados():
        return False
    try:
        from settings import BUSQUEDA_WEB_AUTO

        return bool(BUSQUEDA_WEB_AUTO)
    except Exception:
        return False


def cortex_status() -> dict[str, Any]:
    agentes = web_agentes_autorizados()
    auto = False
    try:
        from settings import BUSQUEDA_WEB_AUTO

        auto = bool(BUSQUEDA_WEB_AUTO)
    except Exception:
        auto = False
    proveedores: dict[str, Any] = {}
    try:
        from config.providers import estado_proveedores

        rep = estado_proveedores()
        proveedores = {
            "llm_disponible": bool(rep.get("llm_disponible")),
            "activo": rep.get("activo") or {},
            "tts": (rep.get("activo") or {}).get("tts"),
            "stt": (rep.get("activo") or {}).get("stt"),
        }
    except Exception as exc:
        proveedores = {"error": type(exc).__name__}

    return {
        "externo_bloqueado": not (agentes and auto),
        "modo": "ejecucion_neuronal" if agentes else "contexto_usuario_y_hilo",
        "web_solo_si": "Busca en la web sobre... (frase_canonica)",
        "web_agentes": agentes,
        "busqueda_web_auto": auto,
        "gate": "autoriza_web",
        "politica": "cortex_absoluto_memoria_antes_que_web",
        "identidad_primaria": "Israel Monta",
        "alucinacion_web": "prohibida_sin_fuente",
        "runtime": "pwa",
        "proveedores": proveedores,
    }
