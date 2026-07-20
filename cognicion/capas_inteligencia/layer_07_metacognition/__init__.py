# -*- coding: utf-8 -*-
"""
Capa 7 — Metacognición, supervisión y autocorrección (calibrada).
Evalúa el borrador ANTES de emitir. No re-ejecuta enjambres L3/L6.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import re
from typing import Any

LAYER_ID = 7
LAYER_NAME = "metacognition_supervision"

# Calibración de autocorrección / anti-alucinación (soporte final)
CALIBRATION: dict[str, float] = {
    "emit_min": 0.85,
    "hedge_min": 0.55,
    "penalty_internal_leak": 0.35,
    "penalty_absolute": 0.28,
    "penalty_dense_facts": 0.22,
    "penalty_short": 0.10,
    "penalty_factual_ungrounded": 0.18,
    "grounding_bonus": 0.08,
    "max_reflection_passes": 2,
}

_RE_AFIRMACION_ABSOLUTA = re.compile(
    r"(?i)\b("
    r"es un hecho|sin duda|definitivamente|siempre es|nunca es|"
    r"garantizo que|100\s*%|absolutamente cierto|como hecho comprobado|"
    r"te aseguro que|es imposible que no|claramente es"
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
    r"según fuentes|no encontré|no tengo constancia|con cautela"
    r")\b"
)
_RE_FUGAS_INTERNAS = re.compile(
    r"(?i)(\[Memoria\s|\[Búsqueda web|\[Contexto personal|"
    r"Pregunta del usuario:|Instrucción:)"
)


def update_calibration(**kwargs: float) -> dict[str, float]:
    """Ajusta umbrales en caliente (soporte / laboratorio)."""
    for key, value in kwargs.items():
        if key in CALIBRATION:
            CALIBRATION[key] = float(value)
    return dict(CALIBRATION)


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


def _grounding_strength(meta: dict[str, Any] | None) -> float:
    """0.0–1.0 según evidencia ya reunida por L2/L3/L6."""
    if not isinstance(meta, dict):
        return 0.0
    cog = meta.get("cognicion") if isinstance(meta.get("cognicion"), dict) else {}
    strength = 0.0
    if cog.get("rag_usado"):
        strength += 0.35
    mn = cog.get("master_neural") if isinstance(cog.get("master_neural"), dict) else {}
    if mn.get("swarm"):
        strength += 0.45
    l6 = cog.get("layer_06") if isinstance(cog.get("layer_06"), dict) else {}
    if l6.get("cached") or (l6.get("result") or {}).get("ok"):
        strength += 0.25
    if meta.get("busqueda_consultada"):
        strength += 0.15
    return min(1.0, round(strength, 3))


def filter_hallucination_markers(text: str) -> str:
    """Filtrado ligero de salidas: suaviza absolutos extremos."""
    if not text:
        return text
    out = _RE_FUGAS_INTERNAS.sub("", text)
    out = _RE_AFIRMACION_ABSOLUTA.sub("según lo disponible", out)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out


def score_draft(
    draft: str,
    *,
    user_message: str = "",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Puntúa el borrador (0.0–1.0) con calibración actual."""
    text = (draft or "").strip()
    findings: list[dict[str, Any]] = []
    score = 1.0
    grounded = _has_grounding(meta)
    g_strength = _grounding_strength(meta)
    cal = CALIBRATION

    if not text:
        return {
            "ok": False,
            "score": 0.0,
            "confidence": "none",
            "action": "fallback",
            "findings": [{"code": "empty_draft", "severity": "high"}],
            "grounded": grounded,
            "grounding_strength": g_strength,
            "layer": LAYER_ID,
            "calibration": dict(cal),
        }

    if _RE_FUGAS_INTERNAS.search(text):
        findings.append({"code": "internal_leak", "severity": "high"})
        score -= cal["penalty_internal_leak"]

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
        score -= cal["penalty_absolute"] * min(abs_hits, 3)

    if num_hits >= 2 and not grounded and hedge_hits == 0:
        findings.append(
            {
                "code": "dense_facts_ungrounded",
                "severity": "medium",
                "count": num_hits,
            }
        )
        score -= cal["penalty_dense_facts"]

    if len(text) < 12 and len((user_message or "").strip()) > 40:
        findings.append({"code": "too_short_for_query", "severity": "low"})
        score -= cal["penalty_short"]

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
        score -= cal["penalty_factual_ungrounded"]

    if grounded:
        score = min(1.0, score + cal["grounding_bonus"] * g_strength)

    score = max(0.0, min(1.0, round(score, 3)))
    if score >= cal["emit_min"]:
        confidence = "high"
        action = "emit"
    elif score >= cal["hedge_min"]:
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
        "grounding_strength": g_strength,
        "layer": LAYER_ID,
        "via": "layer_07_metacognition",
        "calibration": dict(cal),
    }


_HEDGE_PREFIX = (
    "Con la información disponible en este momento, te respondo con cautela "
    "(sin fuentes frescas que respalden cada detalle):\n\n"
)


def self_reflection_loop(
    draft: str,
    *,
    user_message: str = "",
    meta: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Bucle de autoreflexión: puntúa → filtra → re-puntúa (máx. N pases).
    """
    text = (draft or "").strip()
    passes: list[dict[str, Any]] = []
    max_passes = int(CALIBRATION.get("max_reflection_passes") or 2)

    report = score_draft(text, user_message=user_message, meta=meta)
    passes.append({"pass": 1, "score": report.get("score"), "action": report.get("action")})

    for i in range(2, max_passes + 1):
        if report.get("action") == "emit" and not report.get("findings"):
            break
        if report.get("action") in ("hedge", "fallback") or report.get("findings"):
            text = filter_hallucination_markers(text)
            report = score_draft(text, user_message=user_message, meta=meta)
            passes.append(
                {"pass": i, "score": report.get("score"), "action": report.get("action")}
            )

    report["reflection_passes"] = passes
    return text, report


def apply_supervision(
    draft: str,
    *,
    user_message: str = "",
    meta: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Puerta de emisión metacognitiva con autoreflexión calibrada."""
    try:
        text, report = self_reflection_loop(
            draft, user_message=user_message, meta=meta
        )
        action = report.get("action") or "emit"

        if action == "fallback" or not text:
            text = (
                "Israel, no pude validar una respuesta completa. "
                "Reformula la pregunta y la reviso con más cuidado."
            )
            report["rewritten"] = True
        elif action == "hedge" and not text.startswith("Con la información disponible"):
            if not _RE_HEDGING.search(text[:180]):
                text = _HEDGE_PREFIX + text
                report["rewritten"] = True
            else:
                # Ya hay hedging: aplicar filtro de absolutos sin prefijo extra
                filtered = filter_hallucination_markers(text)
                report["rewritten"] = filtered != text
                text = filtered
        else:
            report["rewritten"] = False

        report["emitted"] = True
        report["support"] = "calibrated_self_correction"
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
    return {
        "layer": LAYER_ID,
        "name": LAYER_NAME,
        "owns": [
            "post_llm_draft_scoring",
            "emit_gate_hedging",
            "anti_hallucination_heuristics",
            "self_reflection_loop",
            "calibration",
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
        "calibration": dict(CALIBRATION),
        "boundaries": seal_boundaries(),
    }
