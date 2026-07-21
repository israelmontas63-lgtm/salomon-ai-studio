# -*- coding: utf-8 -*-
"""
Ciclo de aprendizaje heurístico — ruta canónica (`cognicion.aprendizaje_ciclo`).

Incidente → causa raíz → episodio vectorial.
Distinto de `cognicion.aprendizaje` (motor post-turno / preferencias).

Compat: `cognicion.cognitivo.aprendizaje` reexporta este módulo.
"""

from __future__ import annotations

import re
from typing import Any, Final

from cognicion.episodica import FRASE_APRENDIZAJE, guardar_episodio

# Pesos de error: (patrón estructurado, etiqueta causa, peso)
_PESOS_ERROR: Final[tuple[tuple[re.Pattern[str], str, float], ...]] = (
    (
        re.compile(
            r"(?i)\b(api[\s_-]?key|clave|token|credencial|auth|unauthorized|401|403)\b"
        ),
        "falla_de_credencial_o_proveedor",
        3.0,
    ),
    (
        re.compile(
            r"(?i)\b(proveedor|gemini|groq|openai|elevenlabs|fal|replicate|quota|rate[\s_-]?limit)\b"
        ),
        "falla_de_credencial_o_proveedor",
        2.4,
    ),
    (
        re.compile(
            r"(?i)\b(memoria|olvido|contexto|rag|chroma|embedding|epis[oó]dic)\b"
        ),
        "contexto_insuficiente",
        2.8,
    ),
    (
        re.compile(
            r"(?i)\b(c[aá]mara|camera|visi[oó]n|getusermedia|permiso|notallowed|micr[oó]fono)\b"
        ),
        "nucleo_protegido_o_permiso",
        2.6,
    ),
    (
        re.compile(
            r"(?i)\b(tts|voz|audio|cartesia|speech|autoplay|silencio)\b"
        ),
        "falla_de_sintesis_o_audio_pwa",
        2.5,
    ),
    (
        re.compile(
            r"(?i)\b(deploy|render|gunicorn|syntax|import|compile|requirements)\b"
        ),
        "falla_de_despliegue_o_runtime",
        2.7,
    ),
    (
        re.compile(
            r"(?i)\b(tono|saludo|estilo|formal|grosero|cort[eé]s)\b"
        ),
        "desajuste_de_estilo",
        2.2,
    ),
    (
        re.compile(
            r"(?i)\b(latencia|timeout|lento|freeze|cuello\s+de\s+botella|websocket)\b"
        ),
        "cuello_de_botella_o_red",
        2.3,
    ),
    (
        re.compile(
            r"(?i)\b(imagen|genera(r)?|fal|replicate|dall-?e|gr[aá]fic)\b"
        ),
        "falla_de_generacion_multimodal",
        2.1,
    ),
    (
        re.compile(
            r"(?i)\b(instrucci[oó]n|desvi[oó]|no\s+es\s+eso|equivoc|incorrecto|corrige)\b"
        ),
        "desvio_respecto_a_instruccion_de_israel",
        2.0,
    ),
)

_RE_TOKEN = re.compile(r"[a-záéíóúñü0-9_\-]{3,}", re.IGNORECASE)


def _tokens_semanticos(texto: str) -> list[str]:
    return [m.group(0).lower() for m in _RE_TOKEN.finditer(texto or "")]


def _metadatos_contexto(
    desc: str,
    correccion: str,
    *,
    scores: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Metadatos detallados cuando falta corrección/descripción explícita."""
    blob = f"{desc} {correccion}".strip()
    tokens = _tokens_semanticos(blob)
    return {
        "desc_len": len((desc or "").strip()),
        "correccion_len": len((correccion or "").strip()),
        "desc_vacia": not bool((desc or "").strip()),
        "correccion_vacia": not bool((correccion or "").strip()),
        "tokens_muestra": tokens[:24],
        "token_count": len(tokens),
        "scores": dict(sorted((scores or {}).items(), key=lambda kv: -kv[1])[:6]),
        "fuente": "heuristica_semantica",
    }


def inferir_causa_raiz(
    descripcion: str,
    correccion: str = "",
) -> tuple[str, dict[str, Any]]:
    """
    Análisis heurístico por tokens semánticos + pesos de error.

    Returns:
        (etiqueta_causa, metadatos)
    """
    desc = (descripcion or "").strip()
    corr = (correccion or "").strip()
    blob = f"{desc}\n{corr}".strip()
    scores: dict[str, float] = {}

    if blob:
        for patron, etiqueta, peso in _PESOS_ERROR:
            hits = patron.findall(blob)
            if not hits:
                continue
            n = len(hits) if isinstance(hits, list) else 1
            scores[etiqueta] = scores.get(etiqueta, 0.0) + float(peso) * max(n, 1)

    meta = _metadatos_contexto(desc, corr, scores=scores)

    if scores:
        causa = max(scores.items(), key=lambda kv: kv[1])[0]
        meta["confianza"] = round(scores[causa] / (sum(scores.values()) or 1.0), 3)
        return causa, meta

    if corr:
        meta["confianza"] = round(0.35, 3)
        meta["motivo_fallback"] = "correccion_sin_patron_fuerte"
        return "desvio_respecto_a_instruccion_de_israel", meta

    fragmentos = [t for t in _tokens_semanticos(desc)[:8] if t]
    if fragmentos:
        causa = "incidente_contextual_" + "_".join(fragmentos[:4])[:96]
        meta["confianza"] = round(0.2, 3)
        meta["motivo_fallback"] = "descripcion_sin_patron_catalogado"
        return causa, meta

    meta["confianza"] = round(0.05, 3)
    meta["motivo_fallback"] = "sin_texto_util"
    meta["alerta"] = (
        "Descripción y corrección vacías o sin tokens; "
        "se registró metadatos contextuales en lugar de etiqueta genérica."
    )
    return "incidente_sin_senal_semantica", meta


def _inferir_causa(desc: str, correccion: str) -> str:
    """Compat: solo etiqueta (tests / callers legacy)."""
    causa, _ = inferir_causa_raiz(desc, correccion)
    return causa


def registrar_incidente(
    descripcion: str,
    *,
    causa_raiz: str = "",
    session_id: str | None = None,
    correccion_israel: str = "",
) -> dict[str, Any]:
    desc = (descripcion or "").strip()
    corr = (correccion_israel or "").strip()
    meta_causa: dict[str, Any] = {}
    causa = (causa_raiz or "").strip()
    if not causa:
        causa, meta_causa = inferir_causa_raiz(desc, corr)

    texto = (
        f"Incidente: {desc or '(sin descripción — ver metadatos)'}\n"
        f"Corrección de Israel: {corr[:500] if corr else '(vacía — ver metadatos)'}\n"
        f"{FRASE_APRENDIZAJE}"
    )
    ep = guardar_episodio(
        texto,
        tipo="incidente",
        session_id=session_id,
        causa_raiz=causa,
        meta={
            "aprendizaje": True,
            "causa_confianza": meta_causa.get("confianza"),
            "causa_motivo": str(meta_causa.get("motivo_fallback") or "heuristica")[:80],
            "token_count": int(meta_causa.get("token_count") or 0),
        },
    )
    return {
        **ep,
        "frase": FRASE_APRENDIZAJE,
        "causa_raiz": causa,
        "causa_meta": meta_causa,
        "mensaje_israel": (
            f"{FRASE_APRENDIZAJE} "
            f"Causa raíz registrada: {causa[:180]}"
        ),
    }
