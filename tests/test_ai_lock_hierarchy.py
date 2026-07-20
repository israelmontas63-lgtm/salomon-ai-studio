# -*- coding: utf-8 -*-
"""Jerarquía app_state / handle_central_button_click."""

from __future__ import annotations


def test_app_state_y_bloqueo_secundario():
    from cognicion import ai_lock

    ai_lock.liberar(reason="test_reset")
    assert ai_lock.app_state["is_ai_active"] is False

    assert ai_lock.ui_layer_manager("camera")["allowed"] is True

    ai_lock.activar(reason="test")
    assert ai_lock.app_state["is_ai_active"] is True
    gate = ai_lock.ui_layer_manager("camera")
    assert gate["blocked"] is True
    assert gate["allowed"] is False
    assert "prioridad de IA" in gate["mensaje"]
    ai_lock.liberar(reason="test_done")
    assert ai_lock.is_ai_active() is False


def test_handle_central_only_activate():
    from cognicion import ai_lock

    ai_lock.liberar(reason="reset")
    pack = ai_lock.handle_central_button_click("", only_activate=True)
    assert pack["is_ai_active"] is True
    assert ai_lock.is_ai_active() is True
    ai_lock.liberar(reason="done")


def test_api_secondary_y_lock(client_factory=None):
    from fastapi.testclient import TestClient

    from app import app

    with TestClient(app) as client:
        r = client.post("/api/ai/lock", json={"activo": True, "reason": "pytest"})
        assert r.status_code == 200
        assert r.json()["is_ai_active"] is True

        s = client.post("/api/ai/secondary", json={"accion": "camera"})
        assert s.status_code == 200
        assert s.json()["blocked"] is True

        client.post("/api/ai/lock", json={"activo": False, "reason": "pytest_done"})
        s2 = client.post("/api/ai/secondary", json={"accion": "camera"})
        assert s2.json()["blocked"] is False


def test_finally_restaura_aunque_falle_el_cerebro(monkeypatch):
    from cognicion import ai_lock

    ai_lock.liberar(reason="reset")

    def _boom(*_a, **_k):
        raise RuntimeError("fallo_simulado")

    monkeypatch.setattr(ai_lock, "execute_salomon_brain_process", _boom)
    pack = ai_lock.handle_central_button_click(
        "hola",
        obtener_sesion=lambda _sid: ("s1", object()),
    )
    assert pack["ok"] is False
    assert pack.get("restaurado") is True
    assert ai_lock.is_ai_active() is False
    assert "fallo_simulado" in (pack.get("error") or "")
