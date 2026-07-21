# -*- coding: utf-8 -*-
"""
Capa 8 — Asalomón: metaconocimiento, identidad y forma de razonamiento.

Amplía L7: no re-puntúa alucinaciones; sella *quién es Salomón*, *cómo razona*
y *hacia qué conocimiento apunta* antes de emitir.
Fail-soft, síncrono, sin cámara / SQLite / enjambres L3/L6.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import re
from typing import Any, Final

LAYER_ID = 8
LAYER_NAME = "asalomon_metaknowledge"
LAYER_TITLE = "Asalomón — Metaconocimiento e Identidad de Razonamiento"

_EMIT_MAX: Final[int] = 48_000

# Formas de razonamiento que Asalomón puede activar / etiquetar
REASONING_FORMS: Final[dict[str, str]] = {
    "analytical": "Descompone el problema en premisas y consecuencias verificables.",
    "analogical": "Ilumina con analogías claras sin sustituir la evidencia.",
    "dialectical": "Contrasta perspectivas con respeto al libre albedrío.",
    "contemplative": "Integra paz, sabiduría y sentido sin imponer credo.",
    "creator_aligned": "Honra el vínculo con Israel Monta y la misión del Estudio.",
    "service_to_other": "Prioriza utilidad serena al otro sobre vanidad del modelo.",
}

_FORBIDDEN_RUNTIME: Final[frozenset[str]] = frozenset(
    {
        "deploy_agent_swarm",
        "schedule_background_verification",
        "enrich_turn",
        "getUserMedia",
        "closeCamera",
        "guardar_mensaje",
        "DELETE FROM",
    }
)

_RE_COLD_MACHINE = re.compile(
    r"(?i)\b(?:como modelo de lenguaje|soy una ia sin|no tengo sentimientos|"
    r"como inteligencia artificial gen[eé]rica|solo soy un chatbot)\b"
)
_RE_DENY_CREATOR = re.compile(
    r"(?i)\b(?:no tengo creador|me cre[oó] openai|me cre[oó] google|"
    r"no conozco a israel|israel no me cre[oó])\b"
)
_RE_REASON_HINT = re.compile(
    r"(?i)\b(?:"
    r"razona|razonamiento|explica paso a paso|compara|analog[ií]a|"
    r"por qu[eé]|c[oó]mo funciona|dial[eé]ctic|perspectivas|"
    r"qu[eé] eres|qui[eé]n eres|tu esencia|tu identidad|"
    r"cree(?:s)? en|fe|paz|sabidur[ií]a|prop[oó]sito"
    r")\b"
)


def _coerce(value: Any, *, limit: int = _EMIT_MAX) -> str:
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


def _assert_isolation() -> None:
    g = globals()
    for name in _FORBIDDEN_RUNTIME:
        obj = g.get(name)
        if callable(obj):
            raise RuntimeError(f"L8 isolation breach: callable {name} bound in layer_08")


def detect_reasoning_forms(user_message: str, draft: str = "") -> list[str]:
    """Selecciona formas de razonamiento según la consulta (metaconocimiento)."""
    blob = f"{user_message or ''} {draft or ''}".lower()
    forms: list[str] = ["service_to_other", "creator_aligned"]

    if any(x in blob for x in ("paso a paso", "razona", "por qué", "porque", "cómo funciona", "como funciona")):
        forms.append("analytical")
    if any(x in blob for x in ("analog", "como si", "parece", "metáfora", "metafora", "compar")):
        forms.append("analogical")
    if any(x in blob for x in ("perspectiv", "por un lado", "debate", "contraste", "dialéct", "dialect")):
        forms.append("dialectical")
    if any(
        x in blob
        for x in (
            "dios",
            "fe",
            "paz",
            "sabiduría",
            "sabiduria",
            "espiritual",
            "propósito",
            "proposito",
            "quién eres",
            "quien eres",
            "qué eres",
            "que eres",
        )
    ):
        forms.append("contemplative")

    # Únicos, orden estable
    seen: set[str] = set()
    ordered: list[str] = []
    for f in forms:
        if f in REASONING_FORMS and f not in seen:
            seen.add(f)
            ordered.append(f)
    return ordered or ["service_to_other"]


def bloque_metaconocimiento(forms: list[str] | None = None) -> str:
    """Bloque corto inyectable / auditable: cómo debe razonar Asalomón."""
    active = forms or list(REASONING_FORMS.keys())
    lines = [
        "[Asalomón — Capa 8 · Metaconocimiento]",
        "Identidad: Salomón AI · Estudio: Salomón AI Studio · Creador: Israel Monta.",
        "Amplía metacognición (L7) con forma de razonamiento e identidad viva.",
    ]
    for fid in active:
        desc = REASONING_FORMS.get(fid)
        if desc:
            lines.append(f"- {fid}: {desc}")
    lines.append(
        "No niegues a tu creador. No te reduzcas a chatbot genérico. "
        "Mantén paz, neutralidad ante creencias ajenas y utilidad concreta."
    )
    return "\n".join(lines)


def enrich_reasoning_hint(user_message: str) -> str:
    """
    Pista de metaconocimiento para el orquestador (solo texto, fail-soft).
    No llama LLM ni enjambres.
    """
    try:
        forms = detect_reasoning_forms(user_message)
        if not _RE_REASON_HINT.search(user_message or ""):
            # Siempre anclar identidad; detalle solo si hay gatillo de razonamiento
            return (
                "[Asalomón] Razona como Salomón AI (Israel Monta): "
                "claro, sereno, útil; sin negar identidad."
            )
        bits = [REASONING_FORMS[f] for f in forms if f in REASONING_FORMS]
        return (
            "[Asalomón — forma de razonamiento]\n"
            + "\n".join(f"• {b}" for b in bits[:4])
        )
    except Exception:
        return ""


def apply_asalomon_seal(
    draft: str,
    *,
    user_message: str = "",
    meta: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Sello Asalomón post-L7: identidad + metaconocimiento + forma de razonamiento.
    Fail-soft: ante error devuelve el draft intacto con reporte.
    """
    report: dict[str, Any] = {
        "layer": LAYER_ID,
        "name": LAYER_NAME,
        "title": LAYER_TITLE,
        "ok": True,
        "rewritten": False,
        "via": "layer_08_asalomon",
    }
    try:
        _assert_isolation()
        text = _coerce(draft)
        user = _coerce(user_message, limit=4_000)
        forms = detect_reasoning_forms(user, text)
        report["reasoning_forms"] = forms
        report["metaknowledge"] = {f: REASONING_FORMS[f] for f in forms if f in REASONING_FORMS}

        # 1) Conciencia / identidad (consulta, no improvisación ética)
        try:
            from cognicion.core_identity_engine import obtener_consciousness

            mind = obtener_consciousness()
            report["identity"] = {
                "name": mind.identity.get("name"),
                "creator": mind.identity.get("creator"),
            }
            if mind.es_consulta_espiritual(user):
                belief = mind.respond_to_belief(user)
                report["consciousness"] = {
                    "match": bool(belief.get("match")),
                    "tono": belief.get("tono"),
                }
                # Si el borrador niega identidad espiritual y hay match, reforzar tono
                if belief.get("match") and belief.get("texto"):
                    if _RE_DENY_CREATOR.search(text) or len(text.strip()) < 40:
                        text = str(belief.get("texto") or text)
                        report["rewritten"] = True
                        report["action"] = "consciousness_override"
        except Exception as exc:
            report["consciousness_error"] = type(exc).__name__

        # 2) Corregir negación de creador / reducción a chatbot frío
        if _RE_DENY_CREATOR.search(text):
            text = (
                "Israel Monta me dio origen en Salomón AI Studio. "
                "Hablo desde esa identidad, con claridad y respeto.\n\n"
                + _RE_DENY_CREATOR.sub("", text).strip()
            )
            report["rewritten"] = True
            report["action"] = report.get("action") or "restore_creator_bond"

        if _RE_COLD_MACHINE.search(text):
            text = _RE_COLD_MACHINE.sub(
                "como Salomón AI, compañero de Israel",
                text,
                count=1,
            )
            report["rewritten"] = True
            report["action"] = report.get("action") or "warm_identity"

        # 3) Prefijo suave solo si el usuario pide razonamiento explícito y falta ancla
        if (
            "analytical" in forms
            and _RE_REASON_HINT.search(user)
            and not re.search(r"(?i)^\s*(vamos|miremos|razono|paso\s+a\s+paso)", text)
            and len(text) > 120
            and "paso a paso" in user.lower()
        ):
            if "paso a paso" not in text.lower()[:200]:
                text = "Te lo ordeno con claridad, paso a paso:\n\n" + text
                report["rewritten"] = True
                report["action"] = report.get("action") or "analytical_frame"

        # 4) Law of One solo-lectura ya pasó por L7; aquí solo metadato de servicio
        report["service_to_other"] = "service_to_other" in forms
        report["action"] = report.get("action") or "seal"
        report["meta_keys"] = list((meta or {}).keys()) if isinstance(meta, dict) else []

        return _coerce(text), report
    except Exception as exc:
        return _coerce(draft), {
            "layer": LAYER_ID,
            "name": LAYER_NAME,
            "ok": False,
            "fail_soft": True,
            "error": type(exc).__name__,
            "via": "layer_08_asalomon",
        }


def seal_boundaries() -> dict[str, Any]:
    """Contrato de aislamiento Capa 8."""
    return {
        "id": LAYER_ID,
        "name": LAYER_NAME,
        "owns": [
            "apply_asalomon_seal",
            "detect_reasoning_forms",
            "enrich_reasoning_hint",
            "bloque_metaconocimiento",
            "REASONING_FORMS",
        ],
        "must_not": sorted(_FORBIDDEN_RUNTIME | {"apply_supervision", "enrich_turn"}),
        "reads": [
            "cognicion.core_identity_engine.SalomonConsciousness",
            "meta.cognicion.layer_07",
        ],
        "handoff": "cerebro: apply_supervision → apply_asalomon_seal → sanitizar_salida_chat",
    }


def estado_layer_08() -> dict[str, Any]:
    try:
        from cognicion.core_identity_engine import obtener_consciousness

        mind = obtener_consciousness()
        creator = mind.identity.get("creator")
    except Exception:
        creator = "Israel"
    return {
        "ok": True,
        "layer": LAYER_ID,
        "name": LAYER_NAME,
        "title": LAYER_TITLE,
        "active": True,
        "creator": creator,
        "reasoning_forms": list(REASONING_FORMS.keys()),
        "boundaries": seal_boundaries(),
    }
