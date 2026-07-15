"""Smoke tests — verifican que la API arranca y responde."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient


def test_salud_responde_ok():
    from app import app

    client = TestClient(app)
    res = client.get("/api/salud")
    assert res.status_code == 200
    data = res.json()
    assert data["estado"] == "ok"
    assert data["servicio"] == "Salomón AI"


def test_manifest_webmanifest():
    from app import app

    client = TestClient(app)
    res = client.get("/manifest.webmanifest")
    assert res.status_code == 200
    assert "application/manifest+json" in res.headers.get("content-type", "")


def test_chat_sin_auth_cuando_no_hay_clave():
    from app import app

    client = TestClient(app)
    res = client.post("/api/chat", json={"mensaje": "Hola"})
    assert res.status_code == 200
    data = res.json()
    assert "texto" in data
    assert "session_id" in data


def test_chat_rechaza_sin_api_key(monkeypatch):
    import settings

    monkeypatch.setattr(settings, "SALOMON_API_KEY", "clave-secreta-test")
    from app import app

    client = TestClient(app)
    res = client.post("/api/chat", json={"mensaje": "Hola"})
    assert res.status_code == 401

    res_ok = client.post(
        "/api/chat",
        json={"mensaje": "Hola"},
        headers={"X-API-Key": "clave-secreta-test"},
    )
    assert res_ok.status_code == 200


def test_llm_modulo_exporta_funciones():
    from cognicion.llm import (
        analizar_imagen_gemini,
        chat_con_historial,
        gemini_disponible,
        generar_texto,
    )

    assert callable(gemini_disponible)
    assert callable(chat_con_historial)
    assert callable(generar_texto)
    assert callable(analizar_imagen_gemini)
    assert gemini_disponible() == bool(os.getenv("GEMINI_API_KEY", "").strip())
