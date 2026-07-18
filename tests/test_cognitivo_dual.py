# -*- coding: utf-8 -*-
"""Tests Cerebro Cognitivo Dual (Despertar)."""

from __future__ import annotations

from cognicion.cognitivo.claridad import filtrar_claridad
from cognicion.cognitivo.despertar import (
    ciclo_pre_tarea,
    consolidar_sesion,
    estado_cognitivo_dual,
    registrar_correccion,
)
from cognicion.cognitivo.episodica import FRASE_APRENDIZAJE, es_correccion_usuario


def test_filtro_claridad_intencion():
    r = filtrar_claridad("eh este, por favor, implementa el login ya")
    assert r["ok"] is True
    assert r["deseo"] == "accion"
    assert "login" in r["intencion_central"].lower() or "implementa" in r["enfocado"].lower()


def test_detecta_correccion():
    assert es_correccion_usuario("está mal, corrige el tono")
    assert not es_correccion_usuario("explica la fotosíntesis")


def test_ciclo_pre_tarea():
    pre = ciclo_pre_tarea("explica qué es la memoria episódica", session_id="test-dual")
    assert pre["ok"] is True
    assert pre["claridad"]["ok"] is True
    assert pre["critico"]["ok"] is True


def test_registrar_correccion_frase():
    apr = registrar_correccion(
        "te equivocaste con el saludo, sé más sobrio",
        session_id="test-dual",
        causa_raiz="desajuste_de_estilo",
    )
    assert apr["ok"] is True
    assert apr["frase"] == FRASE_APRENDIZAJE
    assert "aprendido" in apr["mensaje_israel"].lower()


def test_consolidar_sesion():
    out = consolidar_sesion("test-dual", notas="Sesión de despertar")
    assert out.get("ok") is True or out.get("resumen")
    assert "Consolidación" in (out.get("resumen") or "")


def test_estado_y_api(monkeypatch):
    st = estado_cognitivo_dual()
    assert st["protocolo"] == "CEREBRO_COGNITIVO_DUAL"
    assert "episodica" in st["capas"]["memoria"]

    import settings

    monkeypatch.setattr(settings, "SALOMON_API_KEY", "")
    from fastapi.testclient import TestClient
    from app import app

    client = TestClient(app)
    res = client.get("/api/cognitivo/estado")
    assert res.status_code == 200
    assert res.json()["frase_aprendizaje"] == FRASE_APRENDIZAJE
