# -*- coding: utf-8 -*-
"""Tests Cerebro Ejecutivo (sin red real)."""

from __future__ import annotations

import pytest

from cognicion.ejecutivo.contactos import identificar_contacto, _heuristica
from cognicion.ejecutivo.exclusividad import exigir_contexto_israel, sello_propiedad
from cognicion.ejecutivo.orquestador import estado_ejecutivo, informe_ejecutivo


FAKE_WEB = {
    "exito": True,
    "resultados": [
        {
            "titulo": "Tendencia demo",
            "snippet": "Señal de mercado educativa.",
            "url": "https://example.com/demo",
        }
    ],
    "respuesta_directa": "Mercado en consolidación (demo).",
}


@pytest.fixture(autouse=True)
def _mock_busqueda(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "cognicion.busqueda.agente.buscar_web",
        lambda q: FAKE_WEB,
    )
    # Evitar LLM real
    monkeypatch.setattr("cognicion.llm.llm_disponible", lambda: False)


def test_exclusividad_israel():
    assert exigir_contexto_israel("Israel Montas")["ok"] is True
    assert exigir_contexto_israel("otro")["ok"] is False
    sello = sello_propiedad()
    assert sello["exclusividad"] is True
    assert sello["owner"] == "Israel Montas"
    assert "bancarias" in sello["disclaimer"].lower() or "bancarias" in sello["disclaimer"]


def test_heuristica_rd():
    h = _heuristica("+18095551212")
    assert h["clasificacion_heuristica"] == "posible_rd_local"


def test_contacto_sin_numero():
    r = identificar_contacto("")
    assert r["ok"] is False


def test_informe_mercados():
    pack = informe_ejecutivo(modulo="mercados", consulta="tendencias IA")
    assert pack["ok"] is True
    assert pack["propiedad_privada"] is True
    assert "mercados" in pack["resultados"]
    assert pack["resultados"]["mercados"]["ok"] is True


def test_informe_contenido_y_oportunidades():
    pack = informe_ejecutivo(modulo="contenido", tema="ciencia viral")
    assert pack["ok"] is True
    assert pack["resultados"]["contenido"]["ok"] is True
    pack2 = informe_ejecutivo(modulo="oportunidades")
    assert pack2["resultados"]["oportunidades"]["ok"] is True


def test_estado_api_shape():
    st = estado_ejecutivo()
    assert "mercados" in st["modulos"]
    assert st["metodologia"]["paso_1"].startswith("SBI-PRO")


def test_api_estado(monkeypatch: pytest.MonkeyPatch):
    import settings

    monkeypatch.setattr(settings, "SALOMON_API_KEY", "")
    from fastapi.testclient import TestClient
    from app import app

    client = TestClient(app)
    res = client.get("/api/ejecutivo/estado")
    assert res.status_code == 200
    assert res.json()["protocolo"] == "CEREBRO_EJECUTIVO"
