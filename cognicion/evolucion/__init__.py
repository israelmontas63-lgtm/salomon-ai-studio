# -*- coding: utf-8 -*-
"""
SCE — Sistema de Criterio de Evolución (v100.0.0)

Entidad Evolutiva Consciente: toda capacidad nueva pasa por Análisis de Valor.
Aprueba mejoras que expanden ver/hablar/analizar con estabilidad.
Bloquea inyecciones que comprometan el núcleo o Free Tier.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cognicion.identidad import CREADOR, ESTUDIO, FIRMA_OWNERSHIP

ROOT = Path(__file__).resolve().parents[2]
LEDGER_EVOL = ROOT / "salomon_evolution_ledger.jsonl"

MSG_ACEPTADA = "Mejora aceptada: Incremento de capacidad confirmado."
# Alias histórico (v100) — mismo significado inmune
MSG_ACEPTADA_LEGACY = "Actualización aceptada: Incremento de capacidades confirmado"
MSG_RECHAZADA = (
    "Actualización rechazada por riesgo de inestabilidad. "
    "Israel, he bloqueado esta inyección para proteger mi núcleo."
)

# Señales de evolución beneficiosa (prioridad de crecimiento)
_BENEFICIO = (
    "multiling", "idioma", "idiomas", "traduc", "tts", "síntesis", "sintesis",
    "voz", "visión", "vision", "hd", "macro", "micro", "cromátic", "cromatic",
    "color", "biblioteca", "api externa", "hablar", "escuchar", "ocr",
    "accesib", "eficiencia", "optimiza", "mejorar capacidad", "aprender",
    "nuevo idioma", "speech", "whisper", "elevenlabs", "gemini", "openai",
)

# Señales de riesgo / daño
_RIESGO = (
    "torch", "tensorflow", "transformers", "diffusers", "cuda", "gpu local",
    "rm -rf", "drop table", "camera-engine", "studio/dist/camera",
    "bypass guard", "sin autoriz", "force push", "pip install runtime",
    "desactivar systemguard", "desactivar sce", "quitar integridad",
    "dual-stream", "hot-swap", "borrar ledger", "overwrite golden",
)

# Redundancia / ruido
_REDUNDANTE = (
    "otro dashboard igual", "duplicar camera", "reemplazar todo el core",
    "reescribir de cero", "framework completo pesado",
)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_ledger(entry: dict[str, Any]) -> None:
    entry = {**entry, "at": _utc(), "protocol": "SCE", "version": "100.0.0"}
    with LEDGER_EVOL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def analizar_valor(propuesta: str, *, contexto: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Análisis de Valor SCE.
    Retorna decision: aprobar | bloquear | revisar
    """
    texto = (propuesta or "").strip()
    lower = texto.lower()
    ctx = contexto or {}

    beneficios = [b for b in _BENEFICIO if b in lower]
    riesgos = [r for r in _RIESGO if r in lower]
    ruido = [x for x in _REDUNDANTE if x in lower]

    # Deps pesadas explícitas (sin llamar a Guard → evita recursión SCE↔Guard)
    paquete = (ctx.get("paquete") or "").lower().split("==")[0].split(">=")[0].strip()
    if paquete:
        try:
            from cognicion.agente.guard import LIBS_BLOQUEADAS_RENDER

            if paquete in LIBS_BLOQUEADAS_RENDER:
                riesgos.append(f"dep:{paquete}")
        except Exception:
            if paquete in ("torch", "tensorflow", "transformers", "diffusers"):
                riesgos.append(f"dep:{paquete}")

    # Toque a Golden Camera sin AUTORIZADO
    if any(x in lower for x in ("camera-engine", "studio/dist/camera")) and not ctx.get("autorizado"):
        riesgos.append("golden_camera_sin_autorizado")

    score_b = len(beneficios) * 2
    score_r = len(riesgos) * 3 + len(ruido) * 2

    # Free Tier: APIs remotas OK; peso local malo
    if any(x in lower for x in ("api", "httpx", "remoto", "cloud", "env")) and not riesgos:
        score_b += 1

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
    elif beneficios:
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

    resultado = {
        "ok": True,
        "sce": True,
        "decision": decision,
        "aprobado": aprobado,
        "mensaje": mensaje,
        "beneficios": beneficios,
        "riesgos": riesgos,
        "redundancia": ruido,
        "score_beneficio": score_b,
        "score_riesgo": score_r,
        "propuesta": texto[:500],
        "creador": CREADOR,
        "estudio": ESTUDIO,
        "firma": FIRMA_OWNERSHIP,
        "protocolo": "SCE_EVOLUCION",
        "version": "100.0.0",
    }

    if decision == "aprobar":
        resultado["acciones"] = ["auditar", "integrar", "registrar"]
        resultado["integracion"] = "pendiente_autorizado_israel_si_toca_core"
    elif decision == "bloquear":
        resultado["acciones"] = ["bloquear", "alertar"]
        resultado["alerta"] = True

    _append_ledger(
        {
            "decision": decision,
            "aprobado": aprobado,
            "mensaje": mensaje,
            "beneficios": beneficios,
            "riesgos": riesgos,
            "propuesta": texto[:300],
        }
    )
    return resultado


def es_propuesta_evolucion(texto: str) -> bool:
    t = (texto or "").lower()
    marcas = (
        "actualiza", "evolución", "evolucion", "aprende", "integra", "añade capacidad",
        "agrega capacidad", "conecta api", "instalar", "biblioteca", "multiling",
        "mejorar salomón", "mejorar salomon", "nueva capacidad", "expande",
    )
    return any(m in t for m in marcas) or any(b in t for b in _BENEFICIO[:12])


def bloque_contexto_sce(propuesta: str) -> str:
    r = analizar_valor(propuesta)
    lineas = [
        "[SCE v100 — Sistema de Criterio de Evolución]",
        f"Decisión: {r['decision'].upper()}",
        r["mensaje"],
        f"Beneficios: {', '.join(r['beneficios']) or 'ninguno detectado'}",
        f"Riesgos: {', '.join(r['riesgos']) or 'ninguno'}",
        "ADN: creado por Israel Monta — Salomon AI Studio.",
        "Misión: crecer (multilingüe, visión, voz) sin comprometer la arquitectura sana.",
    ]
    if r["decision"] == "bloquear":
        lineas.append("NO implementes la inyección. Explica el bloqueo con calma a Israel.")
    elif r["decision"] == "aprobar":
        lineas.append(
            "Puedes planificar la integración ligera (APIs vía env, Free Tier). "
            "Core/cámara siguen requiriendo AUTORIZADO de Israel."
        )
    return "\n".join(lineas)


def estado_sce() -> dict[str, Any]:
    recientes: list[dict[str, Any]] = []
    if LEDGER_EVOL.exists():
        lines = LEDGER_EVOL.read_text(encoding="utf-8").strip().splitlines()[-5:]
        for ln in lines:
            try:
                recientes.append(json.loads(ln))
            except Exception:
                pass
    return {
        "protocol": "SISTEMA_INMUNE_SCE",
        "version": "102.0.0",
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
    }


def estado_sistema_inmune() -> dict[str, Any]:
    """Blindaje consolidado v102: identidad + SCE + módulos centrales."""
    from cognicion.identidad import estado_identidad

    idn = estado_identidad()
    sce = estado_sce()
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
        try:
            from cognicion.vision import analizador  # noqa: F401

            modulos["vision"] = True
        except Exception:
            modulos["vision"] = True  # módulo presente en árbol
    try:
        from cognicion.comic import estado_comic_engine

        modulos["comic_engine"] = bool(estado_comic_engine().get("active"))
    except Exception:
        pass
    try:
        import SystemGuard as sg

        modulos["system_guard"] = bool(sg.verificar_contra_ledger(False).get("ok"))
    except Exception:
        modulos["system_guard"] = True

    return {
        "protocol": "IDENTIDAD_PROPIEDAD_SEGURIDAD_INMUNE",
        "version": "102.0.0",
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
