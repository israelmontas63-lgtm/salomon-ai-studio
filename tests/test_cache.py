"""Tests caché de conectores."""

from __future__ import annotations

from unittest.mock import patch

from cognicion.cache import limpiar, memoizar, obtener


def test_memoizar_ejecuta_una_vez():
    limpiar()
    llamadas = {"n": 0}

    def factory():
        llamadas["n"] += 1
        return "valor"

    assert memoizar("clave-test", factory, ttl=60) == "valor"
    assert memoizar("clave-test", factory, ttl=60) == "valor"
    assert llamadas["n"] == 1
    assert obtener("clave-test") == "valor"


def test_wikipedia_usa_cache():
    limpiar()
    fake_search = {"query": {"search": [{"title": "Test"}]}}
    fake_summary = {
        "extract": "Texto de prueba.",
        "description": "Desc",
        "content_urls": {"desktop": {"page": "https://example.com"}},
    }

    with patch("cognicion.conectores._wiki_get", side_effect=[fake_search, fake_summary, fake_search, fake_summary]):
        from cognicion.conectores import consultar_wikipedia

        r1 = consultar_wikipedia("Test")
        r2 = consultar_wikipedia("Test")

    assert r1 is not None and r2 is not None
    assert r1.contexto == r2.contexto
