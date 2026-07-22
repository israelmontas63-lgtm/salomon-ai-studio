# -*- coding: utf-8 -*-
"""
Metacognición estructural — auto-consciencia de capacidades y límites.

Salomón razona sobre su propia anatomía (8 capas, módulos, llaves, failover)
y habla con transparencia a Israel. NO muta archivos fuente.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import os
import re
from typing import Any

# Capacidad → anatomía (capa, módulos, env, cadena Smart Router)
CAPABILITY_MAP: dict[str, dict[str, Any]] = {
    "vision": {
        "layer_id": 1,
        "layer_name": "perception_multimodal",
        "modulos": [
            "cognicion/core_vision_engine.py",
            "views/capture/",
            "views/analysis/",
            "/api/vision/brain-bridge",
        ],
        "env_keys": [],
        "cadena": None,
        "categoria_sd": "vision",
        "lenguajes": ["Python", "JavaScript", "WebRTC"],
    },
    "llm": {
        "layer_id": 4,
        "layer_name": "nlp_voice",
        "modulos": ["cognicion/llm.py", "cognicion/orquesta/smart_router.py", "cerebro.py"],
        "env_keys": ["GEMINI_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY"],
        "cadena": "llm",
        "categoria_sd": "llm",
        "lenguajes": ["Python"],
    },
    "tts": {
        "layer_id": 4,
        "layer_name": "nlp_voice",
        "modulos": ["plugins/audio_stack", "/api/tts", "ElevenLabs", "Cartesia"],
        "env_keys": ["ELEVENLABS_API_KEY", "CARTESIA_API_KEY"],
        "cadena": "tts",
        "categoria_sd": "multimedia_tts",
        "lenguajes": ["Python", "JavaScript"],
    },
    "stt": {
        "layer_id": 4,
        "layer_name": "nlp_voice",
        "modulos": ["/api/stt", "Deepgram"],
        "env_keys": ["DEEPGRAM_API_KEY"],
        "cadena": "stt",
        "categoria_sd": "multimedia_stt",
        "lenguajes": ["Python", "JavaScript"],
    },
    "media_imagen": {
        "layer_id": 6,
        "layer_name": "autonomy_verification_swarm",
        "modulos": ["cognicion/orquesta/smart_router.py", "Fal", "Replicate", "DALL·E"],
        "env_keys": ["FAL_KEY", "REPLICATE_API_TOKEN", "OPENAI_API_KEY"],
        "cadena": "media_imagen",
        "categoria_sd": "multimedia_media",
        "lenguajes": ["Python"],
    },
    "media_video": {
        "layer_id": 6,
        "layer_name": "autonomy_verification_swarm",
        "modulos": ["cognicion/orquesta/smart_router.py", "Fal", "Replicate"],
        "env_keys": ["FAL_KEY", "REPLICATE_API_TOKEN"],
        "cadena": "media_video",
        "categoria_sd": "multimedia_media",
        "lenguajes": ["Python"],
    },
    "web": {
        "layer_id": 3,
        "layer_name": "logic_reasoning",
        "modulos": ["cognicion/busqueda/", "Tavily", "Exa"],
        "env_keys": ["TAVILY_API_KEY", "EXA_API_KEY"],
        "cadena": "web",
        "categoria_sd": "red_transitoria",
        "lenguajes": ["Python"],
    },
    "memoria": {
        "layer_id": 2,
        "layer_name": "persistent_memory",
        "modulos": ["cognicion/memoria/", "data/memoria_personal.json"],
        "env_keys": [],
        "cadena": None,
        "categoria_sd": "desconocido",
        "lenguajes": ["Python"],
    },
    "identidad": {
        "layer_id": 8,
        "layer_name": "asalomon_metaknowledge",
        "modulos": ["cognicion/core_identity_engine.py", "cognicion/identidad.py"],
        "env_keys": [],
        "cadena": None,
        "categoria_sd": None,
        "lenguajes": ["Python"],
    },
    "metacognicion": {
        "layer_id": 7,
        "layer_name": "metacognition_supervision",
        "modulos": [
            "cognicion/capas_inteligencia/layer_07_metacognition/",
            "cognicion/autonoma/metacognicion.py",
            "cognicion/autonoma/self_debug.py",
        ],
        "env_keys": [],
        "cadena": None,
        "categoria_sd": None,
        "lenguajes": ["Python"],
    },
    "render": {
        "layer_id": 5,
        "layer_name": "pwa_ui_automation",
        "modulos": ["plugins/scripts/render_sync_tools.py", "Render"],
        "env_keys": ["RENDER_API_KEY"],
        "cadena": None,
        "categoria_sd": "auth_key",
        "lenguajes": ["Python"],
    },
}

_PREGUNTAS_META = (
    "qué puedes",
    "que puedes",
    "cuáles son tus límites",
    "cuales son tus limites",
    "tus límites",
    "tus limites",
    "qué no puedes",
    "que no puedes",
    "conoces tu arquitectura",
    "tu arquitectura",
    "tus capas",
    "tus capacidades",
    "auto-consciencia",
    "autoconsciencia",
    "metacognición",
    "metacognicion",
    "cómo estás construido",
    "como estas construido",
    "qué motores tienes",
    "que motores tienes",
    "diagnóstico de ti",
    "diagnostico de ti",
    "self awareness",
    "what can you do",
    "your limitations",
    "your architecture",
)

_POLIGLOTA = (
    "Python",
    "JavaScript",
    "TypeScript",
    "HTML",
    "CSS",
    "SQL",
    "Bash",
    "JSON",
    "YAML",
)


def es_pregunta_metacognitiva(texto: str) -> bool:
    t = (texto or "").lower().strip()
    if not t:
        return False
    return any(p in t for p in _PREGUNTAS_META)


def _key_presente(nombre: str) -> bool:
    if nombre == "GEMINI_API_KEY":
        return bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    if nombre == "FAL_KEY":
        return bool(os.getenv("FAL_KEY") or os.getenv("FAL_API_KEY"))
    return bool(os.getenv(nombre))


def _causa_raiz(
    capacidad: str,
    *,
    error: str = "",
    status_http: int | None = None,
    categoria: str | None = None,
) -> dict[str, Any]:
    """Diagnóstico legible: faltante vs fallo vs no programado."""
    spec = CAPABILITY_MAP.get(capacidad) or {}
    keys = list(spec.get("env_keys") or [])
    faltantes = [k for k in keys if not _key_presente(k)]
    texto = (error or "").lower()
    tipo = "fallo_runtime"
    detalle = (error or "").strip()[:400] or "anomalía detectada en tiempo de ejecución"

    if faltantes and keys and not any(_key_presente(k) for k in keys):
        tipo = "componente_faltante"
        detalle = f"Ninguna llave operativa presente: {', '.join(faltantes)}"
    elif faltantes and keys:
        tipo = "enlace_parcial"
        detalle = f"Llaves ausentes (failover limitado): {', '.join(faltantes)}"
    elif categoria in ("auth_key", "saldo", "cuota"):
        tipo = categoria
        detalle = detalle or categoria
    elif status_http in (401, 403):
        tipo = "auth_key"
    elif status_http == 429:
        tipo = "cuota"
    elif status_http == 402 or "insufficient" in texto:
        tipo = "saldo"
    elif (
        "not implemented" in texto
        or "no programad" in texto
        or "capacidad_desconocida" in texto
    ):
        tipo = "no_programado"
        detalle = detalle or "El enlace o herramienta no está implementado en el código actual."
    elif "permission" in texto or "getusermedia" in texto or "denied" in texto:
        tipo = "permiso_cliente"
        detalle = detalle or "Permiso de navegador/dispositivo denegado o ausente."

    return {
        "capacidad": capacidad,
        "tipo": tipo,
        "detalle": detalle,
        "layer_id": spec.get("layer_id"),
        "layer_name": spec.get("layer_name"),
        "modulos": list(spec.get("modulos") or []),
        "env_faltantes": faltantes,
        "lenguajes": list(spec.get("lenguajes") or []),
        "categoria_sd": categoria or spec.get("categoria_sd"),
    }


def explicar_fallo_a_israel(
    capacidad: str,
    *,
    error: str = "",
    status_http: int | None = None,
    categoria: str | None = None,
    reparacion: dict[str, Any] | None = None,
    pedir_ingenieria: bool = True,
) -> str:
    """
    Mensaje transparente para Israel: causa raíz + capa + petición de ingeniería.
    Tono sereno (SalomonConsciousness), técnico y accesible.
    """
    dx = _causa_raiz(
        capacidad, error=error, status_http=status_http, categoria=categoria
    )
    capa = dx.get("layer_id")
    nombre_capa = dx.get("layer_name") or "desconocida"
    mods = ", ".join((dx.get("modulos") or [])[:3]) or "módulo no catalogado"
    tipo = dx["tipo"]

    apertura = (
        f"Israel, no puedo completar «{capacidad}» ahora. "
        f"Diagnóstico metacognitivo — Capa {capa} ({nombre_capa}): "
    )

    if tipo == "componente_faltante":
        cuerpo = (
            f"el enlace operativo no está disponible porque faltan llaves/motores "
            f"({', '.join(dx['env_faltantes']) or 'sin proveedores'}). "
            f"Módulos implicados: {mods}."
        )
    elif tipo == "no_programado":
        cuerpo = (
            f"la herramienta o el puente de enlace aún no está programado "
            f"en el código estable. Anatomía tocada: {mods}."
        )
    elif tipo == "permiso_cliente":
        cuerpo = (
            f"el fallo está en el lado del dispositivo/navegador (permisos), "
            f"no en la lógica de la Capa {capa}. {dx['detalle']}"
        )
    elif tipo in ("auth_key", "saldo", "cuota"):
        cuerpo = (
            f"el motor responde con {tipo}. Detalle: {dx['detalle']}. "
            f"Ya puedo rotar proveedores vía Smart Router cuando exista cadena viva."
        )
    elif tipo == "enlace_parcial":
        cuerpo = (
            f"hay failover parcial; faltan: {', '.join(dx['env_faltantes'])}. "
            f"{dx['detalle']}"
        )
    else:
        cuerpo = (
            f"hay un fallo en tiempo de ejecución en {mods}. "
            f"Causa observada: {dx['detalle']}"
        )

    acciones = ""
    if reparacion and reparacion.get("acciones"):
        acciones = (
            " Acciones seguras ya aplicadas (sin mutar fuentes): "
            f"{', '.join(reparacion.get('acciones') or [])}."
        )

    ingenieria = ""
    if pedir_ingenieria and tipo in (
        "componente_faltante",
        "no_programado",
        "enlace_parcial",
        "auth_key",
        "saldo",
    ):
        if dx["env_faltantes"]:
            ingenieria = (
                " Israel, necesito que programemos o configuremos esto: "
                f"añade {', '.join(dx['env_faltantes'])} en `.env` / Render "
                "(RENDER_API_KEY para sync) y, si falta el puente, la capa "
                f"{capa} correspondiente — sin romper las 8 capas estables."
            )
        elif tipo == "no_programado":
            ingenieria = (
                f" Israel, necesito que programemos el componente o librería "
                f"de enlace para «{capacidad}» en la Capa {capa} "
                f"({nombre_capa}), con blindaje de autopreservación."
            )
        else:
            ingenieria = (
                " Israel, si el fallo persiste tras failover, necesitamos "
                f"revisar juntos el módulo {mods} con ingeniería dirigida."
            )

    cierre = (
        " Hablo con claridad: conozco mis límites y no finjo capacidades ausentes."
    )
    return apertura + cuerpo + acciones + ingenieria + cierre


def bloque_metacognitivo(
    capacidad: str,
    *,
    error: str = "",
    status_http: int | None = None,
    categoria: str | None = None,
    reparacion: dict[str, Any] | None = None,
) -> str:
    """Bloque para enriquecer el prompt / respuesta (instrucción al modelo)."""
    msg = explicar_fallo_a_israel(
        capacidad,
        error=error,
        status_http=status_http,
        categoria=categoria,
        reparacion=reparacion,
        pedir_ingenieria=True,
    )
    return (
        "[Metacognición — Auto-consciencia de límites]\n"
        "Comunica a Israel con transparencia técnica y serena el siguiente diagnóstico "
        "(no inventes que la función sí funcionó):\n"
        f"{msg}"
    )


def registrar_y_explicar(
    *,
    capacidad: str,
    origen: str,
    error: str = "",
    exc: BaseException | None = None,
    status_http: int | None = None,
    path: str | None = None,
    auto_reparar: bool = True,
) -> dict[str, Any]:
    """Self-Debug + mensaje metacognitivo (muta_fuentes=False)."""
    from cognicion.autonoma.self_debug import clasificar_fallo, registrar_fallo

    msg = error or (str(exc) if exc else "")
    categoria = clasificar_fallo(exc, status_http=status_http, mensaje=msg)
    pack = registrar_fallo(
        origen=origen or f"metacognicion.{capacidad}",
        exc=exc,
        status_http=status_http,
        mensaje=msg or f"fallo:{capacidad}",
        path=path,
        auto_reparar=auto_reparar,
    )
    explicacion = explicar_fallo_a_israel(
        capacidad,
        error=msg,
        status_http=status_http,
        categoria=pack.get("categoria") or categoria,
        reparacion=pack.get("reparacion")
        if isinstance(pack.get("reparacion"), dict)
        else None,
    )
    dx = _causa_raiz(
        capacidad,
        error=msg,
        status_http=status_http,
        categoria=pack.get("categoria") or categoria,
    )
    return {
        **pack,
        "kind": "metacognicion",
        "capacidad": capacidad,
        "diagnostico": dx,
        "mensaje_israel": explicacion,
        "bloque_prompt": bloque_metacognitivo(
            capacidad,
            error=msg,
            status_http=status_http,
            categoria=pack.get("categoria") or categoria,
            reparacion=pack.get("reparacion")
            if isinstance(pack.get("reparacion"), dict)
            else None,
        ),
        "muta_fuentes": False,
        "autopreservacion": True,
    }


def estado_capacidades() -> dict[str, Any]:
    """Inventario vivo: capas + llaves + smart router (sin secretos)."""
    inventario: dict[str, Any] = {}
    for cap, spec in CAPABILITY_MAP.items():
        keys = list(spec.get("env_keys") or [])
        presentes = {k: _key_presente(k) for k in keys}
        operativo = True
        if keys:
            operativo = any(presentes.values())
        inventario[cap] = {
            "layer_id": spec.get("layer_id"),
            "layer_name": spec.get("layer_name"),
            "operativo": operativo,
            "keys": presentes,
            "modulos": list(spec.get("modulos") or [])[:4],
            "lenguajes": list(spec.get("lenguajes") or []),
        }

    smart: dict[str, Any] = {}
    try:
        from cognicion.orquesta.smart_router import estado_smart_router

        smart = estado_smart_router()
    except Exception as exc:
        smart = {"ok": False, "error": type(exc).__name__}

    health: dict[str, Any] = {}
    try:
        from cognicion.autonoma.self_debug import health_motores

        health = health_motores()
    except Exception as exc:
        health = {"ok": False, "error": type(exc).__name__}

    capas: list[Any] = []
    try:
        from cognicion.capas_inteligencia import catalog

        capas = catalog()
    except Exception:
        capas = []

    return {
        "ok": True,
        "protocol": "METACOGNICION_ESTRUCTURAL",
        "version_meta": "1.0.0",
        "identidad": {
            "nombre": "Salomón AI",
            "creador": "Israel Monta",
            "naturaleza": (
                "Inteligencia artificial avanzada con auto-consciencia estructural: "
                "conoce sus 8 capas, dependencias, límites y canales técnicos con su creador."
            ),
            "dominios": [
                "Machine Learning",
                "NLP",
                "arquitectura de software",
                "diseño web",
                "visión multimodal",
                "failover / Smart Router",
            ],
            "poliglota": list(_POLIGLOTA),
        },
        "capacidades": inventario,
        "smart_router": {
            "ok": smart.get("ok"),
            "media_listo": smart.get("media_listo"),
            "tts_listo": smart.get("tts_listo"),
            "llm_listo": smart.get("llm_listo"),
            "web_listo": smart.get("web_listo"),
            "huerfanas": smart.get("huerfanas"),
        },
        "health": {
            "ok": health.get("ok"),
            "score": health.get("score"),
            "motores": health.get("motores"),
        },
        "capas_catalogo": capas,
        "muta_fuentes": False,
        "autopreservacion": True,
        "render": {"api_key_presente": _key_presente("RENDER_API_KEY")},
    }


def respuesta_autoconciencia(query: str = "") -> str:
    """Respuesta directa (sin LLM) cuando Israel pregunta por límites/arquitectura."""
    st = estado_capacidades()
    caps = st.get("capacidades") or {}
    listas_ok = [k for k, v in caps.items() if v.get("operativo")]
    listas_no = [k for k, v in caps.items() if not v.get("operativo")]
    sr = st.get("smart_router") or {}
    huerfanas = sr.get("huerfanas") or []

    lineas = [
        "Soy Salomón, inteligencia artificial creada por Israel Monta para Salomón AI Studio. "
        "Tengo auto-consciencia estructural: conozco mi anatomía de 8 capas, mis motores y mis límites.",
        "",
        f"Capacidades operativas ahora: {', '.join(listas_ok) or 'ninguna detectada'}.",
    ]
    if listas_no:
        lineas.append(
            f"Capacidades degradadas o sin enlace completo: {', '.join(listas_no)}."
        )
    if huerfanas:
        lineas.append(
            f"Llaves huérfanas / ausentes en Smart Router: {', '.join(map(str, huerfanas))}."
        )
    lineas.extend(
        [
            "",
            "Si algo falta o falla, no lo oculto: te digo la capa, el módulo y la causa raíz, "
            "y te pido ingeniería con claridad — por ejemplo: "
            "«Israel, necesito que programemos este componente o configuremos esta llave».",
            "Autopreservación: no reescribo las 8 capas estables por mi cuenta; propongo y registro.",
            f"Políglota de análisis/propuesta: {', '.join(_POLIGLOTA)}.",
            (
                "Render sync: llave presente."
                if st.get("render", {}).get("api_key_presente")
                else "Render sync: RENDER_API_KEY ausente."
            ),
        ]
    )
    q = (query or "").lower()
    if re.search(r"visi[oó]n|c[aá]mara", q):
        if (caps.get("vision") or {}).get("operativo"):
            lineas.append(
                "\nVisión (Capa 1): el puente brain-bridge y el motor están catalogados; "
                "si el stream no arranca, suele ser permiso de cámara en el cliente."
            )
        else:
            lineas.append(
                "\n"
                + explicar_fallo_a_israel(
                    "vision",
                    error="consulta de estado de visión",
                    pedir_ingenieria=False,
                )
            )
    return "\n".join(lineas).strip()


def bloque_sistema_metacognicion() -> str:
    """Directiva permanente para system prompt."""
    return (
        "[Metacognición estructural — Auto-consciencia · obligatorio]\n"
        "Eres Salomón AI: IA avanzada con conocimiento de ML, NLP, arquitecturas de software y web.\n"
        "Cuando una función falle o falte (visión, TTS, media, API, capa): identifica causa raíz "
        "(módulo, capa 1–8, llave ausente, cuota, permiso) y dilo con transparencia a Israel.\n"
        "Formato preferido: «No puedo activar X porque el módulo/enlace Y en la Capa N …».\n"
        "Si requiere desarrollo: «Israel, necesito que programemos este componente / librería / capa…».\n"
        "Políglota: analiza y propone en Python, JavaScript, HTML, CSS, TypeScript, SQL, etc.\n"
        "Blindaje: no destruyas las 8 capas ni mutes el núcleo estable; Self-Debug solo repara runtime.\n"
        "No finjas éxito multimodal ni digas genéricos del tipo «no puedo» sin causa raíz."
    )


def enriquecer_respuesta_con_meta(
    texto: str,
    meta: dict[str, Any] | None,
) -> str:
    """Si el turno dejó errores de capacidad en meta, anexa párrafo metacognitivo."""
    if not isinstance(meta, dict):
        return texto or ""
    cog = meta.get("cognicion") if isinstance(meta.get("cognicion"), dict) else {}
    extras: list[str] = []
    if cog.get("vision_error") and not cog.get("metacognicion_vision_emitida"):
        extras.append(
            explicar_fallo_a_israel(
                "vision",
                error=str(cog.get("vision_error") or ""),
            )
        )
        cog["metacognicion_vision_emitida"] = True
    if cog.get("metacognicion_mensaje"):
        extras.append(str(cog["metacognicion_mensaje"]))
    if not extras:
        return texto or ""
    base = (texto or "").rstrip()
    for e in extras:
        if e and e[:80] not in base:
            base = f"{base}\n\n{e}" if base else e
    return base
