# -*- coding: utf-8 -*-
"""
Capa 7 — Metacognición y supervisión de emisión.
Evalúa el borrador de respuesta ANTES de emitir (anti-alucinación / confianza).
No re-ejecuta el enjambre L3/L6: solo consume evidencia ya reunida.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import re
from typing import Any

# Fronteras lógicas: L7 NO importa schedule_background_verification ni enrich_turn.
LAYER_ID = 7
LAYER_NAME = "metacognition_supervision"

_RE_AFIRMACION_ABSOLUTA = re.compile(
    r"(?i)\b("
    r"es un hecho|sin duda|definitivamente|siempre es|nunca es|"
    r"garantizo que|100\s*%|absolutamente cierto|como hecho comprobado"
    r")\b"
)
_RE_HECHOS_NUMERICOS = re.compile(
    r"(?i)(\d{1,3}(?:[.,]\d+)?\s*%|"
    r"\b(?:en|el)\s+(?:19|20)\d{2}\b|"
    r"\$\s?\d[\d.,]*|"
    r"\b\d+\s*(?:millones?|billones?)\b)"
)
_RE_HEDGING = re.compile(
    r"(?i)\b("
    r"según|parece|podría|aproximadamente|estimado|no estoy seguro|"
    r"con la información disponible|si no me equivoco|es posible que|"
    r"según fuentes|no encontré|no tengo constancia"
    r")\b"
)
_RE_FUGAS_INTERNAS = re.compile(
    r"(?i)(\[Memoria\s|\[Búsqueda web|\[Contexto personal|"
    r"Pregunta del usuario:|Instrucción:)"
)


def _has_grounding(meta: dict[str, Any] | None) -> bool:
    if not isinstance(meta, dict):
        return False
    cog = meta.get("cognicion") if isinstance(meta.get("cognicion"), dict) else {}
    if cog.get("rag_usado") or cog.get("memory_cortex"):
        return True
    mn = cog.get("master_neural") if isinstance(cog.get("master_neural"), dict) else {}
    if mn.get("swarm"):
        return True
    l6 = cog.get("layer_06") if isinstance(cog.get("layer_06"), dict) else {}
    if l6.get("cached") or (l6.get("result") or {}).get("ok"):
        return True
    if meta.get("busqueda_consultada"):
        return True
    return False


def score_draft(
    draft: str,
    *,
    user_message: str = "",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Puntúa el borrador (0.0–1.0) y lista hallazgos.
    Heurística local: sin LLM extra, sin re-búsqueda.
    """
    text = (draft or "").strip()
    findings: list[dict[str, Any]] = []
    score = 1.0
    grounded = _has_grounding(meta)

    if not text:
        return {
            "ok": False,
            "score": 0.0,
            "confidence": "none",
            "action": "fallback",
            "findings": [{"code": "empty_draft", "severity": "high"}],
            "grounded": grounded,
            "layer": LAYER_ID,
        }

    if _RE_FUGAS_INTERNAS.search(text):
        findings.append({"code": "internal_leak", "severity": "high"})
        score -= 0.35

    abs_hits = len(_RE_AFIRMACION_ABSOLUTA.findall(text))
    num_hits = len(_RE_HECHOS_NUMERICOS.findall(text))
    hedge_hits = len(_RE_HEDGING.findall(text))

    if abs_hits and not grounded:
        findings.append(
            {
                "code": "absolute_without_grounding",
                "severity": "high",
                "count": abs_hits,
            }
        )
        score -= 0.25 * min(abs_hits, 3)

    if num_hits >= 2 and not grounded and hedge_hits == 0:
        findings.append(
            {
                "code": "dense_facts_ungrounded",
                "severity": "medium",
                "count": num_hits,
            }
        )
        score -= 0.2

    if len(text) < 12 and len((user_message or "").strip()) > 40:
        findings.append({"code": "too_short_for_query", "severity": "low"})
        score -= 0.1

    # Preguntas factuales típicas sin grounding → bajar confianza
    q = (user_message or "").lower()
    factual_q = any(
        k in q
        for k in (
            "cuánto",
            "cuanto",
            "quién",
            "quien",
            "cuándo",
            "cuando",
            "dónde",
            "donde",
            "precio",
            "noticia",
            "busca",
            "qué es",
            "que es",
        )
    )
    if factual_q and not grounded and abs_hits + num_hits > 0 and hedge_hits == 0:
        findings.append({"code": "factual_query_ungrounded", "severity": "medium"})
        score -= 0.15

    score = max(0.0, min(1.0, round(score, 3)))
    if score >= 0.85:
        confidence = "high"
        action = "emit"
    elif score >= 0.55:
        confidence = "medium"
        action = "hedge" if findings else "emit"
    else:
        confidence = "low"
        action = "hedge"

    return {
        "ok": True,
        "score": score,
        "confidence": confidence,
        "action": action,
        "findings": findings,
        "grounded": grounded,
        "layer": LAYER_ID,
        "via": "layer_07_metacognition",
    }


_HEDGE_PREFIX = (
    "Con la información disponible en este momento, te respondo con cautela "
    "(sin fuentes frescas que respalden cada detalle):\n\n"
)


def apply_supervision(
    draft: str,
    *,
    user_message: str = "",
    meta: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Puerta de emisión metacognitiva.
    Retorna (texto_ajustado, reporte). Fail-soft: ante error interno no bloquea.
    """
    try:
        report = score_draft(draft, user_message=user_message, meta=meta)
        text = (draft or "").strip()
        action = report.get("action") or "emit"

        if action == "fallback" or not text:
            text = (
                "Israel, no pude validar una respuesta completa. "
                "Reformula la pregunta y la reviso con más cuidado."
            )
            report["rewritten"] = True
        elif action == "hedge" and not text.startswith("Con la información disponible"):
            # Evitar doble hedging si el modelo ya matizó
            if not _RE_HEDGING.search(text[:180]):
                text = _HEDGE_PREFIX + text
                report["rewritten"] = True
            else:
                report["rewritten"] = False
        else:
            report["rewritten"] = False

        report["emitted"] = True
        return text, report
    except Exception as exc:
        return (draft or ""), {
            "ok": False,
            "error": type(exc).__name__,
            "action": "emit",
            "layer": LAYER_ID,
            "fail_soft": True,
        }


def seal_boundaries() -> dict[str, Any]:
    """Documenta fronteras: L7 no compite con L3/L6 swarm."""
    return {
        "layer": LAYER_ID,
        "name": LAYER_NAME,
        "owns": [
            "post_llm_draft_scoring",
            "emit_gate_hedging",
            "anti_hallucination_heuristics",
        ],
        "must_not": [
            "deploy_agent_swarm",
            "schedule_background_verification",
            "enrich_turn",
            "logic_engine_web_gate",
        ],
        "consumes_readonly": [
            "meta.cognicion.master_neural",
            "meta.cognicion.layer_06",
            "meta.cognicion.rag_usado",
            "meta.busqueda_consultada",
        ],
        "handoff": "cerebro.procesar_entrada → apply_supervision → sanitizar_salida_chat",
        "ok": True,
    }


def layer_seven_status() -> dict[str, Any]:
    return {
        "layer": LAYER_ID,
        "name": LAYER_NAME,
        "ok": True,
        "boundaries": seal_boundaries(),
    }
