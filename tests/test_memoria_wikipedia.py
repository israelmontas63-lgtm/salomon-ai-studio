"""Tests memoria tipada y conector Wikipedia."""

from __future__ import annotations

from unittest.mock import patch

from cognicion.aprendizaje import procesar_turno
from cognicion.conectores import (
    ConectorWikipedia,
    consultar_wikipedia,
    es_consulta_wikipedia,
    extraer_tema_wikipedia,
    listar_conectores,
)
from cognicion.memoria.gestor import GestorMemoria
from cognicion.memoria.tipos import TipoMemoria
from cognicion.razonamiento.intencion import Intencion, clasificar_intencion
from persistencia.sesiones import asegurar_sesion, guardar_mensaje, inicializar, ultimos_mensajes


def test_tipos_memoria_siete_capas():
    assert len(TipoMemoria) == 7
    assert TipoMemoria.INMEDIATA.value == "inmediata"
    assert TipoMemoria.PREFERENCIAS.value == "preferencias"


def test_ultimos_mensajes_sqlite():
    inicializar()
    sid = "test-memoria-inmediata"
    asegurar_sesion(sid)
    guardar_mensaje(sid, "usuario", "Hola")
    guardar_mensaje(sid, "asistente", "Qué tal")

    msgs = ultimos_mensajes(sid, limite=2)
    assert len(msgs) == 2
    assert msgs[0]["rol"] == "usuario"


def test_gestor_memoria_inmediata():
    inicializar()
    sid = "test-gestor"
    asegurar_sesion(sid)
    guardar_mensaje(sid, "usuario", "Mensaje reciente")

    gestor = GestorMemoria(sid)
    ctx = gestor.memoria_inmediata()
    assert "Memoria inmediata" in ctx
    assert "Mensaje reciente" in ctx


def test_conectores_incluye_wikipedia():
    assert "wikipedia" in listar_conectores()


def test_es_consulta_wikipedia():
    assert es_consulta_wikipedia("¿Quién es Juan Bosch?") is True
    assert es_consulta_wikipedia("Hola") is False


def test_extraer_tema_wikipedia():
    tema = extraer_tema_wikipedia("¿Quién es Juan Bosch?")
    assert tema is not None
    assert "Juan Bosch" in tema


def test_clasificar_intencion_investigacion():
    assert clasificar_intencion("¿Qué es la fotosíntesis?") == Intencion.INVESTIGACION


def test_consultar_wikipedia_mock():
    fake_search = {
        "query": {"search": [{"title": "República Dominicana"}]}
    }
    fake_summary = {
        "extract": "La República Dominicana es un país de América.",
        "description": "País del Caribe",
        "content_urls": {"desktop": {"page": "https://es.wikipedia.org/wiki/RD"}},
    }

    with patch("cognicion.conectores._wiki_get", side_effect=[fake_search, fake_summary]):
        resultado = consultar_wikipedia("República Dominicana")

    assert resultado is not None
    assert resultado.nombre == "wikipedia"
    assert "República Dominicana" in resultado.contexto


def test_conector_wikipedia_aplica():
    conector = ConectorWikipedia()
    assert conector.aplica("Define la gravedad") is True


def test_aprendizaje_usa_capas_gestor():
    class GestorFake:
        activa = True
        preferencias: list[str] = []
        aprendizajes: list[str] = []

        def guardar_preferencia(self, texto: str) -> str | None:
            self.preferencias.append(texto)
            return "p1"

        def guardar_aprendizaje(self, texto: str, categoria: str = "contexto") -> str | None:
            self.aprendizajes.append(texto)
            return "a1"

        def guardar_proyecto(self, texto: str, nombre: str | None = None) -> str | None:
            return "p1"

    gestor = GestorFake()
    resultado = procesar_turno(
        "s1",
        "Recuerda que prefiero respuestas cortas",
        "Entendido.",
        gestor,  # type: ignore[arg-type]
    )
    assert resultado.procesado is True
    assert len(gestor.preferencias) >= 1


def test_memoria_proyecto_sqlite():
    from persistencia.sesiones import cargar_proyecto, guardar_proyecto, inicializar

    inicializar()
    sid = "test-proyecto-session"
    guardar_proyecto(sid, nombre="Salomón AI Studio", nota="Backend FastAPI + React")

    proj = cargar_proyecto(sid)
    assert proj is not None
    assert proj["nombre"] == "Salomón AI Studio"
    assert "FastAPI" in proj["contexto"]


def test_gestor_memoria_proyecto_contexto():
    from persistencia.sesiones import guardar_proyecto, inicializar

    inicializar()
    sid = "test-gestor-proyecto"
    guardar_proyecto(sid, nombre="Mi App", nota="Usamos SQLite y ChromaDB")

    gestor = GestorMemoria(sid)
    ctx, meta = gestor.memoria_proyecto()
    assert meta["proyecto_activo"] is True
    assert "Mi App" in ctx
    assert "SQLite" in ctx


def test_aprendizaje_detecta_proyecto():
    class GestorFake:
        activa = True
        proyectos: list[tuple[str, str | None]] = []

        def guardar_preferencia(self, texto: str) -> str | None:
            return None

        def guardar_aprendizaje(self, texto: str, categoria: str = "contexto") -> str | None:
            return None

        def guardar_proyecto(self, texto: str, nombre: str | None = None) -> str | None:
            self.proyectos.append((texto, nombre))
            return "ok"

    gestor = GestorFake()
    resultado = procesar_turno(
        "s-proj",
        "El proyecto se llama Salomón AI y estamos trabajando en memoria tipada",
        "Perfecto, Israel.",
        gestor,  # type: ignore[arg-type]
    )
    assert resultado.procesado is True
    assert resultado.metadata.get("proyecto_actualizado") is True
    assert len(gestor.proyectos) >= 1


def test_consultar_wikidata_mock():
    fake = {"search": [{"id": "Q786", "label": "República Dominicana", "description": "País"}]}

    with patch("cognicion.conectores._wiki_get", return_value=fake):
        from cognicion.conectores import consultar_wikidata

        resultado = consultar_wikidata("República Dominicana")

    assert resultado is not None
    assert resultado.nombre == "wikidata"
    assert "Q786" in resultado.contexto


def test_consultar_busqueda_mock():
    fake = {
        "AbstractText": "Python es un lenguaje de programación.",
        "AbstractSource": "Wikipedia",
        "AbstractURL": "https://example.com",
    }

    with patch("cognicion.conectores._wiki_get", return_value=fake):
        from cognicion.conectores import consultar_busqueda_web

        resultado = consultar_busqueda_web("Python programming")

    assert resultado is not None
    assert resultado.nombre == "busqueda"
    assert "Python" in resultado.contexto


def test_clasificar_busqueda_web():
    assert clasificar_intencion("Busca en internet: inteligencia artificial") == Intencion.INVESTIGACION
