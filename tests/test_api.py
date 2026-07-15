"""Tests de API — historial, sesión, herramientas."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_historial_tras_chat():
    from app import app

    client = TestClient(app)
    chat = client.post("/api/chat", json={"mensaje": "Prueba historial"})
    assert chat.status_code == 200
    sid = chat.json()["session_id"]

    hist = client.get(f"/api/historial?session_id={sid}")
    assert hist.status_code == 200
    data = hist.json()
    assert data["session_id"] == sid
    assert len(data["mensajes"]) >= 2


def test_cognicion_estado_expone_kernel():
    from app import app

    client = TestClient(app)
    res = client.get("/api/cognicion/estado")
    assert res.status_code == 200
    data = res.json()
    assert "skills" in data
    assert "conectores" in data
    assert "proveedor_llm" in data
    assert data["pilares"]["aprendizaje"] is True


def test_herramientas_catalogo():
    from app import app

    client = TestClient(app)
    res = client.get("/api/herramientas")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 12
    assert any(h["id"] == "ayuda" for h in data["herramientas"])


def test_herramientas_ayuda():
    from app import app

    client = TestClient(app)
    res = client.get("/api/herramientas/ayuda")
    assert res.status_code == 200
    assert "titulo" in res.json()


def test_nuevo_chat_reiniciar():
    from app import app

    client = TestClient(app)
    chat = client.post("/api/chat", json={"mensaje": "Mensaje previo"})
    sid = chat.json()["session_id"]

    nuevo = client.post(f"/api/chat/nuevo?session_id={sid}&reiniciar=true")
    assert nuevo.status_code == 200
    assert nuevo.json()["session_id"] == sid

    hist = client.get(f"/api/historial?session_id={sid}")
    assert hist.status_code == 200
