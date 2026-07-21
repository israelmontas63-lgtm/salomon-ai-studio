# -*- coding: utf-8 -*-
"""
Capa 7 — Metacognición, supervisión y autocorrección (calibrada).
Evalúa el borrador ANTES de emitir. Síncrono, latencia mínima, fail-soft.
No re-ejecuta enjambres L3/L6 ni planificación de fondo.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import re
from typing import Any, Final

LAYER_ID = 7
LAYER_NAME = "metacognition_supervision"

# Ventana máxima de análisis regex (evita coste O(n) en drafts enormes).
_REGEX_WINDOW: Final[int] = 12_000
# Tope duro de salida emitida (protege PWA / TTS).
_EMIT_MAX_CHARS: Final[int] = 48_000

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

# Alternaciones lineales (sin cuantificadores anidados) → O(n) estable en cadenas largas.
_RE_AFIRMACION_ABSOLUTA = re.compile(
    r"(?i)\b(?:"
    r"es un hecho|sin duda|definitivamente|siempre es|nunca es|"
    r"garantizo que|100\s*%|absolutamente cierto|como hecho comprobado|"
    r"te aseguro que|es imposible que no|claramente es"
    r")\b"
)
_RE_HECHOS_NUMERICOS = re.compile(
    r"(?i)(?:\d{1,3}(?:[.,]\d+)?\s*%|"
    r"\b(?:en|el)\s+(?:19|20)\d{2}\b|"
    r"\$\s?\d[\d.,]{0,24}|"
    r"\b\d{1,12}\s*(?:millones?|billones?)\b)"
)
_RE_HEDGING = re.compile(
    r"(?i)\b(?:"
    r"según|parece|podría|aproximadamente|estimado|no estoy seguro|"
    r"con la información disponible|si no me equivoco|es posible que|"
    r"según fuentes|no encontré|no tengo constancia|con cautela"
    r")\b"
)
_RE_FUGAS_INTERNAS = re.compile(
    r"(?i)(?:\[Memoria\s|\[Búsqueda web|\[Contexto personal|"
    r"Pregunta del usuario:|Instrucción:)"
)
_RE_MULTI_NL = re.compile(r"\n{3,}")

# Símbolos prohibidos (deben coincidir con seal_boundaries().must_not).
_FORBIDDEN_RUNTIME: Final[frozenset[str]] = frozenset(
    {
        "deploy_agent_swarm",
        "schedule_background_verification",
        "enrich_turn",
        "logic_engine_web_gate",
    }
)

_HEDGE_PREFIX = (
    "Con la información disponible en este momento, te respondo con cautela "
    "(sin fuentes frescas que respalden cada detalle):\n\n"
)

_FALLBACK_EMIT = (
    "Israel, no pude validar una respuesta completa. "
    "Reformula la pregunta y la reviso con más cuidado."
)


def update_calibration(**kwargs: float) -> dict[str, float]:
    """Ajusta umbrales en caliente (soporte / laboratorio)."""
    for key, value in kwargs.items():
        if key in CALIBRATION:
            try:
                CALIBRATION[key] = float(value)
            except (TypeError, ValueError):
                continue
    return dict(CALIBRATION)


def _coerce_text(value: Any, *, limit: int | None = None) -> str:
    """
    Cemento UTF-8: bytes/surrogates/None → str segura.
    Nunca lanza por encoding; degradación determinista.
    """
    if value is None:
        return ""
    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace")
    elif isinstance(value, str):
        # Fast-path: str UTF-8 válido sin doble encode. Solo repara surrogates/ilegales.
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
        text = text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    if limit is not None and len(text) > limit:
        return text[:limit]
    return text


def _regex_window(text: str) -> str:
    """Recorta el cuerpo analizado para latencia acotada en drafts largos."""
    if len(text) <= _REGEX_WINDOW:
        return text
    half = _REGEX_WINDOW // 2
    return text[:half] + "\n" + text[-half:]


def _count_matches(pattern: re.Pattern[str], text: str, *, cap: int = 8) -> int:
    """Cuenta matches con tope (evita materializar listas enormes)."""
    n = 0
    for _ in pattern.finditer(text):
        n += 1
        if n >= cap:
            break
    return n


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
    """0.0–1.0 según evidencia ya reunida por L2/L3/L6 (solo lectura de meta)."""
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
    """Filtrado ligero de salidas: suaviza absolutos extremos (ventana acotada)."""
    raw = _coerce_text(text)
    if not raw:
        return raw
    if len(raw) <= _REGEX_WINDOW:
        cleaned = _RE_FUGAS_INTERNAS.sub("", raw)
        cleaned = _RE_AFIRMACION_ABSOLUTA.sub("según lo disponible", cleaned)
        return _RE_MULTI_NL.sub("\n\n", cleaned).strip()

    half = _REGEX_WINDOW // 2
    head, mid, tail = raw[:half], raw[half:-half], raw[-half:]
    head = _RE_AFIRMACION_ABSOLUTA.sub(
        "según lo disponible", _RE_FUGAS_INTERNAS.sub("", head)
    )
    tail = _RE_AFIRMACION_ABSOLUTA.sub(
        "según lo disponible", _RE_FUGAS_INTERNAS.sub("", tail)
    )
    return _RE_MULTI_NL.sub("\n\n", f"{head}{mid}{tail}").strip()


def score_draft(
    draft: str,
    *,
    user_message: str = "",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Puntúa el borrador (0.0–1.0) con calibración actual. Síncrono / O(ventana)."""
    text = _coerce_text(draft).strip()
    user_q = _coerce_text(user_message)
    findings: list[dict[str, Any]] = []
    score = 1.0
    grounded = _has_grounding(meta if isinstance(meta, dict) else None)
    g_strength = _grounding_strength(meta if isinstance(meta, dict) else None)
    cal = CALIBRATION
    scan = _regex_window(text)

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

    if _RE_FUGAS_INTERNAS.search(scan):
        findings.append({"code": "internal_leak", "severity": "high"})
        score -= cal["penalty_internal_leak"]

    abs_hits = _count_matches(_RE_AFIRMACION_ABSOLUTA, scan, cap=8)
    num_hits = _count_matches(_RE_HECHOS_NUMERICOS, scan, cap=8)
    hedge_hits = _count_matches(_RE_HEDGING, scan, cap=8)

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

    if len(text) < 12 and len(user_q.strip()) > 40:
        findings.append({"code": "too_short_for_query", "severity": "low"})
        score -= cal["penalty_short"]

    q = user_q.lower()
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
        "scan_chars": len(scan),
    }


def self_reflection_loop(
    draft: str,
    *,
    user_message: str = "",
    meta: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Bucle de autoreflexión síncrono: puntúa → filtra → re-puntúa (máx. N pases).
    Sin I/O de red ni enjambres.
    """
    text = _coerce_text(draft, limit=_EMIT_MAX_CHARS).strip()
    user_q = _coerce_text(user_message, limit=4_000)
    meta_safe = meta if isinstance(meta, dict) else None
    passes: list[dict[str, Any]] = []
    max_passes = max(1, min(int(CALIBRATION.get("max_reflection_passes") or 2), 3))

    report = score_draft(text, user_message=user_q, meta=meta_safe)
    passes.append({"pass": 1, "score": report.get("score"), "action": report.get("action")})

    for i in range(2, max_passes + 1):
        if report.get("action") == "emit" and not report.get("findings"):
            break
        if report.get("action") in ("hedge", "fallback") or report.get("findings"):
            text = filter_hallucination_markers(text)
            report = score_draft(text, user_message=user_q, meta=meta_safe)
            passes.append(
                {"pass": i, "score": report.get("score"), "action": report.get("action")}
            )

    report["reflection_passes"] = passes
    return text, report


def _safe_fail_report(exc: BaseException, *, draft_safe: str) -> tuple[str, dict[str, Any]]:
    """Fallback determinista: nunca pierde la excepción ni rompe la emisión."""
    err_name = type(exc).__name__
    encoding_fail = isinstance(
        exc, (UnicodeError, UnicodeEncodeError, UnicodeDecodeError, ValueError)
    )
    emit = draft_safe if draft_safe else _FALLBACK_EMIT
    return emit, {
        "ok": False,
        "error": err_name,
        "action": "emit",
        "layer": LAYER_ID,
        "fail_soft": True,
        "encoding_fail": encoding_fail,
        "emitted": True,
        "support": "fail_soft_emit_gate",
    }


def _assert_no_forbidden_dispatch() -> None:
    """
    Guardia de aislamiento síncrono: L7 no debe enlazar símbolos L3/L6.
    Verifica el namespace del módulo (no importa orquestador ni cola).
    """
    g = globals()
    for name in _FORBIDDEN_RUNTIME:
        obj = g.get(name)
        if callable(obj):
            raise RuntimeError(f"L7 isolation breach: callable {name} bound in layer_07")


def apply_supervision(
    draft: str,
    *,
    user_message: str = "",
    meta: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Puerta de emisión metacognitiva (síncrona, latencia acotada).
    Fail-soft ante UTF-8 / surrogates / fallos internos: nunca traga la excepción
    sin reporte y nunca invoca L3/L6.
    """
    draft_safe = ""
    try:
        _assert_no_forbidden_dispatch()

        draft_safe = _coerce_text(draft, limit=_EMIT_MAX_CHARS)
        user_safe = _coerce_text(user_message, limit=4_000)
        meta_safe = meta if isinstance(meta, dict) else None

        text, report = self_reflection_loop(
            draft_safe, user_message=user_safe, meta=meta_safe
        )
        action = report.get("action") or "emit"

        if action == "fallback" or not text:
            text = _FALLBACK_EMIT
            report["rewritten"] = True
        elif action == "hedge" and not text.startswith("Con la información disponible"):
            head = text[:180]
            if not _RE_HEDGING.search(head):
                text = _HEDGE_PREFIX + text
                report["rewritten"] = True
            else:
                filtered = filter_hallucination_markers(text)
                report["rewritten"] = filtered != text
                text = filtered
        else:
            report["rewritten"] = False

        text = _coerce_text(text, limit=_EMIT_MAX_CHARS)

        # Canal sináptico law_of_one_lens (unidad / libre albedrío) — fail-soft
        try:
            from cognicion.capas_inteligencia.synaptic_bus import cross_law_of_one

            text, axiom_report = cross_law_of_one(text, user_message=user_safe)
            report["law_of_one"] = axiom_report
            if axiom_report.get("rewritten"):
                report["rewritten"] = True
        except Exception as axiom_exc:
            report["law_of_one"] = {
                "ok": False,
                "error": type(axiom_exc).__name__,
                "fail_soft": True,
            }

        report["emitted"] = True
        report["support"] = "calibrated_self_correction"
        report["isolation"] = "sealed"
        return text, report
    except (UnicodeError, UnicodeEncodeError, UnicodeDecodeError) as exc:
        return _safe_fail_report(exc, draft_safe=draft_safe or _coerce_text(draft))
    except Exception as exc:
        return _safe_fail_report(exc, draft_safe=draft_safe or _coerce_text(draft))


def seal_boundaries() -> dict[str, Any]:
    """Contrato de fronteras: posesión + prohibiciones (fuente de verdad)."""
    must_not = sorted(_FORBIDDEN_RUNTIME)
    call_breaches: list[str] = []
    try:
        with open(__file__, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError:
        src = ""
    # Construir needle en runtime (evita falsos positivos por literales de esta función).
    _lp = chr(40)  # '('
    for name in must_not:
        needle = f"{name}{_lp}"
        if needle not in src:
            continue
        # Breach solo si hay import, binding o llamada cualificada real.
        if (
            f"import {name}" in src
            or f"{name} =" in src
            or f".{name}{_lp}" in src
        ):
            call_breaches.append(name)
    ok = (
        not call_breaches
        and "apply_supervision" in src
        and "self_reflection_loop" in src
        and all(f"{n}{_lp}" not in src for n in must_not if n != "logic_engine_web_gate")
    )
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
        "must_not": must_not,
        "consumes_readonly": [
            "meta.cognicion.master_neural",
            "meta.cognicion.layer_06",
            "meta.cognicion.rag_usado",
            "meta.busqueda_consultada",
        ],
        "handoff": "cerebro.procesar_entrada → apply_supervision → sanitizar_salida_chat",
        "call_breaches": call_breaches,
        "ok": ok,
    }


def layer_seven_status() -> dict[str, Any]:
    boundaries = seal_boundaries()
    return {
        "layer": LAYER_ID,
        "name": LAYER_NAME,
        "ok": bool(boundaries.get("ok")),
        "calibration": dict(CALIBRATION),
        "boundaries": boundaries,
        "regex_window": _REGEX_WINDOW,
        "sync": True,
        "swarm_disabled": True,
    }
