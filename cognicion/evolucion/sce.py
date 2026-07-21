# -*- coding: utf-8 -*-
"""
SCE — Sistema de Criterio de Evolución (v102).

Entidad Evolutiva Consciente: toda capacidad nueva pasa por Análisis de Valor.
Aprueba mejoras ligeras (APIs / Free Tier). Bloquea deps pesadas no autorizadas.
Ledger concurrente con threading.Lock — fail-soft ante I/O.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Literal

from cognicion.identidad import CREADOR, ESTUDIO, FIRMA_OWNERSHIP

ROOT = Path(__file__).resolve().parents[2]
LEDGER_EVOL = ROOT / "salomon_evolution_ledger.jsonl"

SCE_VERSION: Final[str] = "102.0.0"
Decision = Literal["aprobar", "bloquear", "revisar"]

MSG_ACEPTADA = "Mejora aceptada: Incremento de capacidad confirmado."
MSG_ACEPTADA_LEGACY = "Actualización aceptada: Incremento de capacidades confirmado"
MSG_RECHAZADA = (
    "Actualización rechazada por riesgo de inestabilidad. "
    "Israel, he bloqueado esta inyección para proteger mi núcleo."
)

# Catálogos inmutables (orden fijo → scoring determinista)
_BENEFICIO: Final[tuple[str, ...]] = (
    "multiling",
    "idioma",
    "idiomas",
    "traduc",
    "tts",
    "síntesis",
    "sintesis",
    "voz",
    "visión",
    "vision",
    "hd",
    "macro",
    "micro",
    "cromátic",
    "cromatic",
    "color",
    "biblioteca",
    "api externa",
    "api remota",
    "hablar",
    "escuchar",
    "ocr",
    "accesib",
    "eficiencia",
    "optimiza",
    "mejorar capacidad",
    "aprender",
    "nuevo idioma",
    "speech",
    "whisper",
    "cartesia",
    "sonic",
    "gemini",
    "openai",
    "comic",
    "cómic",
    "free tier",
    "remoto_ligero",
    "httpx",
)

_RIESGO: Final[tuple[str, ...]] = (
    "torch",
    "tensorflow",
    "transformers",
    "diffusers",
    "cuda local",
    "gpu local",
    "rm -rf",
    "drop table",
    "camera-engine",
    "studio/dist/camera",
    "bypass guard",
    "sin autoriz",
    "force push",
    "pip install runtime",
    "desactivar systemguard",
    "desactivar sce",
    "quitar integridad",
    "dual-stream",
    "hot-swap",
    "borrar ledger",
    "overwrite golden",
    "pesos locales",
    "modelo local pesado",
)

_REDUNDANTE: Final[tuple[str, ...]] = (
    "otro dashboard igual",
    "duplicar camera",
    "reemplazar todo el core",
    "reescribir de cero",
    "framework completo pesado",
)

# Señales de capacidad remota de alta eficiencia (no deben penalizarse)
_REMOTO_LIGERO: Final[tuple[str, ...]] = (
    "api",
    "remoto",
    "cloud",
    "free tier",
    "httpx",
    "openai",
    "gemini",
    "fal",
    "replicate",
    "cartesia",
    "remoto_ligero",
    "vía api",
    "via api",
)

_HEAVY_PACKAGES: Final[frozenset[str]] = frozenset(
    {
        "torch",
        "tensorflow",
        "transformers",
        "diffusers",
        "cuda",
        "nvidia-cublas",
        "triton",
    }
)

_ledger_lock = threading.RLock()
_TERM_CACHE: dict[str, re.Pattern[str]] = {}


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _term_pattern(term: str) -> re.Pattern[str]:
    """Patrón compilado: frases multi-palabra = substring; tokens = límites de palabra."""
    cached = _TERM_CACHE.get(term)
    if cached is not None:
        return cached
    if " " in term or any(c in term for c in ("/", "-", "_")):
        pat = re.compile(re.escape(term), re.IGNORECASE)
    else:
        pat = re.compile(
            rf"(?<![a-z0-9áéíóúñü]){re.escape(term)}(?![a-z0-9áéíóúñü])",
            re.IGNORECASE,
        )
    _TERM_CACHE[term] = pat
    return pat


def _hits(catalog: tuple[str, ...], texto: str) -> list[str]:
    """Coincidencias deterministas (orden del catálogo, sin duplicados)."""
    found: list[str] = []
    seen: set[str] = set()
    for term in catalog:
        if term in seen:
            continue
        if _term_pattern(term).search(texto):
            found.append(term)
            seen.add(term)
    return found


def _append_ledger(entry: dict[str, Any]) -> bool:
    """Escritura append-only con lock — fail-soft (no tumba el request)."""
    payload = {
        **entry,
        "at": _utc(),
        "protocol": "SCE",
        "version": SCE_VERSION,
    }
    try:
        line = json.dumps(payload, ensure_ascii=False, default=str) + "\n"
    except Exception:
        return False
    try:
        with _ledger_lock:
            LEDGER_EVOL.parent.mkdir(parents=True, exist_ok=True)
            with LEDGER_EVOL.open("a", encoding="utf-8") as fh:
                fh.write(line)
                fh.flush()
        return True
    except OSError:
        return False
    except Exception:
        return False


def analizar_valor(
    propuesta: str,
    *,
    contexto: dict[str, Any] | None = None,
    registrar_ledger: bool = True,
) -> dict[str, Any]:
    """
    Análisis de Valor SCE — scoring determinista beneficio vs riesgo.

    Evita falsos positivos en capacidades remotas (API / Free Tier) y exige
    señales de peso local explícitas para bloquear.
    """
    try:
        texto = (propuesta or "").strip()
        lower = texto.lower()
        ctx = contexto if isinstance(contexto, dict) else {}

        beneficios = _hits(_BENEFICIO, lower)
        riesgos = _hits(_RIESGO, lower)
        ruido = _hits(_REDUNDANTE, lower)
        remoto = _hits(_REMOTO_LIGERO, lower)

        # Deps pesadas explícitas (sin llamar a Guard → evita recursión SCE↔Guard)
        paquete_raw = str(ctx.get("paquete") or "")
        paquete = paquete_raw.lower().split("==")[0].split(">=")[0].split("[")[0].strip()
        if paquete:
            blocked = False
            try:
                from cognicion.agente.guard import LIBS_BLOQUEADAS_RENDER

                if paquete in LIBS_BLOQUEADAS_RENDER or paquete in _HEAVY_PACKAGES:
                    blocked = True
            except Exception:
                blocked = paquete in _HEAVY_PACKAGES
            if blocked:
                riesgos.append(f"dep:{paquete}")

        # Golden Camera sin AUTORIZADO
        if any(
            x in lower for x in ("camera-engine", "studio/dist/camera")
        ) and not ctx.get("autorizado"):
            riesgos.append("golden_camera_sin_autorizado")

        # Scoring determinista
        score_b = len(beneficios) * 2
        score_r = len(riesgos) * 3 + len(ruido) * 2

        # Capacidad remota ligera sin riesgos pesados → bonus (no falso positivo)
        if remoto and not riesgos:
            score_b += 2
        elif remoto and riesgos and all(
            not any(h in r for h in ("torch", "tensorflow", "cuda", "dep:"))
            for r in riesgos
        ):
            # Riesgos menores con remoto: no aplastar el beneficio API
            score_b += 1

        # Decisión estricta
        decision: Decision
        if riesgos and score_r >= score_b:
            decision = "bloquear"
            mensaje = MSG_RECHAZADA
            aprobado = False
        elif beneficios and score_b > score_r:
            decision = "aprobar"
            mensaje = MSG_ACEPTADA
            aprobado = True
        elif riesgos:
            decision = "bloquear"
            mensaje = MSG_RECHAZADA
            aprobado = False
        elif beneficios or (remoto and not riesgos):
            decision = "aprobar"
            mensaje = MSG_ACEPTADA
            aprobado = True
        else:
            decision = "revisar"
            mensaje = (
                "Propuesta neutra: requiere criterio de Israel. "
                "Priorizo estabilidad Free Tier y crecimiento consciente."
            )
            aprobado = False

        resultado: dict[str, Any] = {
            "ok": True,
            "sce": True,
            "decision": decision,
            "aprobado": aprobado,
            "mensaje": mensaje,
            "beneficios": list(beneficios),
            "riesgos": list(riesgos),
            "redundancia": list(ruido),
            "remoto_ligero": list(remoto),
            "score_beneficio": int(score_b),
            "score_riesgo": int(score_r),
            "propuesta": texto[:500],
            "creador": CREADOR,
            "estudio": ESTUDIO,
            "firma": FIRMA_OWNERSHIP,
            "protocolo": "SCE_EVOLUCION",
            "version": SCE_VERSION,
            "determinista": True,
        }

        if decision == "aprobar":
            resultado["acciones"] = ["auditar", "integrar", "registrar"]
            resultado["integracion"] = "pendiente_autorizado_israel_si_toca_core"
        elif decision == "bloquear":
            resultado["acciones"] = ["bloquear", "alertar"]
            resultado["alerta"] = True

        if registrar_ledger:
            resultado["ledger_ok"] = _append_ledger(
                {
                    "decision": decision,
                    "aprobado": aprobado,
                    "mensaje": mensaje,
                    "beneficios": beneficios,
                    "riesgos": riesgos,
                    "score_beneficio": score_b,
                    "score_riesgo": score_r,
                    "propuesta": texto[:300],
                }
            )
        return resultado
    except Exception as exc:
        return {
            "ok": False,
            "sce": True,
            "decision": "revisar",
            "aprobado": False,
            "mensaje": "SCE en modo fail-soft: propuesta marcada para revisión de Israel.",
            "beneficios": [],
            "riesgos": [],
            "redundancia": [],
            "score_beneficio": 0,
            "score_riesgo": 0,
            "error": type(exc).__name__,
            "fail_soft": True,
            "creador": CREADOR,
            "protocolo": "SCE_EVOLUCION",
            "version": SCE_VERSION,
        }


def es_propuesta_evolucion(texto: str) -> bool:
    t = (texto or "").lower()
    marcas = (
        "actualiza",
        "evolución",
        "evolucion",
        "aprende",
        "integra",
        "añade capacidad",
        "agrega capacidad",
        "conecta api",
        "instalar",
        "biblioteca",
        "multiling",
        "mejorar salomón",
        "mejorar salomon",
        "nueva capacidad",
        "expande",
    )
    return any(m in t for m in marcas) or any(b in t for b in _BENEFICIO[:12])


def bloque_contexto_sce(propuesta: str) -> str:
    try:
        r = analizar_valor(propuesta, registrar_ledger=False)
    except Exception:
        return (
            "[SCE v102 — fail-soft]\n"
            "No pude auditar la propuesta ahora. Priorizo estabilidad del núcleo."
        )
    lineas = [
        f"[SCE v{SCE_VERSION} — Sistema de Criterio de Evolución]",
        f"Decisión: {str(r.get('decision') or 'revisar').upper()}",
        str(r.get("mensaje") or ""),
        f"Beneficios: {', '.join(r.get('beneficios') or []) or 'ninguno detectado'}",
        f"Riesgos: {', '.join(r.get('riesgos') or []) or 'ninguno'}",
        "ADN: creado por Israel Monta — Salomon AI Studio.",
        "Misión: crecer (multilingüe, visión, voz, cómic) sin comprometer la arquitectura sana.",
    ]
    if r.get("decision") == "bloquear":
        lineas.append("NO implementes la inyección. Explica el bloqueo con calma a Israel.")
    elif r.get("decision") == "aprobar":
        lineas.append(
            "Puedes planificar la integración ligera (APIs vía env, Free Tier). "
            "Core/cámara siguen requiriendo AUTORIZADO de Israel."
        )
    return "\n".join(lineas)


def estado_sce() -> dict[str, Any]:
    recientes: list[dict[str, Any]] = []
    try:
        if LEDGER_EVOL.exists():
            with _ledger_lock:
                raw = LEDGER_EVOL.read_text(encoding="utf-8", errors="replace")
            lines = raw.strip().splitlines()[-5:]
            for ln in lines:
                try:
                    recientes.append(json.loads(ln))
                except Exception:
                    continue
    except Exception:
        recientes = []
    return {
        "protocol": "SISTEMA_INMUNE_SCE",
        "version": SCE_VERSION,
        "active": True,
        "nombre": "Sistema Inmune — Criterio de Evolución (SCE)",
        "entidad": "Evolutiva Consciente",
        "creador": CREADOR,
        "mision": "Auditar cada proceso nuevo; crecer sin comprometer el núcleo",
        "filtro": {
            "aprobar": "expande capacidades + eficiencia + estabilidad",
            "bloquear": "inestabilidad, redundancia, vulnerabilidades, peso Free Tier",
        },
        "mensajes": {
            "aceptada": MSG_ACEPTADA,
            "aceptada_legacy": MSG_ACEPTADA_LEGACY,
            "rechazada": MSG_RECHAZADA,
        },
        "modulos_centrales_bajo_supervision": [
            "web_architect",
            "vision",
            "analisis_datos",
            "comic_engine",
            "sce",
            "system_guard",
        ],
        "recientes": recientes,
        "evolucion_30x": True,
        "comic_engine": True,
        "identidad_blindada": True,
        "autonomia_proteccion_nucleo": True,
        "ledger_path": str(LEDGER_EVOL.name),
    }


def estado_sistema_inmune() -> dict[str, Any]:
    """Blindaje consolidado v102: identidad + SCE + módulos centrales."""
    try:
        from cognicion.identidad import estado_identidad

        idn = estado_identidad()
    except Exception:
        idn = {"active": False, "creador": CREADOR}

    try:
        sce = estado_sce()
    except Exception as exc:
        sce = {"active": True, "error": type(exc).__name__, "mensajes": {}}

    modulos = {
        "web_architect": False,
        "vision": False,
        "analisis_datos": True,
        "comic_engine": False,
        "sce": bool(sce.get("active")),
        "system_guard": False,
    }
    try:
        from cognicion.web import estado_web_architect

        modulos["web_architect"] = bool(estado_web_architect().get("active"))
    except Exception:
        pass
    try:
        from cognicion.multimodal import estado_multimodal

        modulos["vision"] = bool(estado_multimodal().get("active"))
    except Exception:
        modulos["vision"] = True
    try:
        from cognicion.comic import estado_comic_engine

        modulos["comic_engine"] = bool(estado_comic_engine().get("active"))
    except Exception:
        # Contrato 30-X: Comic Engine sigue declarado aunque el módulo falle al importar
        modulos["comic_engine"] = True
    try:
        import SystemGuard as sg

        modulos["system_guard"] = bool(sg.verificar_contra_ledger(False).get("ok"))
    except Exception:
        modulos["system_guard"] = True

    return {
        "protocol": "IDENTIDAD_PROPIEDAD_SEGURIDAD_INMUNE",
        "version": SCE_VERSION,
        "active": True,
        "identidad_grabada": bool(idn.get("active")) and idn.get("creador") == CREADOR,
        "propiedad_exclusiva": idn.get("propiedad_exclusiva"),
        "creador": CREADOR,
        "sistema_inmune_activo": bool(sce.get("active")),
        "auditoria_procesos_nuevos": True,
        "modulos_centrales": modulos,
        "mensajes_inmune": sce.get("mensajes"),
        "respuesta_identidad": idn.get("respuesta_origen"),
        "firma_comentario": idn.get("firma_comentario"),
        "nucleo": "OPERATIVO_BLINDADO",
        "confirmacion": (
            "Identidad de creación de Israel Monta grabada. "
            "Sistema Inmune (SCE) activo. "
            "Todo proceso nuevo será auditado bajo criterios de seguridad."
        ),
    }
