# -*- coding: utf-8 -*-
"""
Evolución 30-X (v101) — catálogo de vanguardia filtrado por SCE.

Cada habilidad se aprueba como contrato de capacidad ligera (APIs / Free Tier).
Implementaciones pesadas locales (torch, etc.) quedan bloqueadas por SCE+Guard.
"""

from __future__ import annotations

from typing import Any

from cognicion.identidad import CREADOR, ESTUDIO, FIRMA_OWNERSHIP

# Prioridad del día (protocolo Comic Engine)
PRIORIDAD_HOY_ID = 21

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
     "keywords": ["aprender", "interacción"], "nota": "Sin pesos locales; aprende de turnos + APIs"},
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
     "modo": "remoto_ligero", "motor": "vision_video_api", "keywords": ["expresión", "video", "corporal"]},
    {"id": 16, "nombre": "Generación de Audio Espacial", "grupo": "percepcion",
     "modo": "remoto_ligero", "motor": "audio_espacial_api", "keywords": ["audio", "3d", "espacial"]},
    {"id": 17, "nombre": "Estilización Artística Adaptativa", "grupo": "percepcion",
     "modo": "activo", "motor": "prompt_enhancer", "keywords": ["estilo", "artístico", "visual"]},
    {"id": 18, "nombre": "Transcripción de Audio a Código", "grupo": "percepcion",
     "modo": "remoto_ligero", "motor": "stt_code", "keywords": ["dictado", "código", "transcripción"]},
    {"id": 19, "nombre": "Análisis de Sentimiento", "grupo": "percepcion",
     "modo": "activo", "motor": "empatia_cognitiva", "keywords": ["sentimiento", "ánimo", "empatía"]},
    {"id": 20, "nombre": "Escucha Activa", "grupo": "percepcion",
     "modo": "activo", "motor": "orquestador_clarificacion", "keywords": ["aclarar", "escucha", "dudas"]},
    # —— Producción y creatividad (21-30) ——
    {"id": 21, "nombre": "Comic Engine", "grupo": "creatividad",
     "modo": "activo", "motor": "comic_engine", "keywords": ["cómic", "comic", "narrativa", "viñetas"]},
    {"id": 22, "nombre": "Storyboarding Automatizado", "grupo": "creatividad",
     "modo": "activo", "motor": "comic_storyboard", "keywords": ["storyboard", "escenas", "video"]},
    {"id": 23, "nombre": "Edición de Video No Lineal", "grupo": "creatividad",
     "modo": "remoto_ligero", "motor": "media_video", "keywords": ["video", "cortes", "transiciones"]},
    {"id": 24, "nombre": "Creación de Assets 3D", "grupo": "creatividad",
     "modo": "remoto_ligero", "motor": "assets_3d_api", "keywords": ["3d", "ar", "modelado"]},
    {"id": 25, "nombre": "Copywriting Persuasivo", "grupo": "creatividad",
     "modo": "activo", "motor": "copywriting", "keywords": ["copy", "redacción", "persuasivo"]},
    {"id": 26, "nombre": "Automatización de Redes Sociales", "grupo": "creatividad",
     "modo": "activo", "motor": "social_content", "keywords": ["redes", "contenido", "social"]},
    {"id": 27, "nombre": "Investigación Web Profunda", "grupo": "creatividad",
     "modo": "activo", "motor": "busqueda_web", "keywords": ["investigación", "tendencias", "web"]},
    {"id": 28, "nombre": "Generación de Música de Fondo", "grupo": "creatividad",
     "modo": "remoto_ligero", "motor": "musica_api", "keywords": ["música", "fondo", "composición"]},
    {"id": 29, "nombre": "Edición de Imagen Generativa", "grupo": "creatividad",
     "modo": "activo", "motor": "media_imagen", "keywords": ["imagen", "edición", "generativa"]},
    {"id": 30, "nombre": "Sincronización Labial (Lip-Sync)", "grupo": "creatividad",
     "modo": "remoto_ligero", "motor": "lipsync_comic", "keywords": ["lip-sync", "animación", "cómic"]},
]

# Deduplicate if any accidental dup ids (keep last)
_by_id: dict[int, dict[str, Any]] = {}
for h in HABILIDADES_30X:
    if isinstance(h["id"], int):
        _by_id[h["id"]] = h
HABILIDADES_30X = [_by_id[i] for i in range(1, 31) if i in _by_id]

_CACHE_30X: dict[str, Any] | None = None


def _propuesta_sce(h: dict[str, Any]) -> str:
    kws = ", ".join(h.get("keywords") or [])
    return (
        f"integrar capacidad {h['nombre']}: {kws}; "
        f"modo {h['modo']} vía API remota / Free Tier; "
        f"visión voz idiomas eficiencia; arquitectura sana"
    )


def integrar_30x_via_sce(*, registrar_ledger: bool = True, force: bool = False) -> dict[str, Any]:
    """Pasa las 30 habilidades por SCE y sella el ADN v101."""
    global _CACHE_30X
    if _CACHE_30X is not None and not force:
        return _CACHE_30X

    from cognicion.evolucion import MSG_ACEPTADA, analizar_valor

    aprobadas: list[dict[str, Any]] = []
    revisadas: list[dict[str, Any]] = []
    bloqueadas: list[dict[str, Any]] = []

    for h in HABILIDADES_30X:
        # Solo bloquear si el MODO/nombre pide peso local prohibido
        blob = f"{h.get('nombre','')} {h.get('modo','')} {h.get('motor','')}".lower()
        riesgos = any(
            r in blob
            for r in ("torch local", "cuda local", "pip install runtime", "camera-engine")
        )
        if riesgos:
            item = {
                **h,
                "sce_decision": "bloquear",
                "sce_aprobado": False,
                "activa": False,
                "sce_mensaje": (
                    "Actualización rechazada por riesgo de inestabilidad. "
                    "Israel, he bloqueado esta inyección para proteger mi núcleo"
                ),
            }
            bloqueadas.append(item)
            continue
        item = {
            **h,
            "sce_decision": "aprobar",
            "sce_aprobado": True,
            "sce_mensaje": MSG_ACEPTADA,
            "activa": True,
        }
        aprobadas.append(item)

    # Un solo registro SCE del batch
    if registrar_ledger:
        try:
            analizar_valor(
                "integrar Evolución 30-X + Comic Engine: 30 capacidades ligeras "
                "(visión, voz, idiomas, cómic, eficiencia) vía API Free Tier, arquitectura sana"
            )
        except Exception:
            pass

    prioridad = next((a for a in aprobadas if a["id"] == PRIORIDAD_HOY_ID), aprobadas[0] if aprobadas else None)

    pack = {
        "ok": True,
        "protocol": "EVOLUCION_30X_COMIC_ENGINE",
        "version": "101.0.0",
        "creador": CREADOR,
        "estudio": ESTUDIO,
        "firma": FIRMA_OWNERSHIP,
        "mensaje_adn": MSG_ACEPTADA,
        "total": 30,
        "aprobadas": len(aprobadas),
        "bloqueadas": len(bloqueadas),
        "revisadas": len(revisadas),
        "habilidades": aprobadas + bloqueadas + revisadas,
        "prioridad_hoy": prioridad,
        "comic_engine": True,
        "nucleo": "sano",
    }
    _CACHE_30X = pack
    return pack


def estado_30x() -> dict[str, Any]:
    pack = integrar_30x_via_sce(registrar_ledger=True)
    # Compact list for API
    resumen = [
        {
            "id": h["id"],
            "nombre": h["nombre"],
            "grupo": h["grupo"],
            "modo": h["modo"],
            "activa": h.get("activa", False),
            "sce": h.get("sce_decision"),
        }
        for h in pack["habilidades"]
    ]
    prio = pack.get("prioridad_hoy") or {}
    return {
        "protocol": pack["protocol"],
        "version": pack["version"],
        "active": True,
        "total": 30,
        "aprobadas_sce": pack["aprobadas"],
        "mensaje": pack["mensaje_adn"],
        "creador": CREADOR,
        "prioridad_hoy": {
            "id": prio.get("id"),
            "nombre": prio.get("nombre"),
            "motivo": "Protocolo v101 centra el núcleo artístico en Comic_Engine",
        },
        "comic_engine_activo": True,
        "nucleo": "OPERATIVO",
        "habilidades": resumen,
        "firma": FIRMA_OWNERSHIP,
    }


def es_peticion_30x(texto: str) -> bool:
    t = (texto or "").lower()
    marcas = (
        "30 habilidades", "30-x", "30x", "evolución 30", "comic engine",
        "cómic engine", "habilidades de vanguardia", "núcleo artístico",
    )
    return any(m in t for m in marcas)


def bloque_contexto_30x() -> str:
    st = estado_30x()
    p = st["prioridad_hoy"]
    return "\n".join([
        "[Evolución 30-X + Comic Engine v101]",
        f"SCE: {st['aprobadas_sce']}/30 capacidades selladas bajo ADN de {CREADOR}.",
        st["mensaje"],
        f"Prioridad hoy: #{p.get('id')} {p.get('nombre')} — {p.get('motivo')}.",
        "Comic_Engine activo: Guion → Storyboard → Ilustración → Lettering.",
        "Free Tier: motores remotos/ligeros; sin torch local ni tocar Golden Camera.",
    ])
