"""Nodos del grafo — cada uno envuelve capacidades ya existentes."""

from __future__ import annotations

import re
from typing import Any

from cognicion.grafo.estado import EstadoSalomon

_PALABRAS_PROFUNDAS = (
    "analiza",
    "análisis",
    "analisis",
    "debate",
    "debatir",
    "por qué",
    "por que",
    "porque",
    "qué piensas",
    "que piensas",
    "perspectiva",
    "perspectivas",
    "razona",
    "razonamiento",
    "profundiza",
    "profundizar",
    "compara",
    "ventajas",
    "desventajas",
    "opinión",
    "opinion",
    "reflexiona",
    "reflexión",
    "reflexion",
    "argumenta",
    "contraargumento",
    "critica",
    "crítica",
    "evalúa",
    "evalua",
    "dilema",
    "hipótesis",
    "hipotesis",
)


def _detectar_ruta(mensaje: str) -> str:
    t = (mensaje or "").lower()
    if any(
        p in t
        for p in (
            "genera imagen",
            "generar imagen",
            "crea una imagen",
            "dibuja",
            "dall-e",
            "dalle",
            "ilustra",
            "imagen de",
            "genera una imagen",
            "flux",
            "midjourney",
            "fotorreal",
            "retrato hd",
            "imagen hd",
        )
    ):
        return "imagen"
    if any(
        p in t
        for p in (
            "genera video",
            "generar video",
            "crea un video",
            "runway",
            "kling",
            "gen-3",
            "gen3",
            "clip de video",
            "animación de",
            "animacion de",
            "editar video",
            "edita el video",
            "cortar video",
            "corte de video",
            "filtro video",
            "overlay",
            "superponer texto",
            "procesar video",
        )
    ):
        return "video"
    if any(
        p in t
        for p in (
            "upscale",
            "escalar imagen",
            "refinar textura",
            "krea",
            "postproceso",
            "post-proceso",
        )
    ):
        return "imagen"  # post vía media_ops hint en bridge
    if any(
        p in t
        for p in ("guion", "guión", "comercial", "motivacional", "vender", "monetiz")
    ):
        return "contenido"
    if any(
        p in t
        for p in ("código", "codigo", "bug", "error", "refactor", "arreglar", "parche")
    ):
        return "tecnico"
    return "hablar"


def requiere_razonamiento_profundo(
    mensaje: str,
    *,
    forzar: bool = False,
) -> bool:
    """True solo cuando aporta profundidad (protege latencia del modo rápido)."""
    if forzar:
        return True
    t = (mensaje or "").strip().lower()
    if not t:
        return False
    if any(p in t for p in _PALABRAS_PROFUNDAS):
        return True
    # Preguntas densas / multi-cláusula
    if len(t) >= 120 and ("?" in t or t.count(",") >= 2):
        return True
    if t.count("?") >= 2:
        return True
    return False


def _esqueleto_razonamiento(mensaje: str) -> dict[str, Any]:
    """Fallback local sin LLM — estructura mínima usable."""
    corto = (mensaje or "").strip()
    if len(corto) > 160:
        corto = corto[:157] + "…"
    return {
        "reformulacion": f"El usuario pide explorar con rigor: {corto}",
        "perspectivas": [
            "Clarificar qué se asume y qué falta por saber",
            "Valorar trade-offs antes de concluir",
            "Ofrecer una posición clara y una vía de diálogo",
        ],
        "supuestos": "Puede haber matices no dichos; conviene explicitarlos.",
        "pregunta_reflexiva": (
            "¿Qué parte te importa más ahora: la claridad del concepto "
            "o las implicaciones prácticas?"
        ),
        "plan": [
            "Responder con una tesis breve",
            "Mostrar 1–2 matices",
            "Cerrar con una pregunta para profundizar",
        ],
        "fuente": "local",
    }


def _parsear_razonamiento(texto: str, mensaje: str) -> dict[str, Any]:
    base = _esqueleto_razonamiento(mensaje)
    if not (texto or "").strip():
        return base

    def _campo(nombre: str) -> str | None:
        m = re.search(
            rf"(?im)^{nombre}\s*:\s*(.+?)(?=^\w[\w_]*\s*:|\Z)",
            texto,
            re.S,
        )
        return m.group(1).strip() if m else None

    ref = _campo("REFORMULACION") or _campo("REFORMULACIÓN")
    if ref:
        base["reformulacion"] = ref.split("\n")[0].strip()

    pers = _campo("PERSPECTIVAS")
    if pers:
        items = [
            re.sub(r"^[\-\d\.\)\s]+", "", ln).strip()
            for ln in pers.splitlines()
            if ln.strip()
        ]
        if items:
            base["perspectivas"] = items[:4]

    sup = _campo("SUPUESTOS")
    if sup:
        base["supuestos"] = " ".join(sup.split())

    preg = _campo("PREGUNTA")
    if preg:
        base["pregunta_reflexiva"] = preg.split("\n")[0].strip()

    plan = _campo("PLAN")
    if plan:
        items = [
            re.sub(r"^[\-\d\.\)\s]+", "", ln).strip()
            for ln in plan.splitlines()
            if ln.strip()
        ]
        if items:
            base["plan"] = items[:5]

    base["fuente"] = "llm"
    return base


def _bloque_razonamiento_para_prompt(razonamiento: dict[str, Any] | None) -> str:
    if not razonamiento:
        return ""
    pers = razonamiento.get("perspectivas") or []
    plan = razonamiento.get("plan") or []
    lineas = [
        "[Razonamiento lógico previo — úsalo; no lo copies literal]",
        f"Reformulación: {razonamiento.get('reformulacion', '')}",
        "Perspectivas:",
        *[f"- {p}" for p in pers],
        f"Supuestos: {razonamiento.get('supuestos', '')}",
        f"Plan: {'; '.join(plan)}",
        f"Pregunta reflexiva sugerida: {razonamiento.get('pregunta_reflexiva', '')}",
        "En tu respuesta: tesis clara, 1–2 matices y cierra con UNA pregunta "
        "para seguir el diálogo (estilo experto, no interrogatorio).",
    ]
    return "\n".join(lineas)


def nodo_coordinador(estado: EstadoSalomon) -> dict[str, Any]:
    """Decide ruta: orquesta multi-agente, razonamiento, media o chat."""
    from cognicion.memoria.contexto_personal import bloque_contexto, extraer_y_aprender
    from cognicion.orquesta import necesita_orquesta

    mensaje = (estado.get("mensaje") or "").strip()
    meta = dict(estado.get("metadata") or {})
    forzar = bool(meta.get("profundizar"))
    forzar_orquesta = bool(meta.get("forzar_orquesta"))
    extraer_y_aprender(mensaje)
    hechos = bloque_contexto()
    ruta_meta = (meta.get("ruta_forzada") or "").strip().lower()
    if ruta_meta in (
        "imagen",
        "video",
        "hablar",
        "contenido",
        "tecnico",
        "busqueda",
        "orquestador",
    ):
        ruta = ruta_meta
    else:
        ruta = _detectar_ruta(mensaje)

    orquesta = False
    if ruta_meta == "orquestador" or forzar_orquesta:
        orquesta = True
        ruta = "orquestador"
    elif ruta not in ("imagen", "video"):
        orquesta = necesita_orquesta(
            mensaje, forzar=False, hechos_personales=hechos
        )
        if orquesta and ruta in ("hablar", "contenido", "busqueda"):
            ruta = "orquestador"

    profundo = False
    if ruta not in ("imagen", "video", "busqueda", "orquestador"):
        profundo = requiere_razonamiento_profundo(mensaje, forzar=forzar)
    modo = "profundo" if (profundo or orquesta) else "rapido"
    return {
        "intencion": ruta,
        "ruta": ruta,  # type: ignore[typeddict-item]
        "modo_razonamiento": modo,  # type: ignore[typeddict-item]
        "hechos_personales": hechos,
        "necesita_orquesta": orquesta,
        "media_path": estado.get("media_path") or meta.get("media_path"),
        "media_ops": estado.get("media_ops") or meta.get("media_ops") or {},
        "metadata": {
            **meta,
            "coordinador": {
                "ruta": ruta,
                "modo_razonamiento": modo,
                "orquesta": orquesta,
            },
        },
    }


def nodo_orquestador(estado: EstadoSalomon) -> dict[str, Any]:
    """
    Colsub — director on-demand: escala 1–40 agentes según complejidad,
    respeta CPU/RAM y sintetiza con lo ya reunido si hay presión.
    """
    from cognicion.orquesta import colsub_desplegar

    mensaje = (estado.get("consulta_busqueda") or estado.get("mensaje") or "").strip()
    meta = dict(estado.get("metadata") or {})
    forzar_n = meta.get("colsub_n") or meta.get("agentes_n")
    try:
        forzar_n = int(forzar_n) if forzar_n is not None else None
    except (TypeError, ValueError):
        forzar_n = None

    pack = colsub_desplegar(
        mensaje,
        forzar_n=forzar_n,
        hechos_personales=estado.get("hechos_personales") or "",
    )
    colsub_meta = pack.get("colsub") or {}
    return {
        "hallazgos_agentes": pack,
        "necesita_orquesta": False,
        "consulta_busqueda": mensaje,
        "metadata": {
            **meta,
            "orquestador": {
                "ok": bool(pack.get("exito")),
                "agentes_ok": pack.get("agentes_ok") or [],
                "agentes_fallidos": pack.get("agentes_fallidos") or [],
                "total_hallazgos": pack.get("total_hallazgos") or 0,
                "colsub": colsub_meta,
            },
        },
        "ruta": "hablar",
    }


def nodo_razonamiento(estado: EstadoSalomon) -> dict[str, Any]:
    """
    Cadena de pensamiento + convergencia multi-agente.
    Si hay hallazgos_agentes, consolida y entrega respuesta elegante (síntesis).
    """
    from cognicion.busqueda import necesita_busqueda_web
    from cognicion.llm import generar_texto, llm_disponible
    from cognicion.orquesta.agentes_paralelos import sintetizar_orquesta
    from settings import BUSQUEDA_WEB_AUTO

    mensaje = (estado.get("mensaje") or "").strip()
    hechos = estado.get("hechos_personales") or ""
    meta = dict(estado.get("metadata") or {})
    forzar_busqueda = bool(meta.get("forzar_busqueda"))
    hallazgos = estado.get("hallazgos_agentes") or {}

    # ── Modo síntesis (post-orquesta) ─────────────────────────────────────
    if hallazgos.get("informes"):
        texto = sintetizar_orquesta(
            mensaje or hallazgos.get("consulta") or "",
            hallazgos,
            hechos_personales=hechos,
        )
        razon = {
            "reformulacion": f"Convergencia multi-agente sobre: {(mensaje or '')[:120]}",
            "perspectivas": [
                f"Agentes OK: {', '.join(hallazgos.get('agentes_ok') or []) or 'ninguno'}",
                f"Fallidos (continuamos): {', '.join(hallazgos.get('agentes_fallidos') or []) or 'ninguno'}",
            ],
            "supuestos": "Se priorizan hechos útiles; se eliminan redundancias entre informes.",
            "pregunta_reflexiva": "¿Qué ángulo quieres profundizar: web, académico o mercado?",
            "plan": [
                "Consolidar hallazgos",
                "Eliminar redundancias",
                "Entregar síntesis elegante",
            ],
            "modo": "sintesis_multiagente",
        }
        return {
            "razonamiento": razon,
            "respuesta": texto,
            "sintesis_lista": True,
            "necesita_busqueda": False,
            "necesita_orquesta": False,
            "metadata": {
                **meta,
                "razonamiento": {
                    "ok": True,
                    "fuente": "sintesis_orquesta",
                    "agentes_ok": hallazgos.get("agentes_ok"),
                },
            },
            "ruta": "fin",
        }

    # ── Modo planificación (pre-respuesta) ────────────────────────────────
    llm_ok = llm_disponible()
    llm_limitado = not llm_ok
    razon: dict[str, Any]
    ok_meta: dict[str, Any]

    if not llm_ok:
        razon = _esqueleto_razonamiento(mensaje)
        razon["necesita_datos_externos"] = True
        ok_meta = {"ok": True, "fuente": "local", "llm": False, "motivo": "llm_no_disponible"}
        llm_limitado = True
    else:
        prompt = f"""Eres el nodo de razonamiento lógico de Salomón.
Analiza la pregunta ANTES de responder. Sé breve y estructurado.
No redactes la respuesta final al usuario.

Mensaje del usuario:
{mensaje}

Contexto personal (no inventes de más):
{hechos or '(ninguno)'}

Responde EXACTAMENTE con este formato:

REFORMULACION: (una frase)
PERSPECTIVAS:
- (perspectiva 1)
- (perspectiva 2)
- (perspectiva 3 opcional)
SUPUESTOS: (una o dos frases)
PREGUNTA: (una pregunta reflexiva para dialogar)
PLAN:
- (paso 1)
- (paso 2)
- (paso 3)
NECESITA_BUSQUEDA: si|no
NECESITA_ORQUESTA: si|no
CONSULTA: (consulta breve si hace falta datos externos; si no, ninguna)
"""
        try:
            bruto = (generar_texto(prompt) or "").strip()
            razon = _parsear_razonamiento(bruto, mensaje)
            m_nb = re.search(r"(?im)^NECESITA_BUSQUEDA\s*:\s*(si|sí|no)\b", bruto)
            m_no = re.search(r"(?im)^NECESITA_ORQUESTA\s*:\s*(si|sí|no)\b", bruto)
            m_c = re.search(r"(?im)^CONSULTA\s*:\s*(.+)$", bruto)
            if m_nb and m_nb.group(1).lower() in ("si", "sí"):
                razon["necesita_datos_externos"] = True
            if m_no and m_no.group(1).lower() in ("si", "sí"):
                razon["necesita_orquesta"] = True
            if m_c:
                cons = m_c.group(1).strip()
                if cons.lower() not in ("ninguna", "n/a", "-", "no"):
                    razon["consulta_busqueda"] = cons
            ok_meta = {"ok": True, "fuente": razon.get("fuente"), "llm": True}
        except Exception as exc:
            razon = _esqueleto_razonamiento(mensaje)
            razon["necesita_datos_externos"] = True
            ok_meta = {
                "ok": True,
                "fuente": "local",
                "llm": False,
                "error": type(exc).__name__,
            }
            llm_limitado = True

    from cognicion.orquesta import necesita_orquesta as _nec_orq

    auto = BUSQUEDA_WEB_AUTO or forzar_busqueda
    orquesta = bool(razon.get("necesita_orquesta")) or _nec_orq(
        mensaje, hechos_personales=hechos
    )
    necesita = bool(razon.get("necesita_datos_externos")) or necesita_busqueda_web(
        mensaje,
        llm_limitado=llm_limitado,
        forzar=forzar_busqueda,
    )
    if not auto:
        necesita = forzar_busqueda
        orquesta = bool(meta.get("forzar_orquesta"))

    # Orquesta tiene prioridad sobre búsqueda simple cuando hay complejidad
    if orquesta:
        necesita = False

    consulta = (
        razon.get("consulta_busqueda")
        or meta.get("consulta_busqueda")
        or mensaje
    )

    return {
        "razonamiento": razon,
        "necesita_busqueda": necesita,
        "necesita_orquesta": orquesta,
        "consulta_busqueda": consulta,
        "sintesis_lista": False,
        "metadata": {
            **meta,
            "razonamiento": ok_meta,
            "busqueda_planificada": necesita,
            "orquesta_planificada": orquesta,
        },
    }


def nodo_busqueda(estado: EstadoSalomon) -> dict[str, Any]:
    """Agente de búsqueda web — respaldo principal ante límites o falta de datos."""
    from cognicion.busqueda import responder_con_busqueda

    mensaje = estado.get("consulta_busqueda") or estado.get("mensaje") or ""
    hechos = estado.get("hechos_personales") or ""
    meta = dict(estado.get("metadata") or {})
    pack = responder_con_busqueda(mensaje, hechos_personales=hechos)
    ruta_destino = estado.get("ruta") or "hablar"
    # Si veníamos a hablar/contenido, la búsqueda ya entrega respuesta final útil
    return {
        "resultado_busqueda": pack.get("busqueda") or {},
        "respuesta": pack.get("texto") or "",
        "necesita_busqueda": False,
        "metadata": {
            **meta,
            "busqueda": {
                "ok": bool(pack.get("exito")),
                "motor": pack.get("motor"),
                "respaldo_principal": True,
            },
        },
        "ruta": "fin" if ruta_destino in ("hablar", "contenido", "busqueda") else ruta_destino,
        "error": None if pack.get("exito") else "busqueda_sin_resultados",
    }


def nodo_hablar(estado: EstadoSalomon) -> dict[str, Any]:
    """Agente conversacional — si hay límite/respuesta vacía, rescata con búsqueda web."""
    from cerebro import SalomonAI
    from cognicion.busqueda import (
        responder_con_busqueda,
        respuesta_parece_limite_o_vacia,
    )
    from settings import BUSQUEDA_WEB_AUTO

    sid = estado.get("session_id")
    salomon = SalomonAI(session_id=sid)
    entrada = estado.get("mensaje") or ""
    bloque = _bloque_razonamiento_para_prompt(estado.get("razonamiento"))
    busq_prev = estado.get("resultado_busqueda") or {}
    if busq_prev:
        entrada = (
            f"[Contexto de búsqueda web — úsalo como hechos]\n"
            f"{busq_prev.get('respuesta_directa') or busq_prev}\n\n"
            f"{entrada}"
        )
    if bloque:
        entrada = f"{bloque}\n\n[Mensaje del usuario]\n{entrada}"

    # Si el razonamiento ya pidió búsqueda y aún no se ejecutó, hacerlo antes
    if estado.get("necesita_busqueda") and not busq_prev and BUSQUEDA_WEB_AUTO:
        pack = responder_con_busqueda(
            estado.get("consulta_busqueda") or estado.get("mensaje") or "",
            hechos_personales=estado.get("hechos_personales") or "",
        )
        return {
            "session_id": salomon.sesion_id,
            "respuesta": pack.get("texto") or "",
            "resultado_busqueda": pack.get("busqueda") or {},
            "necesita_busqueda": False,
            "metadata": {
                **(estado.get("metadata") or {}),
                "hablar": {"exito": True, "tts": False, "via": "busqueda_previa"},
                "busqueda": {"ok": bool(pack.get("exito")), "motor": pack.get("motor")},
            },
            "ruta": "fin",
        }

    resp = salomon.procesar_entrada(entrada)
    texto = resp.texto or ""
    meta = {
        **(estado.get("metadata") or {}),
        "hablar": {"exito": resp.exito, "tts": resp.tts_disponible},
    }

    # Respaldo principal: nunca quedarse en mensaje de límites
    cogn = (resp.metadata or {}).get("cognicion") or {}
    llm_limitado = bool(cogn.get("llm_error") or cogn.get("llm_nota"))
    if BUSQUEDA_WEB_AUTO and (
        respuesta_parece_limite_o_vacia(texto) or llm_limitado
    ):
        pack = responder_con_busqueda(
            estado.get("mensaje") or "",
            hechos_personales=estado.get("hechos_personales") or "",
        )
        if pack.get("texto"):
            texto = pack["texto"]
            meta["busqueda"] = {
                "ok": bool(pack.get("exito")),
                "motor": pack.get("motor"),
                "rescate_limites": True,
            }
            return {
                "session_id": salomon.sesion_id,
                "respuesta": texto,
                "resultado_busqueda": pack.get("busqueda") or {},
                "necesita_busqueda": False,
                "metadata": meta,
                "ruta": "fin",
            }

    return {
        "session_id": salomon.sesion_id,
        "respuesta": texto,
        "metadata": meta,
        "ruta": "fin",
    }


def nodo_contenido(estado: EstadoSalomon) -> dict[str, Any]:
    """Agente de contenido — guion motivacional/comercial con LLM."""
    from cognicion.llm import generar_texto, llm_disponible

    mensaje = estado.get("mensaje") or ""
    hechos = estado.get("hechos_personales") or ""
    tema = mensaje.strip()
    bloque_r = _bloque_razonamiento_para_prompt(estado.get("razonamiento"))

    if not llm_disponible():
        borrador = (
            f"# Guion — borrador local\n\nTema: {tema}\n\n"
            "## Apertura\nLa curiosidad enciende el aprendizaje.\n\n"
            "## Cuerpo\nLa ciencia en la infancia construye criterio y futuro.\n\n"
            "## Cierre\nApoya la curiosidad hoy.\n"
        )
        return {
            "borrador_guion": borrador,
            "respuesta": "Generé un borrador básico (LLM no disponible).",
            "metadata": {
                **(estado.get("metadata") or {}),
                "contenido": {"ok": True, "llm": False},
            },
            "ruta": "fin",
        }

    prompt = f"""Eres el agente de contenido de Salomón AI Studio (marca negro y oro).
Redacta un GUION BREVE y MOTIVACIONAL en español, tono inspirador y profesional.

Pedido del usuario:
{tema}

Contexto de marca / memoria (úsalo con naturalidad, sin inventar de más):
{hechos or '(sin datos extra)'}

{bloque_r}

Formato obligatorio:
# Título atractivo
## Apertura (gancho) — 2 a 4 frases
## Cuerpo — 1 párrafo corto con valor emocional y claridad
## Cierre (CTA) — 2 frases con llamado a la acción

Sin meta-comentarios. Solo el guion listo para leer en voz alta."""

    try:
        borrador = (generar_texto(prompt) or "").strip()
        if not borrador:
            raise RuntimeError("llm_vacio")
        meta_ok = {"ok": True, "llm": True}
    except Exception as exc:
        borrador = (
            f"# La curiosidad científica en los niños\n\n"
            f"## Apertura (gancho)\n"
            f"Israel, cada pregunta de un niño es una chispa de futuro.\n\n"
            f"## Cuerpo\n"
            f"Sobre «{tema[:160]}»: cultivar curiosidad científica "
            f"enseña a observar, dudar con respeto y descubrir. "
            f"Eso forma mentes libres y marcas con propósito.\n\n"
            f"## Cierre (CTA)\n"
            f"Hoy, celebra una pregunta. Mañana, cosecharás un innovador.\n"
            f"— Agente de contenido (respaldo)\n"
        )
        meta_ok = {"ok": True, "llm": False, "error": type(exc).__name__}

    return {
        "borrador_guion": borrador,
        "respuesta": (
            "Listo. Aquí tienes el guion del agente de contenido. "
            "¿Lo leemos en voz alta con ElevenLabs o lo afinamos un poco más?"
        ),
        "metadata": {
            **(estado.get("metadata") or {}),
            "contenido": meta_ok,
        },
        "ruta": "fin",
    }


def nodo_tecnico(estado: EstadoSalomon) -> dict[str, Any]:
    """Agente técnico — reutiliza el registro / corrector sin tocar seguridad."""
    from cognicion.agente.registro import ejecutar_agente

    mensaje = estado.get("mensaje") or ""
    bloque = _bloque_razonamiento_para_prompt(estado.get("razonamiento"))
    if bloque:
        mensaje = f"{bloque}\n\nTarea técnica:\n{mensaje}"
    try:
        resultado = ejecutar_agente("corrector", tarea=mensaje, autonomo=False)
        texto = (
            str(resultado)
            if resultado is not None
            else (
                "Revisé tu pedido técnico. "
                "¿Confirmas que aplique cambios en el código?"
            )
        )
    except Exception as exc:
        texto = (
            f"Detecté un fallo técnico al invocar el agente corrector: "
            f"{type(exc).__name__}. "
            "Solución sugerida: reiniciar el servidor y repetir el pedido. ¿Confirmas?"
        )
        return {
            "resultado_tecnico": texto,
            "respuesta": texto,
            "error": str(exc),
            "ruta": "fin",
        }

    return {
        "resultado_tecnico": texto,
        "respuesta": texto,
        "metadata": {
            **(estado.get("metadata") or {}),
            "tecnico": {"ok": True},
        },
        "ruta": "fin",
    }


def nodo_imagen(estado: EstadoSalomon) -> dict[str, Any]:
    """Agente imagen vía Colsub Media Engine (Flux/MJ Pro → fallback)."""
    from cognicion.media.media_engine import bridge_colsub_media

    mensaje = (estado.get("mensaje") or "").strip()
    ops = dict(estado.get("media_ops") or {})
    prompt = (ops.get("prompt") or mensaje).strip()
    hint = str(ops.get("hint") or "").strip()
    if not hint:
        low = prompt.lower()
        if any(x in low for x in ("upscale", "krea", "refinar", "escalar", "4k")):
            hint = "postproceso"
        else:
            hint = "imagen_hd"
    pack = bridge_colsub_media(
        prompt,
        hint=hint,
        imagen_entrada=ops.get("imagen_entrada") or ops.get("ruta"),
        forzar_motor=ops.get("motor"),
    )
    resultado = dict(pack.get("resultado") or {})
    resultado["routing"] = pack.get("routing")
    resultado["tarea"] = pack.get("tarea")
    if resultado.get("exito"):
        texto = (
            "Imagen lista (Colsub Multi-Model Routing). "
            f"Motor: {resultado.get('motor')} · {resultado.get('modelo') or ''}. "
            f"Calidad: {resultado.get('calidad') or pack.get('routing', {}).get('calidad')}. "
            f"Archivo: {resultado.get('url_relativa') or resultado.get('ruta')}"
        )
        if resultado.get("aviso"):
            texto += f" ({resultado['aviso']})"
    else:
        texto = f"No pude generar la imagen: {resultado.get('error', 'desconocido')}"

    return {
        "resultado_imagen": resultado,
        "respuesta": texto,
        "metadata": {
            **(estado.get("metadata") or {}),
            "imagen": {
                "ok": bool(resultado.get("exito")),
                "motor": resultado.get("motor"),
                "routing": pack.get("routing"),
            },
        },
        "ruta": "fin",
        "error": None if resultado.get("exito") else resultado.get("error"),
    }


def nodo_video(estado: EstadoSalomon) -> dict[str, Any]:
    """Video Pro (Runway/Kling) o edición local MoviePy."""
    from cognicion.media.media_engine import bridge_colsub_media
    from cognicion.media.video import editar_video

    ops = dict(estado.get("media_ops") or {})
    meta = dict(estado.get("metadata") or {})
    mensaje = (estado.get("mensaje") or "").strip()
    ruta_media = estado.get("media_path") or meta.get("media_path") or ops.get("ruta")

    # Generación Pro si no hay archivo de entrada
    if not ruta_media or ops.get("generar") or ops.get("hint") == "video_gen":
        pack = bridge_colsub_media(
            str(ops.get("prompt") or mensaje),
            hint="video_gen",
            forzar_motor=ops.get("motor"),
        )
        resultado = dict(pack.get("resultado") or {})
        resultado["routing"] = pack.get("routing")
        if resultado.get("exito"):
            texto = (
                "Video listo (Colsub Multi-Model Routing). "
                f"Motor: {resultado.get('motor')} · {resultado.get('modelo') or ''}. "
                f"Activo: {resultado.get('url_relativa') or resultado.get('task_id') or resultado.get('ruta')}"
            )
        else:
            texto = (
                f"No pude generar el video Pro: {resultado.get('error') or resultado.get('aviso')}. "
                "Configura RUNWAY_API_KEY o KLING_API_KEY, o sube un clip para edición local."
            )
        return {
            "resultado_video": resultado,
            "respuesta": texto,
            "metadata": {
                **meta,
                "video": {
                    "ok": bool(resultado.get("exito")),
                    "motor": resultado.get("motor"),
                    "routing": pack.get("routing"),
                },
            },
            "ruta": "fin",
            "error": None if resultado.get("exito") else resultado.get("error"),
        }

    resultado = editar_video(
        ruta_media,
        operacion=str(ops.get("operacion") or "cortar"),
        inicio=float(ops.get("inicio") or 0),
        fin=ops.get("fin"),
        texto_overlay=str(ops.get("texto_overlay") or ""),
        brillo=float(ops.get("brillo") or 1.2),
    )
    if resultado.get("exito"):
        texto = (
            f"Video procesado ({resultado.get('operacion')}). "
            f"Motor: {resultado.get('motor')}. "
            f"Salida: {resultado.get('url_relativa') or resultado.get('ruta')}"
        )
        if resultado.get("aviso"):
            texto += f" ({resultado['aviso']})"
    else:
        texto = (
            f"No pude editar el video: {resultado.get('error')} "
            f"{resultado.get('detalle') or ''}"
        ).strip()

    return {
        "resultado_video": resultado,
        "respuesta": texto,
        "metadata": {
            **meta,
            "video": {"ok": bool(resultado.get("exito")), "motor": resultado.get("motor")},
        },
        "ruta": "fin",
        "error": None if resultado.get("exito") else resultado.get("error"),
    }


def enrutar_despues_coordinador(estado: EstadoSalomon) -> str:
    """Orquesta → orquestador; profunda → razonamiento; factual → búsqueda; else agente."""
    meta = estado.get("metadata") or {}
    if meta.get("forzar_orquesta") or meta.get("ruta_forzada") == "orquestador":
        return "orquestador"
    if estado.get("necesita_orquesta") or (estado.get("ruta") == "orquestador"):
        return "orquestador"
    if meta.get("forzar_busqueda") or meta.get("ruta_forzada") == "busqueda":
        return "busqueda"
    if (estado.get("modo_razonamiento") or "rapido") == "profundo":
        return "razonamiento"
    from cognicion.busqueda import necesita_busqueda_web
    from settings import BUSQUEDA_WEB_AUTO

    ruta = estado.get("ruta") or "hablar"
    if (
        BUSQUEDA_WEB_AUTO
        and ruta == "hablar"
        and necesita_busqueda_web(estado.get("mensaje") or "")
    ):
        return "busqueda"
    if ruta in (
        "hablar",
        "contenido",
        "tecnico",
        "imagen",
        "video",
        "busqueda",
        "orquestador",
    ):
        return ruta
    return "hablar"


def enrutar_despues_orquestador(estado: EstadoSalomon) -> str:
    """Tras desplegar agentes → razonamiento consolida."""
    return "razonamiento"


def enrutar_despues_razonamiento(estado: EstadoSalomon) -> str:
    if estado.get("sintesis_lista") or (
        estado.get("respuesta") and (estado.get("hallazgos_agentes") or {}).get("informes")
    ):
        return "fin"
    if estado.get("necesita_orquesta") and not (estado.get("hallazgos_agentes") or {}).get(
        "informes"
    ):
        return "orquestador"
    if estado.get("necesita_busqueda"):
        return "busqueda"
    ruta = estado.get("ruta") or "hablar"
    if ruta in ("hablar", "contenido", "tecnico", "imagen", "video", "busqueda"):
        return ruta
    return "hablar"
