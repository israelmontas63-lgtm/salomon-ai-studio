"""
Registro de conectores de conocimiento — adaptadores desacoplados.
Extiende fuentes existentes (clima, wikipedia) sin modificar el núcleo.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Protocol

import clima
from cognicion.cache import memoizar

WIKI_API = "https://es.wikipedia.org/w/api.php"
WIKI_REST = "https://es.wikipedia.org/api/rest_v1/page/summary"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
DDG_API = "https://api.duckduckgo.com/"

PALABRAS_BUSQUEDA = (
    "busca en internet",
    "buscar en internet",
    "busca en la web",
    "buscar en la web",
    "busca en linea",
    "busca en línea",
    "google",
    "investiga sobre",
    "investiga en",
    "búscame",
    "buscame",
    "search:",
)

PALABRAS_WIKIDATA = (
    "wikidata",
    "dato estructurado",
    "datos estructurados",
    "entidad wikidata",
    "identificador wikidata",
)

PALABRAS_NOTICIAS = (
    "noticias",
    "últimas noticias",
    "ultimas noticias",
    "titulares",
    "qué pasó",
    "que paso",
    "novedades sobre",
    "actualidad de",
    "news about",
    "headlines",
    "noticias de",
    "noticias sobre",
)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=es&gl=DO&ceid=DO:es"

PALABRAS_WIKIPEDIA = (
    "wikipedia",
    "wiki",
    "quién es",
    "quien es",
    "qué es",
    "que es",
    "define",
    "definición",
    "definicion",
    "historia de",
    "biografía",
    "biografia",
    "cuéntame sobre",
    "cuentame sobre",
    "información sobre",
    "informacion sobre",
    "busca en wikipedia",
)


@dataclass
class ResultadoConector:
    nombre: str
    contexto: str
    metadata: dict[str, Any]


class ConectorConocimiento(Protocol):
    nombre: str

    def aplica(self, entrada: str, **kwargs: Any) -> bool: ...

    def consultar(self, entrada: str, **kwargs: Any) -> ResultadoConector | None: ...


def es_consulta_wikipedia(texto: str) -> bool:
    t = (texto or "").lower()
    return any(p in t for p in PALABRAS_WIKIPEDIA)


def es_consulta_wikidata(texto: str) -> bool:
    t = (texto or "").lower()
    if any(p in t for p in PALABRAS_WIKIDATA):
        return True
    return es_consulta_wikipedia(texto)


def es_consulta_busqueda(texto: str) -> bool:
    t = (texto or "").lower()
    return any(p in t for p in PALABRAS_BUSQUEDA)


def es_consulta_noticias(texto: str) -> bool:
    t = (texto or "").lower()
    return any(p in t for p in PALABRAS_NOTICIAS)


def extraer_tema_noticias(texto: str) -> str | None:
    patrones = (
        r"(?:noticias sobre|noticias de|últimas noticias de|ultimas noticias de)\s+(.+?)(?:\?|$|\.)",
        r"(?:novedades sobre|actualidad de|qué pasó en|que paso en)\s+(.+?)(?:\?|$|\.)",
        r"(?:titulares sobre|titulares de)\s+(.+?)(?:\?|$|\.)",
    )
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            tema = match.group(1).strip(" ,.!")
            if len(tema) >= 3:
                return tema[:120]
    if es_consulta_noticias(texto):
        limpio = texto.strip(" ?.")
        for prefijo in PALABRAS_NOTICIAS:
            limpio = re.sub(re.escape(prefijo), "", limpio, flags=re.IGNORECASE).strip()
        if len(limpio) >= 3:
            return limpio[:120]
    return None


def extraer_tema_busqueda(texto: str) -> str | None:
    patrones = (
        r"(?:busca en internet|buscar en internet|busca en la web)[:\s]+(.+?)(?:\?|$|\.)",
        r"(?:investiga sobre|investiga en|búscame|buscame)[:\s]+(.+?)(?:\?|$|\.)",
        r"search:\s*(.+?)(?:\?|$|\.)",
    )
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            tema = match.group(1).strip(" ,.!")
            if len(tema) >= 3:
                return tema[:120]
    if es_consulta_busqueda(texto):
        limpio = texto.strip(" ?.")
        for prefijo in PALABRAS_BUSQUEDA:
            limpio = re.sub(re.escape(prefijo), "", limpio, flags=re.IGNORECASE).strip()
        if len(limpio) >= 3:
            return limpio[:120]
    return None


def extraer_tema_wikipedia(texto: str) -> str | None:
    """Extrae el tema a buscar en Wikipedia."""
    patrones = (
        r"(?:wikipedia|wiki)[:\s]+(.+?)(?:\?|$|\.)",
        r"(?:quién es|quien es|qué es|que es)\s+(.+?)(?:\?|$|\.)",
        r"(?:define|definición|definicion de)\s+(.+?)(?:\?|$|\.)",
        r"(?:historia de|biografía de|biografia de)\s+(.+?)(?:\?|$|\.)",
        r"(?:cuéntame sobre|cuentame sobre|información sobre|informacion sobre)\s+(.+?)(?:\?|$|\.)",
    )
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if not match:
            continue
        tema = match.group(1).strip(" ,.!")
        if len(tema) >= 3:
            return tema

    if es_consulta_wikipedia(texto):
        limpio = texto.strip(" ?.")
        for prefijo in PALABRAS_WIKIPEDIA:
            limpio = re.sub(re.escape(prefijo), "", limpio, flags=re.IGNORECASE).strip()
        if len(limpio) >= 3:
            return limpio[:120]

    return None


def _wiki_get(url: str, timeout: int = 12) -> dict | list | None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SalomonAI/1.0 (conector conocimiento)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_get_text(url: str, timeout: int = 12) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SalomonAI/1.0 (conector conocimiento)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _buscar_titulo_wikipedia(tema: str) -> str | None:
    params = urllib.parse.urlencode({
        "action": "query",
        "list": "search",
        "srsearch": tema,
        "srlimit": "1",
        "format": "json",
        "utf8": "1",
    })
    datos = _wiki_get(f"{WIKI_API}?{params}")
    if not isinstance(datos, dict):
        return None

    resultados = datos.get("query", {}).get("search", [])
    if not resultados:
        return None
    return resultados[0].get("title")


def _resumen_wikipedia(titulo: str) -> dict | None:
    titulo_cod = urllib.parse.quote(titulo.replace(" ", "_"), safe="")
    url = f"{WIKI_REST}/{titulo_cod}"
    try:
        datos = _wiki_get(url)
        return datos if isinstance(datos, dict) else None
    except urllib.error.HTTPError:
        return None


def consultar_wikipedia(tema: str) -> ResultadoConector | None:
    """Consulta Wikipedia en español y devuelve contexto formateado."""
    return memoizar(
        f"wikipedia:{tema.lower()}",
        lambda: _consultar_wikipedia_sin_cache(tema),
        ttl=1800,
    )


def _consultar_wikipedia_sin_cache(tema: str) -> ResultadoConector | None:
    titulo = _buscar_titulo_wikipedia(tema)
    if not titulo:
        return ResultadoConector(
            nombre="wikipedia",
            contexto=(
                f"[Wikipedia — sin resultados]\n"
                f"No encontré artículos para «{tema}».\n"
                "Instrucción: Indica al usuario que no hubo coincidencias claras."
            ),
            metadata={"wikipedia_error": "sin_resultados", "tema": tema},
        )

    resumen = _resumen_wikipedia(titulo)
    if not resumen:
        return ResultadoConector(
            nombre="wikipedia",
            contexto=(
                f"[Wikipedia — error]\n"
                f"No pude leer el artículo «{titulo}».\n"
                "Instrucción: Responde con lo que sepas y menciona la limitación."
            ),
            metadata={"wikipedia_error": "resumen_fallido", "titulo": titulo},
        )

    extracto = (resumen.get("extract") or "").strip()
    descripcion = (resumen.get("description") or "").strip()
    url_articulo = (resumen.get("content_urls") or {}).get("desktop", {}).get("page", "")

    contexto = f"""[Wikipedia — {titulo}]
{f"Descripción: {descripcion}" if descripcion else ""}
{extracto}
{"Fuente: " + url_articulo if url_articulo else ""}

Instrucción: Usa estos datos reales de Wikipedia en español. Cita el artículo de forma natural si es relevante."""

    return ResultadoConector(
        nombre="wikipedia",
        contexto=contexto.strip(),
        metadata={
            "wikipedia_titulo": titulo,
            "wikipedia_url": url_articulo,
        },
    )


def consultar_wikidata(tema: str) -> ResultadoConector | None:
    """Consulta Wikidata y devuelve datos estructurados en español."""
    return memoizar(
        f"wikidata:{tema.lower()}",
        lambda: _consultar_wikidata_sin_cache(tema),
        ttl=1800,
    )


def _consultar_wikidata_sin_cache(tema: str) -> ResultadoConector | None:
    params = urllib.parse.urlencode({
        "action": "wbsearchentities",
        "search": tema,
        "language": "es",
        "format": "json",
        "limit": "1",
    })
    datos = _wiki_get(f"{WIKIDATA_API}?{params}")
    if not isinstance(datos, dict):
        return None

    resultados = datos.get("search") or []
    if not resultados:
        return ResultadoConector(
            nombre="wikidata",
            contexto=(
                f"[Wikidata — sin entidades]\n"
                f"No encontré entidades para «{tema}».\n"
                "Instrucción: Responde con conocimiento general."
            ),
            metadata={"wikidata_error": "sin_resultados", "tema": tema},
        )

    entidad = resultados[0]
    entity_id = entidad.get("id", "")
    etiqueta = entidad.get("label") or tema
    descripcion = entidad.get("description") or ""

    contexto = f"""[Wikidata — {etiqueta}]
ID: {entity_id}
{f"Descripción: {descripcion}" if descripcion else ""}
URL: https://www.wikidata.org/wiki/{entity_id}

Instrucción: Usa estos datos estructurados para enriquecer la respuesta con hechos verificables."""

    return ResultadoConector(
        nombre="wikidata",
        contexto=contexto.strip(),
        metadata={
            "wikidata_id": entity_id,
            "wikidata_label": etiqueta,
        },
    )


def consultar_busqueda_web(tema: str) -> ResultadoConector | None:
    """Búsqueda web ligera vía DuckDuckGo Instant Answer."""
    return memoizar(
        f"busqueda:{tema.lower()}",
        lambda: _consultar_busqueda_sin_cache(tema),
        ttl=600,
    )


def _consultar_busqueda_sin_cache(tema: str) -> ResultadoConector | None:
    params = urllib.parse.urlencode({
        "q": tema,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1",
    })
    datos = _wiki_get(f"{DDG_API}?{params}")
    if not isinstance(datos, dict):
        return None

    abstracto = (datos.get("AbstractText") or datos.get("Abstract") or "").strip()
    fuente = (datos.get("AbstractSource") or "").strip()
    url = (datos.get("AbstractURL") or "").strip()

    if not abstracto:
        related = datos.get("RelatedTopics") or []
        snippets: list[str] = []
        for item in related[:3]:
            if isinstance(item, dict) and item.get("Text"):
                snippets.append(str(item["Text"])[:200])
        if snippets:
            abstracto = "\n".join(f"- {s}" for s in snippets)
        else:
            return ResultadoConector(
                nombre="busqueda",
                contexto=(
                    f"[Búsqueda web — sin resumen instantáneo]\n"
                    f"No obtuve un resumen directo para «{tema}».\n"
                    "Instrucción: Responde con tu conocimiento y sugiere refinar la búsqueda."
                ),
                metadata={"busqueda_error": "sin_resumen", "tema": tema},
            )

    contexto = f"""[Búsqueda web — DuckDuckGo]
Consulta: {tema}
{abstracto}
{f"Fuente: {fuente}" if fuente else ""}
{f"URL: {url}" if url else ""}

Instrucción: Usa estos resultados como referencia factual reciente."""

    return ResultadoConector(
        nombre="busqueda",
        contexto=contexto.strip(),
        metadata={"busqueda_tema": tema, "busqueda_fuente": fuente},
    )


def consultar_noticias(tema: str, max_items: int = 5) -> ResultadoConector | None:
    """Consulta titulares recientes vía Google News RSS (es)."""
    return memoizar(
        f"noticias:{tema.lower()}",
        lambda: _consultar_noticias_sin_cache(tema, max_items),
        ttl=300,
    )


def _consultar_noticias_sin_cache(tema: str, max_items: int = 5) -> ResultadoConector | None:
    query = urllib.parse.quote(tema)
    url = GOOGLE_NEWS_RSS.format(query=query)
    xml_texto = _http_get_text(url)
    root = ET.fromstring(xml_texto)

    items: list[tuple[str, str]] = []
    for item in root.findall(".//item")[:max_items]:
        titulo = (item.findtext("title") or "").strip()
        enlace = (item.findtext("link") or "").strip()
        if titulo:
            items.append((titulo, enlace))

    if not items:
        return ResultadoConector(
            nombre="noticias",
            contexto=(
                f"[Noticias — sin titulares]\n"
                f"No encontré titulares recientes para «{tema}».\n"
                "Instrucción: Informa al usuario y sugiere refinar el tema."
            ),
            metadata={"noticias_error": "sin_titulares", "tema": tema},
        )

    lineas = [f"[Noticias recientes — {tema}]", "Titulares:"]
    for i, (titulo, enlace) in enumerate(items, 1):
        extra = f" ({enlace})" if enlace else ""
        lineas.append(f"{i}. {titulo}{extra}")

    lineas.append(
        "Instrucción: Resume estos titulares en español dominicano. "
        "Indica que provienen de fuentes de noticias recientes."
    )

    return ResultadoConector(
        nombre="noticias",
        contexto="\n".join(lineas),
        metadata={"noticias_tema": tema, "noticias_count": len(items)},
    )


class ConectorClima:
    nombre = "clima"

    def aplica(self, entrada: str, **kwargs: Any) -> bool:
        return clima.es_consulta_clima(entrada)

    def consultar(self, entrada: str, **kwargs: Any) -> ResultadoConector | None:
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")
        clave = f"clima:{entrada.strip().lower()}:{lat}:{lon}"

        def _fetch() -> ResultadoConector | None:
            resultado = clima.preparar_contexto_clima(entrada, lat=lat, lon=lon)
            if not resultado:
                return None
            meta: dict[str, Any] = {}
            if resultado.necesita_ubicacion:
                meta["clima_necesita_ubicacion"] = True
            if resultado.error:
                meta["clima_error"] = resultado.error
            return ResultadoConector(
                nombre=self.nombre,
                contexto=resultado.contexto,
                metadata=meta,
            )

        return memoizar(clave, _fetch, ttl=600)


class ConectorWikipedia:
    nombre = "wikipedia"

    def aplica(self, entrada: str, **kwargs: Any) -> bool:
        return es_consulta_wikipedia(entrada)

    def consultar(self, entrada: str, **kwargs: Any) -> ResultadoConector | None:
        tema = extraer_tema_wikipedia(entrada)
        if not tema:
            return None
        try:
            return consultar_wikipedia(tema)
        except urllib.error.URLError:
            return ResultadoConector(
                nombre=self.nombre,
                contexto=(
                    "[Wikipedia — sin conexión]\n"
                    "No pude conectar con Wikipedia en este momento.\n"
                    "Instrucción: Responde con tu conocimiento general."
                ),
                metadata={"wikipedia_error": "conexion_fallida"},
            )
        except Exception:
            return ResultadoConector(
                nombre=self.nombre,
                contexto=(
                    "[Wikipedia — error]\n"
                    "Ocurrió un error al consultar Wikipedia.\n"
                    "Instrucción: Continúa la conversación sin depender de la wiki."
                ),
                metadata={"wikipedia_error": "error_desconocido"},
            )


class ConectorWikidata:
    nombre = "wikidata"

    def aplica(self, entrada: str, **kwargs: Any) -> bool:
        return es_consulta_wikidata(entrada)

    def consultar(self, entrada: str, **kwargs: Any) -> ResultadoConector | None:
        tema = extraer_tema_wikipedia(entrada) or extraer_tema_busqueda(entrada)
        if not tema:
            return None
        try:
            return consultar_wikidata(tema)
        except urllib.error.URLError:
            return ResultadoConector(
                nombre=self.nombre,
                contexto=(
                    "[Wikidata — sin conexión]\n"
                    "No pude conectar con Wikidata.\n"
                    "Instrucción: Continúa sin datos estructurados."
                ),
                metadata={"wikidata_error": "conexion_fallida"},
            )
        except Exception:
            return ResultadoConector(
                nombre=self.nombre,
                contexto=(
                    "[Wikidata — error]\n"
                    "Error al consultar Wikidata.\n"
                    "Instrucción: Responde con conocimiento general."
                ),
                metadata={"wikidata_error": "error_desconocido"},
            )


class ConectorBusqueda:
    nombre = "busqueda"

    def aplica(self, entrada: str, **kwargs: Any) -> bool:
        return es_consulta_busqueda(entrada)

    def consultar(self, entrada: str, **kwargs: Any) -> ResultadoConector | None:
        tema = extraer_tema_busqueda(entrada)
        if not tema:
            return None
        try:
            return consultar_busqueda_web(tema)
        except urllib.error.URLError:
            return ResultadoConector(
                nombre=self.nombre,
                contexto=(
                    "[Búsqueda web — sin conexión]\n"
                    "No pude conectar con el servicio de búsqueda.\n"
                    "Instrucción: Responde con tu conocimiento."
                ),
                metadata={"busqueda_error": "conexion_fallida"},
            )
        except Exception:
            return ResultadoConector(
                nombre=self.nombre,
                contexto=(
                    "[Búsqueda web — error]\n"
                    "Error en la búsqueda web.\n"
                    "Instrucción: Continúa la conversación normalmente."
                ),
                metadata={"busqueda_error": "error_desconocido"},
            )


class ConectorNoticias:
    nombre = "noticias"

    def aplica(self, entrada: str, **kwargs: Any) -> bool:
        return es_consulta_noticias(entrada)

    def consultar(self, entrada: str, **kwargs: Any) -> ResultadoConector | None:
        tema = extraer_tema_noticias(entrada)
        if not tema:
            return None
        try:
            return consultar_noticias(tema)
        except urllib.error.URLError:
            return ResultadoConector(
                nombre=self.nombre,
                contexto=(
                    "[Noticias — sin conexión]\n"
                    "No pude obtener titulares en este momento.\n"
                    "Instrucción: Responde con contexto general."
                ),
                metadata={"noticias_error": "conexion_fallida"},
            )
        except ET.ParseError:
            return ResultadoConector(
                nombre=self.nombre,
                contexto=(
                    "[Noticias — error de formato]\n"
                    "No pude interpretar el feed de noticias.\n"
                    "Instrucción: Continúa sin titulares externos."
                ),
                metadata={"noticias_error": "parse_error"},
            )
        except Exception:
            return ResultadoConector(
                nombre=self.nombre,
                contexto=(
                    "[Noticias — error]\n"
                    "Ocurrió un error al consultar noticias.\n"
                    "Instrucción: Responde con tu conocimiento."
                ),
                metadata={"noticias_error": "error_desconocido"},
            )


_CONECTORES: list[ConectorConocimiento] = [
    ConectorClima(),
    ConectorWikipedia(),
    ConectorWikidata(),
    ConectorBusqueda(),
    ConectorNoticias(),
]


def registrar_conector(conector: ConectorConocimiento) -> None:
    """Añade un conector sin duplicar los existentes."""
    if any(c.nombre == conector.nombre for c in _CONECTORES):
        return
    _CONECTORES.append(conector)


def listar_conectores() -> list[str]:
    return [c.nombre for c in _CONECTORES]


def consultar_conectores(
    entrada: str,
    *,
    lat: float | None = None,
    lon: float | None = None,
    forzar: set[str] | None = None,
) -> tuple[list[str], list[ResultadoConector]]:
    """Ejecuta conectores aplicables y devuelve contextos."""
    bloques: list[ResultadoConector] = []
    activos: list[str] = []

    for conector in _CONECTORES:
        if forzar is not None and conector.nombre not in forzar:
            continue
        if forzar is None and not conector.aplica(entrada, lat=lat, lon=lon):
            continue

        resultado = conector.consultar(entrada, lat=lat, lon=lon)
        if resultado:
            bloques.append(resultado)
            activos.append(conector.nombre)

    return activos, bloques
