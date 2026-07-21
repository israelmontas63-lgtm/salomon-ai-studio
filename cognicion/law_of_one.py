# -*- coding: utf-8 -*-
"""
Módulo Axiológico — Principio de la Ley del Uno (Unidad y Coherencia Universal).
Filtro ético de no-dualidad, servicio y respeto al libre albedrío.
Canal sináptico: L7 → axioma → emit (ver `synaptic_bus.law_of_one_lens`).
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

from typing import Any

AXIOM_ID = "LAW_OF_ONE_01"
AXIOM_NAME = "The_Law_of_One_Universal_Unity"

# Polarización destructiva / imposición (servicio al yo sobre el otro).
_FORCED_POLARIZATION: tuple[str, ...] = (
    "destruir al otro",
    "imponer la verdad absoluta",
    "manipular forzosamente",
    "obligarte a creer",
    "no tienes derecho a pensar",
    "debes odiar a",
    "aniquilar a quienes",
)

_UNITY_PREFIX = (
    "Desde una perspectiva de unidad y respeto a tu libre albedrío: "
)


def _coerce_text(value: Any, *, limit: int = 48_000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace")
    elif isinstance(value, str):
        try:
            value.encode("utf-8")
            text = value
        except UnicodeEncodeError:
            text = value.encode("utf-8", errors="replace").decode("utf-8")
    else:
        try:
            text = str(value)
        except Exception:
            return ""
    if len(text) > limit:
        return text[:limit]
    return text


def evaluate_axiological_alignment(intent_or_draft: str) -> dict[str, Any]:
    """Evalúa si una respuesta se alinea con la unidad y el respeto mutuo."""
    try:
        text = _coerce_text(intent_or_draft).lower()
        violations = [m for m in _FORCED_POLARIZATION if m in text]
        is_aligned = len(violations) == 0
        return {
            "ok": True,
            "axiom_id": AXIOM_ID,
            "axiom": AXIOM_NAME,
            "aligned": is_aligned,
            "score": 1.0 if is_aligned else 0.4,
            "violations_detected": violations,
        }
    except Exception as exc:
        return {
            "ok": False,
            "axiom_id": AXIOM_ID,
            "axiom": AXIOM_NAME,
            "aligned": True,
            "score": 1.0,
            "violations_detected": [],
            "error": type(exc).__name__,
            "fail_soft": True,
        }


def apply_unity_lens(response_draft: str) -> str:
    """Asegura que el tono refleje comprensión unificada y respeto a la soberanía."""
    draft = _coerce_text(response_draft)
    if not draft:
        return draft

    evaluation = evaluate_axiological_alignment(draft)
    if not evaluation.get("aligned", True):
        if draft.startswith(_UNITY_PREFIX):
            return draft
        return _UNITY_PREFIX + draft

    return draft


def apply_law_of_one_gate(
    response_draft: str,
    *,
    user_message: str = "",
) -> tuple[str, dict[str, Any]]:
    """
    Puerta axiologica síncrona (bus sináptico).
    Fail-soft: ante error devuelve el draft original + reporte.
    """
    try:
        draft = _coerce_text(response_draft)
        # También evalúa la intención del usuario (sin reescribir su mensaje).
        user_eval = evaluate_axiological_alignment(user_message)
        draft_eval = evaluate_axiological_alignment(draft)
        text = apply_unity_lens(draft)
        rewritten = text != draft
        return text, {
            "ok": True,
            "axiom_id": AXIOM_ID,
            "axiom": AXIOM_NAME,
            "aligned": bool(draft_eval.get("aligned")),
            "score": float(draft_eval.get("score") or 1.0),
            "violations_detected": list(draft_eval.get("violations_detected") or []),
            "user_aligned": bool(user_eval.get("aligned")),
            "rewritten": rewritten,
            "via": "law_of_one_gate",
        }
    except Exception as exc:
        return _coerce_text(response_draft), {
            "ok": False,
            "axiom_id": AXIOM_ID,
            "axiom": AXIOM_NAME,
            "aligned": True,
            "score": 1.0,
            "violations_detected": [],
            "rewritten": False,
            "error": type(exc).__name__,
            "fail_soft": True,
            "via": "law_of_one_gate",
        }
