"""
Memoria de contexto dinámica — hechos clave entre sesiones.
Persiste en JSON local y capa PREFERENCIAS / PROYECTO vía MemoriaVectorial.
"""

from __future__ import annotations

import json
import re
from typing import Any

from cognicion.memoria.tipos import TipoMemoria
from cognicion.memoria.vectorial import obtener_memoria
from settings import ROOT_DIR

_ARCHIVO = ROOT_DIR / "data" / "memoria_personal.json"

_SEMILLAS: list[dict[str, str]] = [
    {"clave": "usuario", "valor": "Israel", "capa": "preferencias"},
    {"clave": "persona_cercana", "valor": "Melanie", "capa": "preferencias"},
    {"clave": "marca_visual", "valor": "negro y oro con monograma", "capa": "preferencias"},
    {
        "clave": "voz",
        "valor": "ElevenLabs Multilingual v2, tono juvenil y enérgico",
        "capa": "preferencias",
    },
    {
        "clave": "enfoque",
        "valor": "monetización de marca, guiones y contenido motivacional",
        "capa": "proyecto",
    },
]

_PATRONES: list[tuple[str, re.Pattern[str], str]] = [
    (
        "persona_cercana",
        re.compile(r"\b(?:se llama|llamada|es)\s+(Melanie)\b", re.I),
        "preferencias",
    ),
    (
        "preferencia_edicion",
        re.compile(r"(?:prefiero|quiero|usa siempre|no uses)\s+(.{8,120})", re.I),
        "preferencias",
    ),
    (
        "proyecto",
        re.compile(r"(?:proyecto|estamos trabajando en|marca)\s+(.{4,100})", re.I),
        "proyecto",
    ),
]


def _cargar() -> dict[str, Any]:
    if not _ARCHIVO.exists():
        return {"hechos": {}}
    try:
        return json.loads(_ARCHIVO.read_text(encoding="utf-8"))
    except Exception:
        return {"hechos": {}}


def _guardar(data: dict[str, Any]) -> None:
    _ARCHIVO.parent.mkdir(parents=True, exist_ok=True)
    _ARCHIVO.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _sincronizar_vectorial(hechos: dict[str, Any]) -> None:
    mem = obtener_memoria()
    if not mem.activa:
        return
    for clave, meta in hechos.items():
        texto = f"{clave}: {meta.get('valor', '')}"
        capa = meta.get("capa") or TipoMemoria.PREFERENCIAS.value
        mem.guardar_en_capa(
            texto,
            capa,
            session_id="personal",
            categoria="contexto_personal",
            origen="dinamico",
        )


def asegurar_semillas() -> None:
    data = _cargar()
    hechos = data.setdefault("hechos", {})
    cambiados = False
    for s in _SEMILLAS:
        if s["clave"] not in hechos:
            hechos[s["clave"]] = {"valor": s["valor"], "capa": s["capa"]}
            cambiados = True
    if cambiados:
        _guardar(data)
        _sincronizar_vectorial(hechos)


def registrar_hecho(clave: str, valor: str, capa: str = "preferencias") -> None:
    data = _cargar()
    data.setdefault("hechos", {})[clave] = {
        "valor": valor.strip(),
        "capa": capa,
    }
    _guardar(data)
    _sincronizar_vectorial(data["hechos"])


def extraer_y_aprender(texto_usuario: str) -> list[str]:
    """Extrae hechos del mensaje y los persiste. Devuelve claves actualizadas."""
    asegurar_semillas()
    actualizados: list[str] = []
    for clave, patron, capa in _PATRONES:
        m = patron.search(texto_usuario or "")
        if not m:
            continue
        valor = m.group(1).strip(" .,!?:;")
        if len(valor) >= 3:
            registrar_hecho(clave, valor, capa)
            actualizados.append(clave)
    return actualizados


def bloque_contexto() -> str:
    """Texto listo para inyectar en el prompt del turno."""
    asegurar_semillas()
    hechos = _cargar().get("hechos") or {}
    if not hechos:
        return ""
    lineas = ["[Memoria personal — recuerda siempre]"]
    for clave, meta in hechos.items():
        lineas.append(f"- {clave}: {meta.get('valor', '')}")
    lineas.append(
        "Instrucción: Personaliza la respuesta con estos hechos cuando sea natural. "
        "No inventes otros nombres o preferencias."
    )
    return "\n".join(lineas)
