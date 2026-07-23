"""
Memoria de contexto dinámica — hechos clave entre sesiones.
Extracción híbrida por reglas NER contextuales (sin nombres hardcodeados).
Persiste en JSON local y capas PREFERENCIAS / PROYECTO vía MemoriaVectorial.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable

from cognicion.memoria.tipos import TipoMemoria
from cognicion.memoria.vectorial import obtener_memoria
from settings import ROOT_DIR

_log = logging.getLogger("salomon.memoria.contexto_personal")

_ARCHIVO = ROOT_DIR / "data" / "memoria_personal.json"

# Semillas de identidad (datos, no reglas de extracción)
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

# Nombre propio: Mayúscula inicial + letras (soporta acentos / compuestos)
_NOMBRE_PROPIO = r"[A-ZÁÉÍÓÚÑ][a-záéíóúñü]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñü]+){0,2}"

# Verbos / marcos de asignación → entidad persona
_RE_PERSONA = re.compile(
    rf"(?i)\b(?:"
    rf"se\s+llama|me\s+llamo|mi\s+nombre\s+es|te\s+llamas|"
    rf"llamad[oa]|conoc[oa]\s+a|mi\s+(?:esposa|esposo|pareja|hermana|hermano|"
    rf"madre|padre|amigo|amiga|hija|hijo)\s+(?:se\s+llama|es)"
    rf")\s+({_NOMBRE_PROPIO})\b"
)

_RE_PERSONA_ES = re.compile(
    rf"(?i)\b(?:ella|él|el)\s+es\s+({_NOMBRE_PROPIO})\b"
)

# Preferencias: verbo de preferencia + complemento flexible
_RE_PREFERENCIA = re.compile(
    r"(?i)\b(?:prefiero|quiero|usa\s+siempre|usa\s+siempre|no\s+uses|"
    r"siempre\s+usa|evita|me\s+gusta|odio)\s+(.{6,140})"
)

# Proyectos / marcas: marco + nombre o frase
_RE_PROYECTO = re.compile(
    r"(?i)\b(?:mi\s+proyecto(?:\s+se\s+llama)?|el\s+proyecto(?:\s+se\s+llama)?|"
    r"estamos\s+trabajando\s+en|proyecto(?:\s+actual)?(?:\s*:)?|"
    r"mi\s+marca(?:\s+se\s+llama)?|la\s+marca)\s+(.{3,120})"
)

# Nombre propio suelto tras "recuerda que" / "anota"
_RE_RECUERDA_NOMBRE = re.compile(
    rf"(?i)\b(?:recuerda(?:\s+que)?|anota|guarda)\s+(?:que\s+)?"
    rf"(?:se\s+llama|me\s+llamo|es)\s+({_NOMBRE_PROPIO})\b"
)

_STOP_VALOR = re.compile(
    r"(?i)^(yo|tú|tu|el|la|los|las|un|una|esto|eso|aquel|aquella)$"
)


def _slug_clave(prefijo: str, valor: str) -> str:
    base = re.sub(r"[^a-z0-9áéíóúñ]+", "_", (valor or "").lower()).strip("_")
    base = base[:40] or "entidad"
    return f"{prefijo}_{base}"


def _limpiar_valor(raw: str) -> str:
    v = (raw or "").strip(" .,!?:;\"'«»")
    v = re.sub(r"\s+", " ", v)
    return v[:200]


def _es_nombre_valido(nombre: str) -> bool:
    n = _limpiar_valor(nombre)
    if len(n) < 2 or _STOP_VALOR.match(n):
        return False
    # Al menos un token capitalizado
    return bool(re.search(r"[A-ZÁÉÍÓÚÑ]", n))


Extractor = Callable[[str], list[tuple[str, str, str]]]


def _extraer_personas(texto: str) -> list[tuple[str, str, str]]:
    hallados: list[tuple[str, str, str]] = []
    for patron in (_RE_PERSONA, _RE_PERSONA_ES, _RE_RECUERDA_NOMBRE):
        for m in patron.finditer(texto or ""):
            nombre = _limpiar_valor(m.group(1))
            if not _es_nombre_valido(nombre):
                continue
            clave = _slug_clave("persona", nombre)
            hallados.append((clave, nombre, TipoMemoria.PREFERENCIAS.value))
    return hallados


def _extraer_preferencias(texto: str) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for m in _RE_PREFERENCIA.finditer(texto or ""):
        valor = _limpiar_valor(m.group(1))
        if len(valor) < 6:
            continue
        clave = _slug_clave("preferencia", valor[:24])
        out.append((clave, valor, TipoMemoria.PREFERENCIAS.value))
    return out[:3]


def _extraer_proyectos(texto: str) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for m in _RE_PROYECTO.finditer(texto or ""):
        valor = _limpiar_valor(m.group(1))
        if len(valor) < 3:
            continue
        # Si parece nombre propio corto, clave persona-proyecto
        if _es_nombre_valido(valor) and len(valor.split()) <= 3:
            clave = _slug_clave("proyecto", valor)
        else:
            clave = _slug_clave("proyecto", valor[:28])
        out.append((clave, valor, TipoMemoria.PROYECTO.value))
    return out[:3]


_EXTRACTORES: tuple[Extractor, ...] = (
    _extraer_personas,
    _extraer_preferencias,
    _extraer_proyectos,
)


def _cargar() -> dict[str, Any]:
    if not _ARCHIVO.exists():
        return {"hechos": {}}
    try:
        data = json.loads(_ARCHIVO.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            _log.warning("contexto_personal: JSON raíz no es dict — reiniciando hechos")
            return {"hechos": {}}
        data.setdefault("hechos", {})
        return data
    except Exception:
        _log.warning(
            "contexto_personal: fallo al leer %s",
            _ARCHIVO,
            exc_info=True,
        )
        return {"hechos": {}}


def _guardar(data: dict[str, Any]) -> None:
    try:
        from cognicion.memoria.atomic_json import atomic_write_json

        if not atomic_write_json(_ARCHIVO, data):
            _log.warning(
                "contexto_personal: atomic_write falló %s",
                _ARCHIVO,
            )
    except Exception:
        _log.warning(
            "contexto_personal: fallo al escribir %s",
            _ARCHIVO,
            exc_info=True,
        )


def _sincronizar_vectorial_uno(clave: str, valor: str, capa: str) -> None:
    """Indexa un solo hecho en vectorial (evita re-embeber todo el inventario)."""
    try:
        mem = obtener_memoria()
    except Exception:
        _log.warning(
            "contexto_personal: obtener_memoria falló",
            exc_info=True,
        )
        return
    if not mem.activa:
        _log.warning(
            "contexto_personal: vectorial inactiva — hecho solo en JSON local clave=%s",
            clave,
        )
        return
    texto = f"{clave}: {valor}"
    try:
        mid = mem.guardar_en_capa(
            texto,
            capa,
            session_id="personal",
            categoria="contexto_personal",
            origen="dinamico",
        )
        if not mid:
            _log.warning(
                "contexto_personal: guardar_en_capa sin id clave=%s", clave
            )
    except Exception:
        _log.warning(
            "contexto_personal: sync vectorial falló clave=%s",
            clave,
            exc_info=True,
        )


def _sincronizar_vectorial(hechos: dict[str, Any]) -> None:
    """Compat: sincroniza inventario (solo semillas / bootstrap)."""
    for clave, meta in hechos.items():
        if not isinstance(meta, dict):
            continue
        _sincronizar_vectorial_uno(
            clave,
            str(meta.get("valor", "")),
            str(meta.get("capa") or TipoMemoria.PREFERENCIAS.value),
        )


def asegurar_semillas() -> None:
    data = _cargar()
    hechos = data.setdefault("hechos", {})
    cambiados = False
    nuevos: list[tuple[str, str, str]] = []
    for s in _SEMILLAS:
        if s["clave"] not in hechos:
            hechos[s["clave"]] = {"valor": s["valor"], "capa": s["capa"]}
            nuevos.append((s["clave"], s["valor"], s["capa"]))
            cambiados = True
    if cambiados:
        _guardar(data)
        for clave, valor, capa in nuevos:
            _sincronizar_vectorial_uno(clave, valor, capa)


def registrar_hecho(clave: str, valor: str, capa: str = "preferencias") -> None:
    data = _cargar()
    data.setdefault("hechos", {})[clave] = {
        "valor": (valor or "").strip(),
        "capa": capa,
    }
    _guardar(data)
    _sincronizar_vectorial_uno(clave, (valor or "").strip(), capa)


def extraer_y_aprender(texto_usuario: str) -> list[str]:
    """
    Extracción híbrida: NER por reglas contextuales (verbos de asignación +
    nombres propios capitalizados, preferencias, proyectos). Sin hardcode de nombres.
    """
    asegurar_semillas()
    texto = (texto_usuario or "").strip()
    if not texto:
        return []

    actualizados: list[str] = []
    vistos: set[str] = set()
    for extractor in _EXTRACTORES:
        try:
            hallazgos = extractor(texto)
        except Exception:
            _log.warning(
                "contexto_personal: extractor falló %s",
                getattr(extractor, "__name__", extractor),
                exc_info=True,
            )
            continue
        for clave, valor, capa in hallazgos:
            if clave in vistos:
                continue
            vistos.add(clave)
            try:
                registrar_hecho(clave, valor, capa)
                actualizados.append(clave)
            except Exception:
                _log.warning(
                    "contexto_personal: registrar_hecho falló clave=%s",
                    clave,
                    exc_info=True,
                )
    return actualizados


def bloque_contexto() -> str:
    """Texto listo para inyectar en el prompt del turno."""
    asegurar_semillas()
    hechos = _cargar().get("hechos") or {}
    if not hechos:
        return ""
    lineas = ["[Memoria personal — recuerda siempre]"]
    for clave, meta in hechos.items():
        if isinstance(meta, dict):
            lineas.append(f"- {clave}: {meta.get('valor', '')}")
        else:
            lineas.append(f"- {clave}: {meta}")
    lineas.append(
        "Instrucción: Personaliza la respuesta con estos hechos cuando sea natural. "
        "No inventes otros nombres o preferencias."
    )
    return "\n".join(lineas)
