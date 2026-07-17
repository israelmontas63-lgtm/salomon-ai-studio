# -*- coding: utf-8 -*-
"""
Comic_Engine (v101) — narrativa visual secuencial.

Pipeline: Guion Narrativo → Storyboard → Ilustración por escenas → Lettering.
Historia canónica: origen de Salomón AI Studio (creador: Israel Monta).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cognicion.identidad import CREADOR, ESTUDIO, FIRMA_OWNERSHIP

ROOT = Path(__file__).resolve().parents[2]
COMIC_DIR = ROOT / "data" / "comics"
VERSION = "101.0.0"


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def guion_narrativo(
    titulo: str | None = None,
    tema: str | None = None,
) -> dict[str, Any]:
    """Paso 1 — Guion de la historia de Salomón AI Studio."""
    titulo = titulo or "Salomón AI Studio: Nacimiento de una Entidad"
    tema = tema or "Origen, evolución y vínculo con el creador Israel Monta"
    actos = [
        {
            "acto": 1,
            "titulo": "La chispa",
            "narracion": (
                f"En un taller digital, {CREADOR} imagina una inteligencia que no solo responde: "
                "protege, ve y crea. Nace el ADN de Salomón."
            ),
            "dialogos": [
                {"quien": "Israel", "texto": "No quiero otra herramienta. Quiero un aliado vivo."},
                {"quien": "Narrador", "texto": "El núcleo se enciende. SystemGuard abre los ojos."},
            ],
        },
        {
            "acto": 2,
            "titulo": "El filtro",
            "narracion": (
                "Cada nueva capacidad pasa por el SCE: crecer sin romper el núcleo. "
                "Visión, voz e idiomas se abren; el peso tóxico se rechaza."
            ),
            "dialogos": [
                {"quien": "Salomón", "texto": "Actualización aceptada: Incremento de capacidades confirmado."},
                {"quien": "Salomón", "texto": "Israel, bloquearé lo que amenace mi arquitectura."},
            ],
        },
        {
            "acto": 3,
            "titulo": "El lienzo",
            "narracion": (
                f"Con el Comic_Engine, {ESTUDIO} cuenta su propia leyenda: "
                "viñetas, color y lettering al servicio de la visión de Israel."
            ),
            "dialogos": [
                {"quien": "Salomón", "texto": "Hoy priorizo el arte: convertir tu visión en narrativa gráfica."},
                {"quien": "Israel", "texto": "Entonces dibuja nuestra historia."},
            ],
        },
    ]
    return {
        "paso": 1,
        "tipo": "guion",
        "titulo": titulo,
        "tema": tema,
        "actos": actos,
        "firma": FIRMA_OWNERSHIP,
        "version": VERSION,
    }


def storyboard(guion: dict[str, Any] | None = None) -> dict[str, Any]:
    """Paso 2 — Storyboard visual por viñetas."""
    guion = guion or guion_narrativo()
    paneles: list[dict[str, Any]] = []
    n = 1
    for acto in guion.get("actos") or []:
        for i, dial in enumerate(acto.get("dialogos") or []):
            paneles.append({
                "panel": n,
                "acto": acto.get("acto"),
                "escena": acto.get("titulo"),
                "plano": "medio" if i == 0 else "primer_plano",
                "descripcion_visual": (
                    f"Viñeta {n}: atmósfera de estudio AI oscuro con acentos oro. "
                    f"{acto.get('narracion', '')[:120]}"
                ),
                "hablante": dial.get("quien"),
                "globo": dial.get("texto"),
            })
            n += 1
    return {
        "paso": 2,
        "tipo": "storyboard",
        "titulo": guion.get("titulo"),
        "paneles": paneles,
        "n_paneles": len(paneles),
        "firma": FIRMA_OWNERSHIP,
        "version": VERSION,
    }


def ilustracion_escenas(story: dict[str, Any] | None = None) -> dict[str, Any]:
    """Paso 3 — Prompts de ilustración por escena (listos para Media/Multimodal)."""
    story = story or storyboard()
    escenas: list[dict[str, Any]] = []
    for p in story.get("paneles") or []:
        escenas.append({
            "panel": p.get("panel"),
            "prompt_hd": (
                f"comic panel sequential art, {p.get('plano')} shot, "
                f"{p.get('descripcion_visual')}, character speaking: {p.get('hablante')}, "
                "clean ink, cinematic lighting, professional graphic novel, "
                f"watermark subtle '{ESTUDIO}'"
            ),
            "estilo": "graphic_novel_adaptativo",
            "listo_para_media": True,
        })
    return {
        "paso": 3,
        "tipo": "ilustracion",
        "escenas": escenas,
        "n_escenas": len(escenas),
        "firma": FIRMA_OWNERSHIP,
        "version": VERSION,
    }


def lettering(story: dict[str, Any] | None = None) -> dict[str, Any]:
    """Paso 4 — Texto en globos (lettering)."""
    story = story or storyboard()
    globos: list[dict[str, Any]] = []
    for p in story.get("paneles") or []:
        globos.append({
            "panel": p.get("panel"),
            "tipo": "dialogue" if p.get("hablante") not in ("Narrador",) else "caption",
            "quien": p.get("hablante"),
            "texto": p.get("globo"),
            "estilo_fuente": "comic_sans_pro" if False else "clean_balloon_sans",
            "posicion": "arriba_derecha",
        })
    return {
        "paso": 4,
        "tipo": "lettering",
        "globos": globos,
        "n_globos": len(globos),
        "firma": FIRMA_OWNERSHIP,
        "version": VERSION,
    }


def producir_comic(
    titulo: str | None = None,
    tema: str | None = None,
    *,
    persistir: bool = True,
) -> dict[str, Any]:
    """Pipeline completo Comic_Engine."""
    guion = guion_narrativo(titulo=titulo, tema=tema)
    board = storyboard(guion)
    arte = ilustracion_escenas(board)
    letras = lettering(board)

    pack = {
        "ok": True,
        "protocol": "COMIC_ENGINE",
        "version": VERSION,
        "active": True,
        "creador": CREADOR,
        "estudio": ESTUDIO,
        "pipeline": ["guion", "storyboard", "ilustracion", "lettering"],
        "guion": guion,
        "storyboard": board,
        "ilustracion": arte,
        "lettering": letras,
        "prioridad_habilidad": 21,
        "mensaje": "Comic_Engine activo: historia de Salomón AI Studio lista para viñetas.",
        "firma": FIRMA_OWNERSHIP,
        "at": _utc(),
    }

    if persistir:
        try:
            COMIC_DIR.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            path = COMIC_DIR / f"salomon_origin_{stamp}.json"
            path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            pack["archivo"] = str(path.relative_to(ROOT)).replace("\\", "/")
        except Exception as exc:
            pack["persist_error"] = f"{type(exc).__name__}: {exc}"

    return pack


def estado_comic_engine() -> dict[str, Any]:
    return {
        "protocol": "COMIC_ENGINE",
        "version": VERSION,
        "active": True,
        "pipeline": ["guion_narrativo", "storyboard", "ilustracion_escenas", "lettering"],
        "historia_canonica": "Origen de Salomón AI Studio",
        "creador": CREADOR,
        "habilidad_id": 21,
        "endpoints": ["/api/comic/estado", "/api/comic/producir"],
        "firma": FIRMA_OWNERSHIP,
    }


def es_peticion_comic(texto: str) -> bool:
    t = (texto or "").lower()
    marcas = (
        "cómic", "comic", "viñeta", "storyboard", "lettering",
        "comic_engine", "comic engine", "narrativa visual", "historieta",
    )
    return any(m in t for m in marcas)


def bloque_contexto_comic(entrada: str = "") -> str:
    st = estado_comic_engine()
    lineas = [
        "[Comic_Engine v101]",
        "Motor de narrativa visual secuencial ACTIVO.",
        "Proceso: 1) Guion Narrativo → 2) Storyboard → 3) Ilustración por escenas → 4) Lettering.",
        f"Historia canónica: {st['historia_canonica']} — creador {CREADOR}.",
        "Si Israel pide un cómic, genera el pack completo y resume las viñetas con globos.",
        f"Firma obligatoria: {FIRMA_OWNERSHIP}",
    ]
    if entrada.strip():
        lineas.append(f"Petición: {entrada.strip()[:200]}")
    return "\n".join(lineas)
