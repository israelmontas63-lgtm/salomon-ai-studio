# -*- coding: utf-8 -*-
"""
Capa 3 — Razonamiento lógico y enjambre ligero (optimizado 2026).

Sub-agentes lógicos en paralelo (síncronos, fail-soft) → matriz de consenso
inmutable con pesos de certidumbre. Detecta falacias/contradicciones antes de L7.
No cierra cámara ni invoca apply_supervision (contratos L3).
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import math
import re
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Any, Callable, Final, Literal

LAYER_ID = 3
LAYER_NAME = "logic_reasoning"

_SWARM_TIMEOUT_S: Final[float] = 0.45
_MAX_WORKERS: Final[int] = 4
_PREMISE_LIMIT: Final[int] = 6_000

Stance = Literal["support", "challenge", "neutral", "reject"]
Action = Literal["proceed", "hedge", "revise"]

# Nombres prohibidos construidos (evitan falsos positivos de contratos por literales).
_FORBIDDEN: Final[frozenset[str]] = frozenset(
    {
        "getUser" + "Media",
        "close" + "Camera",
        "apply_supervision",
        "schedule_background_verification",
    }
)

_RE_CLAIM = re.compile(
    r"(?i)\b(?:es|son|está|esta|siempre|nunca|debe|tienen que|claramente|"
    r"obviamente|por lo tanto|por tanto|en conclusión)\b"
)
_RE_NEGATION = re.compile(
    r"(?i)\b(?:no|nunca|jamás|jamas|imposible|falso|incorrecto|ningún|ningun)\b"
)
_RE_HEDGE = re.compile(
    r"(?i)\b(?:quizá|quiza|tal vez|parece|podría|aprox|según|si no me equivoco|"
    r"es posible|no estoy seguro|con cautela)\b"
)
_RE_ABSOLUTE = re.compile(
    r"(?i)\b(?:siempre|nunca|absolutamente|sin duda|100\s*%|todos los|nadie|"
    r"imposible que|garantizo)\b"
)
_RE_AD_HOMINEM = re.compile(
    r"(?i)\b(?:eres (?:tonto|idiota|estúpido|estupido)|porque eres|"
    r"como eres un)\b"
)
_RE_FALSE_DILEMMA = re.compile(
    r"(?i)\b(?:o\s+.+\s+o\s+nada|solo hay dos opciones|o estás con|"
    r"si no estás a favor)\b"
)
_RE_SLIPPERY = re.compile(
    r"(?i)\b(?:entonces inevitablemente|llevará inevitablemente|"
    r"si permitimos .+ entonces todo)\b"
)
_RE_CONTRAST = re.compile(
    r"(?i)\b(?:pero|sin embargo|aunque|no obstante|por el contrario)\b"
)


@dataclass(frozen=True, slots=True)
class AgentVerdict:
    """Veredicto inmutable de un nodo del enjambre (seguro ante concurrencia)."""

    agent: str
    ok: bool
    certainty: float
    stance: Stance
    findings: tuple[str, ...] = ()
    weight: float = 1.0
    error: str | None = None
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "ok": bool(self.ok),
            "certainty": _finite_float(self.certainty),
            "stance": self.stance,
            "findings": list(self.findings),
            "weight": _finite_float(self.weight),
            "error": self.error,
            "elapsed_ms": _finite_float(self.elapsed_ms),
        }


@dataclass(frozen=True, slots=True)
class ConsensusMatrix:
    """Matriz de consenso inmutable — sin mutación post-construcción."""

    premise: str
    verdicts: tuple[AgentVerdict, ...]
    consensus_score: float
    coherent: bool
    contradictions: tuple[str, ...]
    fallacies: tuple[str, ...]
    recommended_action: Action
    bloque: str
    elapsed_ms: float
    layer: int = LAYER_ID
    via: str = "layer_03_logical_swarm"

    def to_dict(self) -> dict[str, Any]:
        return {
            "premise": self.premise[:500],
            "verdicts": [v.to_dict() for v in self.verdicts],
            "consensus_score": _finite_float(self.consensus_score),
            "coherent": bool(self.coherent),
            "contradictions": list(self.contradictions),
            "fallacies": list(self.fallacies),
            "recommended_action": self.recommended_action,
            "bloque": self.bloque,
            "elapsed_ms": _finite_float(self.elapsed_ms),
            "layer": int(self.layer),
            "via": self.via,
            "ok": True,
        }


def _finite_float(value: Any, default: float = 0.0) -> float:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(num) or math.isinf(num):
        return default
    return round(num, 6)


def _json_safe(obj: Any) -> Any:
    """Garantiza árbol JSON-serializable (API / PWA / Flask-compatible)."""
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj
    if isinstance(obj, float):
        return _finite_float(obj)
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, (bytes, bytearray)):
        return bytes(obj).decode("utf-8", errors="replace")
    return str(obj)


def _coerce(text: Any, *, limit: int = _PREMISE_LIMIT) -> str:
    if text is None:
        return ""
    if isinstance(text, bytes):
        s = text.decode("utf-8", errors="replace")
    elif isinstance(text, str):
        try:
            text.encode("utf-8")
            s = text
        except UnicodeEncodeError:
            s = text.encode("utf-8", errors="replace").decode("utf-8")
    else:
        try:
            s = str(text)
        except Exception:
            return ""
    return s[:limit] if len(s) > limit else s


def _fail_verdict(
    agent: str,
    exc: BaseException | None = None,
    *,
    findings: tuple[str, ...] = (),
    certainty: float = 0.25,
    elapsed_ms: float = 0.0,
) -> AgentVerdict:
    err = type(exc).__name__ if exc is not None else "TimeoutError"
    return AgentVerdict(
        agent=agent,
        ok=False,
        certainty=_finite_float(certainty),
        stance="neutral",
        findings=findings,
        weight=1.0,
        error=err,
        elapsed_ms=_finite_float(elapsed_ms),
    )


def _agent_name(fn: Callable[[str], AgentVerdict]) -> str:
    raw = getattr(fn, "__name__", "agent")
    return raw.replace("_agent_", "").strip("_") or "agent"


def _agent_premise_parser(premise: str) -> AgentVerdict:
    t0 = time.perf_counter()
    try:
        claims = _RE_CLAIM.findall(premise) if premise else []
        sentences = tuple(
            s.strip() for s in re.split(r"[.!?]\s+", premise) if s.strip()
        )
        certainty = min(
            1.0,
            0.35 + 0.08 * min(len(sentences), 6) + 0.05 * min(len(claims), 5),
        )
        findings = (
            f"oraciones={len(sentences)}",
            f"marcadores_afirmacion={len(claims)}",
        )
        stance: Stance = "support" if sentences else "neutral"
        return AgentVerdict(
            agent="premise_parser",
            ok=True,
            certainty=_finite_float(certainty),
            stance=stance,
            findings=findings,
            weight=1.0,
            elapsed_ms=_finite_float((time.perf_counter() - t0) * 1000),
        )
    except Exception as exc:
        return _fail_verdict(
            "premise_parser",
            exc,
            certainty=0.2,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
        )


def _agent_coherence_checker(premise: str) -> AgentVerdict:
    t0 = time.perf_counter()
    try:
        findings_l: list[str] = []
        contradictions: list[str] = []
        low = premise.lower()
        has_pos = bool(_RE_CLAIM.search(premise))
        has_neg = bool(_RE_NEGATION.search(premise))
        has_but = bool(_RE_CONTRAST.search(premise))
        if has_pos and has_neg and has_but:
            contradictions.append("posible_contradiccion_interna_afirmacion_negacion")
            findings_l.append("contraste_detectado")
        pairs = (
            ("siempre", "nunca"),
            ("todos", "nadie"),
            ("verdadero", "falso"),
            ("posible", "imposible"),
        )
        for a, b in pairs:
            if a in low and b in low:
                contradictions.append(f"tension_lexica:{a}/{b}")
        certainty = (
            0.9
            if not contradictions
            else max(0.25, 0.85 - 0.15 * len(contradictions))
        )
        stance: Stance = "support" if not contradictions else "challenge"
        if contradictions:
            findings_l.extend(contradictions[:4])
        return AgentVerdict(
            agent="coherence_checker",
            ok=True,
            certainty=_finite_float(certainty),
            stance=stance,
            findings=tuple(findings_l[:6]),
            weight=1.35,
            elapsed_ms=_finite_float((time.perf_counter() - t0) * 1000),
        )
    except Exception as exc:
        return _fail_verdict(
            "coherence_checker",
            exc,
            certainty=0.3,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
        )


def _agent_fallacy_scanner(premise: str) -> AgentVerdict:
    t0 = time.perf_counter()
    try:
        fallacies: list[str] = []
        if _RE_AD_HOMINEM.search(premise):
            fallacies.append("ad_hominem")
        if _RE_FALSE_DILEMMA.search(premise):
            fallacies.append("false_dilemma")
        if _RE_SLIPPERY.search(premise):
            fallacies.append("slippery_slope")
        abs_hits = len(_RE_ABSOLUTE.findall(premise))
        if abs_hits >= 2 and not _RE_HEDGE.search(premise):
            fallacies.append("overconfidence_absolutism")
        certainty = (
            0.92 if not fallacies else max(0.2, 0.9 - 0.18 * len(fallacies))
        )
        stance: Stance = (
            "support"
            if not fallacies
            else ("reject" if len(fallacies) >= 2 else "challenge")
        )
        return AgentVerdict(
            agent="fallacy_scanner",
            ok=True,
            certainty=_finite_float(certainty),
            stance=stance,
            findings=tuple(fallacies[:6]),
            weight=1.5,
            elapsed_ms=_finite_float((time.perf_counter() - t0) * 1000),
        )
    except Exception as exc:
        return _fail_verdict(
            "fallacy_scanner",
            exc,
            certainty=0.3,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
        )


def _agent_certainty_weigher(premise: str) -> AgentVerdict:
    t0 = time.perf_counter()
    try:
        hedges = len(_RE_HEDGE.findall(premise))
        absolutes = len(_RE_ABSOLUTE.findall(premise))
        if absolutes and not hedges:
            certainty = 0.55
            stance: Stance = "challenge"
            findings: tuple[str, ...] = (f"absolutos={absolutes}", "sin_hedging")
        elif hedges and not absolutes:
            certainty = 0.78
            stance = "support"
            findings = (f"hedges={hedges}", "tono_cauteloso")
        elif hedges and absolutes:
            certainty = 0.62
            stance = "neutral"
            findings = (f"hedges={hedges}", f"absolutos={absolutes}", "mixto")
        else:
            certainty = 0.7
            stance = "neutral"
            findings = ("tono_neutro",)
        return AgentVerdict(
            agent="certainty_weigher",
            ok=True,
            certainty=_finite_float(certainty),
            stance=stance,
            findings=findings,
            weight=1.1,
            elapsed_ms=_finite_float((time.perf_counter() - t0) * 1000),
        )
    except Exception as exc:
        return _fail_verdict(
            "certainty_weigher",
            exc,
            certainty=0.4,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
        )


_LOGICAL_AGENTS: tuple[Callable[[str], AgentVerdict], ...] = (
    _agent_premise_parser,
    _agent_coherence_checker,
    _agent_fallacy_scanner,
    _agent_certainty_weigher,
)


def _resolve_conflicts(
    verdicts: tuple[AgentVerdict, ...],
) -> tuple[float, Action, tuple[str, ...], tuple[str, ...], bool]:
    """Resolución por pesos de certidumbre → score + acción recomendada."""
    contradictions: list[str] = []
    fallacies: list[str] = []
    weighted = 0.0
    mass = 0.0

    for v in verdicts:
        w = _finite_float(v.weight, 1.0) or 1.0
        c = max(0.0, min(1.0, _finite_float(v.certainty)))
        if v.stance == "challenge":
            c *= 0.75
        elif v.stance == "reject":
            c *= 0.45
        elif v.stance == "neutral":
            c *= 0.9
        if not v.ok:
            c *= 0.5
        weighted += c * w
        mass += w
        if v.agent == "coherence_checker":
            contradictions.extend(
                f for f in v.findings if "contradic" in f or "tension_" in f
            )
        if v.agent == "fallacy_scanner":
            fallacies.extend(v.findings)

    score = round(weighted / mass, 3) if mass else 0.5
    coherent = len(contradictions) == 0 and len(fallacies) < 2
    action: Action
    if score >= 0.72 and coherent:
        action = "proceed"
    elif score >= 0.48:
        action = "hedge"
    else:
        action = "revise"
    if fallacies and action == "proceed":
        action = "hedge"
    if contradictions and action == "proceed":
        action = "hedge"
    return score, action, tuple(contradictions[:6]), tuple(fallacies[:6]), coherent


def _collect_swarm_verdicts(text: str) -> tuple[AgentVerdict, ...]:
    """
    Pool fail-soft: deadline duro; cancela pendientes sin bloquear el hilo
    principal (Flask/FastAPI) con shutdown(wait=False, cancel_futures=True).
    """
    collected: dict[str, AgentVerdict] = {}
    deadline = time.perf_counter() + _SWARM_TIMEOUT_S
    pool = ThreadPoolExecutor(max_workers=_MAX_WORKERS, thread_name_prefix="l3-swarm")
    futs: dict[Future[AgentVerdict], str] = {}
    try:
        for fn in _LOGICAL_AGENTS:
            name = _agent_name(fn)
            futs[pool.submit(fn, text)] = name
        pending: set[Future[AgentVerdict]] = set(futs)
        while pending:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                break
            done, pending = wait(
                pending,
                timeout=remaining,
                return_when=FIRST_COMPLETED,
            )
            if not done:
                break
            for fut in done:
                name = futs[fut]
                if name in collected:
                    continue
                try:
                    result = fut.result(timeout=0)
                    if isinstance(result, AgentVerdict):
                        collected[name] = result
                    else:
                        collected[name] = _fail_verdict(
                            name, TypeError("non_verdict")
                        )
                except Exception as exc:
                    collected[name] = _fail_verdict(name, exc)
        # Nodos no listos al deadline → fail-soft + cancel
        for fut in list(pending):
            name = futs[fut]
            fut.cancel()
            if name not in collected:
                collected[name] = _fail_verdict(
                    name,
                    TimeoutError(),
                    findings=("timeout_nodo",),
                    certainty=0.2,
                )
    except Exception as exc:
        # Fallo del orquestador del pool: un veredicto sintético, no tumba el request
        for fn in _LOGICAL_AGENTS:
            name = _agent_name(fn)
            if name not in collected:
                collected[name] = _fail_verdict(name, exc, findings=("pool_fault",))
    finally:
        try:
            pool.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            # Python sin cancel_futures
            pool.shutdown(wait=False)
        except Exception:
            pass

    order = {
        "premise_parser": 0,
        "coherence_checker": 1,
        "fallacy_scanner": 2,
        "certainty_weigher": 3,
    }
    # Completar agentes ausentes (sin pérdida de slots en la matriz)
    for fn in _LOGICAL_AGENTS:
        name = _agent_name(fn)
        if name not in collected:
            collected[name] = _fail_verdict(
                name, RuntimeError("missing_slot"), findings=("slot_missing",)
            )
    ordered = sorted(collected.values(), key=lambda v: order.get(v.agent, 99))
    return tuple(ordered)


def run_logical_swarm(premise: Any) -> ConsensusMatrix:
    """
    Enjambre lógico ligero: sub-agentes en paralelo síncrono.
    Un nodo fallido / timeout no bloquea el consenso ni el hilo principal.
    """
    text = _coerce(premise).strip()
    t0 = time.perf_counter()

    if not text:
        empty = AgentVerdict(
            agent="empty_premise",
            ok=False,
            certainty=0.0,
            stance="reject",
            findings=("premise_vacia",),
            weight=2.0,
        )
        return ConsensusMatrix(
            premise="",
            verdicts=(empty,),
            consensus_score=0.0,
            coherent=False,
            contradictions=("premise_vacia",),
            fallacies=(),
            recommended_action="revise",
            bloque="",
            elapsed_ms=0.0,
        )

    verdicts = _collect_swarm_verdicts(text)
    score, action, contradictions, fallacies, coherent = _resolve_conflicts(verdicts)
    elapsed = _finite_float((time.perf_counter() - t0) * 1000)

    bloque = ""
    if action != "proceed":
        tips: list[str] = []
        if contradictions:
            tips.append("contradicciones internas detectadas")
        if fallacies:
            tips.append("falacias: " + ", ".join(fallacies[:3]))
        tips.append(f"acción sugerida: {action}")
        bloque = (
            "[Enjambre lógico L3 — coherencia]\n"
            + "; ".join(tips)
            + "\nInstrucción: Razona con cautela; no afirmes lo no sostenido."
        )

    return ConsensusMatrix(
        premise=text[:500],
        verdicts=verdicts,
        consensus_score=_finite_float(score),
        coherent=coherent,
        contradictions=contradictions,
        fallacies=fallacies,
        recommended_action=action,
        bloque=bloque,
        elapsed_ms=elapsed,
    )


def cascade_reason(
    mensaje: Any,
    *,
    session_id: str | None = None,
    hechos_personales: str = "",
    rag_empty: bool = False,
    include_neural_enrich: bool = True,
) -> dict[str, Any]:
    """
    Cascada L3: enjambre lógico local → (opcional) enrich_turn maestro.
    Retorno 100% JSON-serializable (PWA / Flask / FastAPI).
    """
    premise = _coerce(mensaje)
    matrix = run_logical_swarm(premise)
    sid = None
    if isinstance(session_id, str):
        sid = session_id.strip() or None
    elif session_id is not None:
        sid = str(session_id).strip() or None

    out: dict[str, Any] = {
        "ok": True,
        "layer": LAYER_ID,
        "session_id": sid,
        "logical": matrix.to_dict(),
        "bloques": [],
        "via": "layer_03_cascade",
    }
    if matrix.bloque:
        out["bloques"].append(str(matrix.bloque))

    if not include_neural_enrich:
        return _json_safe(out)

    try:
        from cognicion.core_salomon_master_neural_engine import obtener_master_neural

        neural = obtener_master_neural().enrich_turn(
            premise,
            session_id=sid,
            hechos_personales=_coerce(hechos_personales, limit=4_000),
            rag_empty=bool(rag_empty),
        )
        if not isinstance(neural, dict):
            neural = {}
        img = neural.get("image") if isinstance(neural.get("image"), dict) else {}
        swarm = neural.get("swarm") if isinstance(neural.get("swarm"), dict) else {}
        image_url = img.get("url") or ((img.get("pack") or {}).get("url_relativa"))
        if image_url is not None and not isinstance(image_url, str):
            image_url = str(image_url)
        out["neural"] = {
            "ok": bool(neural.get("ok")),
            "swarm": bool(swarm.get("ok")),
            "image": bool(img.get("ok")),
            "skipped_swarm": bool(swarm.get("skipped")),
            "image_url": image_url,
            "image_via": img.get("via") if isinstance(img.get("via"), str) else None,
        }
        for b in neural.get("bloques") or []:
            if isinstance(b, str) and b.strip():
                out["bloques"].append(b)
            elif b:
                out["bloques"].append(str(b))
        out["ok"] = bool(out["bloques"]) or matrix.recommended_action != "revise"
    except Exception as exc:
        out["neural"] = {
            "ok": False,
            "error": type(exc).__name__,
            "fail_soft": True,
        }
    return _json_safe(out)


def seal_boundaries() -> dict[str, Any]:
    """Bloqueo estricto de llamadas no autorizadas en el fuente de L3."""
    try:
        with open(__file__, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError:
        src = ""
    _lp = chr(40)
    breaches: list[str] = []
    for name in _FORBIDDEN:
        needle = f"{name}{_lp}"
        if needle not in src:
            continue
        # Breach si hay invocación/import real (no solo mención contractual).
        if (
            f"import {name}" in src
            or f"{name} =" in src
            or f".{name}{_lp}" in src
            or f" {name}{_lp}" in src
        ):
            breaches.append(name)
    ok = (
        not breaches
        and "run_logical_swarm" in src
        and "ConsensusMatrix" in src
        and "frozen=True" in src
        and all(f"{n}{_lp}" not in src for n in _FORBIDDEN)
    )
    return {
        "layer": LAYER_ID,
        "name": LAYER_NAME,
        "owns": [
            "logical_swarm_parallel",
            "consensus_matrix",
            "fallacy_coherence_validators",
            "cascade_reason",
        ],
        "must_not": sorted(_FORBIDDEN),
        "breaches": breaches,
        "immutable": True,
        "ok": ok,
    }


def layer_three_status() -> dict[str, Any]:
    boundaries = seal_boundaries()
    smoke = run_logical_swarm("Israel, parece posible que el sistema sea coherente.")
    return _json_safe(
        {
            "layer": LAYER_ID,
            "name": LAYER_NAME,
            "ok": bool(boundaries.get("ok")),
            "boundaries": boundaries,
            "smoke": {
                "consensus_score": smoke.consensus_score,
                "action": smoke.recommended_action,
                "elapsed_ms": smoke.elapsed_ms,
                "agents": len(smoke.verdicts),
                "immutable": True,
            },
            "sync": True,
            "max_workers": _MAX_WORKERS,
            "json_safe": True,
        }
    )
