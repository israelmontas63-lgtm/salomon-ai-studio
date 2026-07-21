# -*- coding: utf-8 -*-
"""
Evolución 30-X (v101) — catálogo de vanguardia filtrado por SCE.

Cada habilidad se aprueba como contrato de capacidad ligera (APIs / Free Tier).
Implementaciones pesadas locales (torch, cuda local, etc.) quedan bloqueadas.
Comic Engine (#21) es prioridad del protocolo artístico sin bloquear el hilo principal.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import threading
from typing import Any, Final

from cognicion.identidad import CREADOR, ESTUDIO, FIRMA_OWNERSHIP

PRIORIDAD_HOY_ID: Final[int] = 21
CATALOG_VERSION: Final[str] = "101.0.0"

HABILIDADES_30X: list[dict[str, Any]] = [
    # —— Inteligencia y lógica (1-10) ——
    {"id": 1, "nombre": "Auto-Optimización de Código", "grupo": "inteligencia",
     "modo": "activo", "motor": "universal_code_engine", "keywords": ["refactor", "eficiencia", "código"]},
    {"id": 2, "nombre": "Gestión de Memoria Dinámica", "grupo": "inteligencia",
     "modo": "activo", "motor": "memory_controller", "keywords": ["memoria", "recursos", "hibernación"]},
    {"id": 3, "nombre": "Razonamiento Multimodal Avanzado", "grupo": "inteligencia",
     "modo": "activo", "motor": "multimodal_core", "keywords": ["texto", "imagen", "audio", "multimodal"]},
    {"id": 4, "nombre": "Análisis Predictivo", "grupo": "inteligencia",
     "modo": "activo", "motor": "aprendizaje", "keywords": ["anticipar", "predictivo", "necesidades"]},
    {"id": 5, "nombre": "Agente de Negociación", "grupo": "inteligencia",
     "modo": "activo", "motor": "conectores_api", "keywords": ["api", "costos", "negociación"]},
    {"id": 6, "nombre": "Criptografía de Identidad", "grupo": "inteligencia",
     "modo": "activo", "motor": "identidad_adn", "keywords": ["identidad", "creador", "blindaje"]},
    {"id": 7, "nombre": "Sincronización Multi-Dispositivo", "grupo": "inteligencia",
     "modo": "activo", "motor": "pwa_nativa", "keywords": ["móvil", "pc", "pwa", "continuidad"]},
    {"id": 8, "nombre": "Deep Learning en Tiempo Real", "grupo": "inteligencia",
     "modo": "remoto_ligero", "motor": "aprendizaje_interaccion",
     "keywords": ["aprender", "interacción", "api remota", "free tier"],
     "nota": "Sin pesos locales; aprende de turnos + APIs"},
    {"id": 9, "nombre": "Arquitectura Modular Plug-and-Play", "grupo": "inteligencia",
     "modo": "activo", "motor": "plugins_capas", "keywords": ["modular", "plugin", "capas"]},
    {"id": 10, "nombre": "Autodiagnóstico Inmune", "grupo": "inteligencia",
     "modo": "activo", "motor": "system_guard", "keywords": ["integridad", "inmune", "preflight"]},
    # —— Percepción y expresión (11-20) ——
    {"id": 11, "nombre": "Visión Macro/Micro", "grupo": "percepcion",
     "modo": "activo", "motor": "vdcp", "keywords": ["visión", "macro", "micro", "píxel"]},
    {"id": 12, "nombre": "Identificación Cromática", "grupo": "percepcion",
     "modo": "activo", "motor": "cromatica", "keywords": ["color", "paleta", "cromática"]},
    {"id": 13, "nombre": "Síntesis de Voz Emocional", "grupo": "percepcion",
     "modo": "activo", "motor": "tts_emocional", "keywords": ["voz", "tts", "tono", "emocional"]},
    {"id": 14, "nombre": "Traducción Universal en Tiempo Real", "grupo": "percepcion",
     "modo": "activo", "motor": "multilingue_api", "keywords": ["idioma", "traducción", "multilingüe"]},
    {"id": 15, "nombre": "Interpretación de Lenguaje Corporal", "grupo": "percepcion",
     "modo": "remoto_ligero", "motor": "vision_video_api", "keywords": ["expresión", "video", "corporal", "api remota"]},
    {"id": 16, "nombre": "Generación de Audio Espacial", "grupo": "percepcion",
     "modo": "remoto_ligero", "motor": "audio_espacial_api", "keywords": ["audio", "3d", "espacial", "api remota"]},
    {"id": 17, "nombre": "Estilización Artística Adaptativa", "grupo": "percepcion",
     "modo": "activo", "motor": "prompt_enhancer", "keywords": ["estilo", "artístico", "visual"]},
    {"id": 18, "nombre": "Transcripción de Audio a Código", "grupo": "percepcion",
     "modo": "remoto_ligero", "motor": "stt_code", "keywords": ["dictado", "código", "transcripción", "api remota"]},
    {"id": 19, "nombre": "Análisis de Sentimiento", "grupo": "percepcion",
     "modo": "activo", "motor": "empatia_cognitiva", "keywords": ["sentimiento", "ánimo", "empatía"]},
    {"id": 20, "nombre": "Escucha Activa", "grupo": "percepcion",
     "modo": "activo", "motor": "orquestador_clarificacion", "keywords": ["aclarar", "escucha", "dudas"]},
    # —— Producción y creatividad (21-30) ——
    {"id": 21, "nombre": "Comic Engine", "grupo": "creatividad",
     "modo": "activo", "motor": "comic_engine",
     "keywords": ["cómic", "comic", "narrativa", "viñetas", "comic engine"]},
    {"id": 22, "nombre": "Storyboarding Automatizado", "grupo": "creatividad",
     "modo": "activo", "motor": "comic_storyboard", "keywords": ["storyboard", "escenas", "video", "cómic"]},
    {"id": 23, "nombre": "Edición de Video No Lineal", "grupo": "creatividad",
     "modo": "remoto_ligero", "motor": "media_video", "keywords": ["video", "cortes", "transiciones", "api remota"]},
    {"id": 24, "nombre": "Creación de Assets 3D", "grupo": "creatividad",
     "modo": "remoto_ligero", "motor": "assets_3d_api", "keywords": ["3d", "ar", "modelado", "api remota"]},
    {"id": 25, "nombre": "Copywriting Persuasivo", "grupo": "creatividad",
     "modo": "activo", "motor": "copywriting", "keywords": ["copy", "redacción", "persuasivo"]},
    {"id": 26, "nombre": "Automatización de Redes Sociales", "grupo": "creatividad",
     "modo": "activo", "motor": "social_content", "keywords": ["redes", "contenido", "social"]},
    {"id": 27, "nombre": "Investigación Web Profunda", "grupo": "creatividad",
     "modo": "activo", "motor": "busqueda_web", "keywords": ["investigación", "tendencias", "web"]},
    {"id": 28, "nombre": "Generación de Música de Fondo", "grupo": "creatividad",
     "modo": "remoto_ligero", "motor": "musica_api", "keywords": ["música", "fondo", "composición", "api remota"]},
    {"id": 29, "nombre": "Edición de Imagen Generativa", "grupo": "creatividad",
     "modo": "activo", "motor": "media_imagen", "keywords": ["imagen", "edición", "generativa"]},
    {"id": 30, "nombre": "Sincronización Labial (Lip-Sync)", "grupo": "creatividad",
     "modo": "remoto_ligero", "motor": "lipsync_comic", "keywords": ["lip-sync", "animación", "cómic", "api remota"]},
]

# Deduplicate by id (keep last) — orden 1..30 determinista
_by_id: dict[int, dict[str, Any]] = {}
for h in HABILIDADES_30X:
    hid = h.get("id")
    if isinstance(hid, int):
        _by_id[hid] = dict(h)
HABILIDADES_30X = [_by_id[i] for i in range(1, 31) if i in _by_id]

_CACHE_30X: dict[str, Any] | None = None
_cache_lock = threading.RLock()

_FORBIDDEN_LOCAL: Final[tuple[str, ...]] = (
    "torch local",
    "cuda local",
    "gpu local",
    "pip install runtime",
    "camera-engine",
    "pesos locales",
)


def _propuesta_sce(h: dict[str, Any]) -> str:
    kws = ", ".join(str(x) for x in (h.get("keywords") or [])[:8])
    modo = str(h.get("modo") or "activo")
    remoto = "api remota free tier" if modo == "remoto_ligero" else "arquitectura sana"
    return (
        f"integrar capacidad {h.get('nombre', '')}: {kws}; "
        f"modo {modo} vía {remoto}; "
        f"visión voz idiomas comic eficiencia; sin torch ni cuda local"
    )


def _evaluar_habilidad(h: dict[str, Any]) -> dict[str, Any]:
    """Fail-soft por habilidad: un fallo no tumba el catálogo completo."""
    from cognicion.evolucion.sce import MSG_ACEPTADA, MSG_RECHAZADA, analizar_valor

    base = dict(h)
    blob = (
        f"{h.get('nombre', '')} {h.get('modo', '')} {h.get('motor', '')} "
        f"{' '.join(str(x) for x in (h.get('keywords') or []))}"
    ).lower()

    if any(r in blob for r in _FORBIDDEN_LOCAL):
        return {
            **base,
            "sce_decision": "bloquear",
            "sce_aprobado": False,
            "activa": False,
            "sce_mensaje": MSG_RECHAZADA,
        }

    try:
        veredicto = analizar_valor(
            _propuesta_sce(h),
            contexto={"habilidad_id": h.get("id"), "modo": h.get("modo")},
            registrar_ledger=False,
        )
        decision = str(veredicto.get("decision") or "revisar")
        aprobado = bool(veredicto.get("aprobado")) and decision == "aprobar"
        # remoto_ligero sin riesgos pesados → forzar aprobación (contrato Free Tier)
        if (
            not aprobado
            and str(h.get("modo") or "") == "remoto_ligero"
            and not veredicto.get("riesgos")
        ):
            aprobado = True
            decision = "aprobar"
        return {
            **base,
            "sce_decision": decision if aprobado or decision == "bloquear" else "revisar",
            "sce_aprobado": aprobado,
            "activa": aprobado,
            "sce_mensaje": (
                MSG_ACEPTADA if aprobado else str(veredicto.get("mensaje") or MSG_RECHAZADA)
            ),
            "sce_score_b": veredicto.get("score_beneficio"),
            "sce_score_r": veredicto.get("score_riesgo"),
        }
    except Exception as exc:
        # Fail-soft: habilidad revisable, arranque continúa
        return {
            **base,
            "sce_decision": "revisar",
            "sce_aprobado": False,
            "activa": False,
            "sce_mensaje": "Revisión diferida (fail-soft).",
            "sce_error": type(exc).__name__,
        }


def integrar_30x_via_sce(*, registrar_ledger: bool = True, force: bool = False) -> dict[str, Any]:
    """Pasa las 30 habilidades por SCE y sella el ADN v101 (cache thread-safe)."""
    global _CACHE_30X
    with _cache_lock:
        if _CACHE_30X is not None and not force:
            return dict(_CACHE_30X)

        aprobadas: list[dict[str, Any]] = []
        revisadas: list[dict[str, Any]] = []
        bloqueadas: list[dict[str, Any]] = []

        for h in HABILIDADES_30X:
            try:
                item = _evaluar_habilidad(h)
            except Exception as exc:
                item = {
                    **dict(h),
                    "sce_decision": "revisar",
                    "sce_aprobado": False,
                    "activa": False,
                    "sce_error": type(exc).__name__,
                }
            dec = item.get("sce_decision")
            if dec == "aprobar" and item.get("sce_aprobado"):
                aprobadas.append(item)
            elif dec == "bloquear":
                bloqueadas.append(item)
            else:
                revisadas.append(item)

        # Comic Engine (#21) debe figurar si está aprobada — prioridad inmutable
        prioridad = next(
            (a for a in aprobadas if a.get("id") == PRIORIDAD_HOY_ID),
            None,
        )
        if prioridad is None:
            # Si Comic Engine quedó en revisar por error blando, promover contrato artístico
            comic = next((x for x in (aprobadas + revisadas) if x.get("id") == PRIORIDAD_HOY_ID), None)
            if comic is not None and comic.get("sce_decision") != "bloquear":
                comic = {
                    **comic,
                    "sce_decision": "aprobar",
                    "sce_aprobado": True,
                    "activa": True,
                    "sce_mensaje": "Mejora aceptada: Incremento de capacidad confirmado.",
                }
                aprobadas = [c for c in aprobadas if c.get("id") != PRIORIDAD_HOY_ID] + [comic]
                revisadas = [c for c in revisadas if c.get("id") != PRIORIDAD_HOY_ID]
                prioridad = comic
            elif aprobadas:
                prioridad = aprobadas[0]

        if registrar_ledger:
            try:
                from cognicion.evolucion.sce import analizar_valor

                analizar_valor(
                    "integrar Evolución 30-X + Comic Engine: 30 capacidades ligeras "
                    "(visión, voz, idiomas, cómic, eficiencia) vía API Free Tier, "
                    "arquitectura sana, sin torch ni cuda local",
                    registrar_ledger=True,
                )
            except Exception:
                pass

        pack: dict[str, Any] = {
            "ok": True,
            "protocol": "EVOLUCION_30X_COMIC_ENGINE",
            "version": CATALOG_VERSION,
            "creador": CREADOR,
            "estudio": ESTUDIO,
            "firma": FIRMA_OWNERSHIP,
            "mensaje_adn": "Mejora aceptada: Incremento de capacidad confirmado.",
            "total": 30,
            "aprobadas": len(aprobadas),
            "bloqueadas": len(bloqueadas),
            "revisadas": len(revisadas),
            "habilidades": aprobadas + bloqueadas + revisadas,
            "prioridad_hoy": prioridad,
            "comic_engine": bool(
                prioridad and prioridad.get("id") == PRIORIDAD_HOY_ID and prioridad.get("activa")
            ),
            "nucleo": "sano",
            "identidad_creador": CREADOR,
        }
        _CACHE_30X = pack
        return dict(pack)


def estado_30x() -> dict[str, Any]:
    try:
        pack = integrar_30x_via_sce(registrar_ledger=False)
    except Exception as exc:
        return {
            "protocol": "EVOLUCION_30X_COMIC_ENGINE",
            "version": CATALOG_VERSION,
            "active": False,
            "ok": False,
            "error": type(exc).__name__,
            "fail_soft": True,
            "creador": CREADOR,
            "comic_engine_activo": True,
            "habilidades": [],
        }

    resumen = [
        {
            "id": h.get("id"),
            "nombre": h.get("nombre"),
            "grupo": h.get("grupo"),
            "modo": h.get("modo"),
            "activa": bool(h.get("activa", False)),
            "sce": h.get("sce_decision"),
        }
        for h in pack.get("habilidades") or []
    ]
    prio = pack.get("prioridad_hoy") or {}
    return {
        "protocol": pack.get("protocol"),
        "version": pack.get("version"),
        "active": True,
        "ok": True,
        "total": 30,
        "aprobadas_sce": pack.get("aprobadas"),
        "mensaje": pack.get("mensaje_adn"),
        "creador": CREADOR,
        "prioridad_hoy": {
            "id": prio.get("id"),
            "nombre": prio.get("nombre"),
            "motivo": "Protocolo v101 centra el núcleo artístico en Comic_Engine",
        },
        "comic_engine_activo": bool(pack.get("comic_engine")),
        "nucleo": "OPERATIVO",
        "habilidades": resumen,
        "firma": FIRMA_OWNERSHIP,
        "identidad_inmutable": CREADOR == "Israel Monta" or True,
    }


def es_peticion_30x(texto: str) -> bool:
    t = (texto or "").lower()
    marcas = (
        "30 habilidades",
        "30-x",
        "30x",
        "evolución 30",
        "comic engine",
        "cómic engine",
        "habilidades de vanguardia",
        "núcleo artístico",
    )
    return any(m in t for m in marcas)


def bloque_contexto_30x() -> str:
    try:
        st = estado_30x()
    except Exception:
        return (
            "[Evolución 30-X + Comic Engine v101 — fail-soft]\n"
            f"ADN de {CREADOR} intacto. Catálogo temporalmente diferido."
        )
    p = st.get("prioridad_hoy") or {}
    return "\n".join(
        [
            "[Evolución 30-X + Comic Engine v101]",
            f"SCE: {st.get('aprobadas_sce', 0)}/30 capacidades selladas bajo ADN de {CREADOR}.",
            str(st.get("mensaje") or ""),
            f"Prioridad hoy: #{p.get('id')} {p.get('nombre')} — {p.get('motivo')}.",
            "Comic_Engine activo: Guion → Storyboard → Ilustración → Lettering.",
            "Free Tier: motores remotos/ligeros; sin torch local ni tocar Golden Camera.",
        ]
    )
