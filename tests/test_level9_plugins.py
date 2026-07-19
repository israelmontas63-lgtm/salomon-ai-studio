# -*- coding: utf-8 -*-
"""Level 9 — Plug-and-Play periféricas."""

from __future__ import annotations


def test_descubrir_plugins_tiene_manifests():
    from cognicion.plugins.cargador import descubrir_plugins, reiniciar_registro

    reiniciar_registro()
    plugins = descubrir_plugins()
    ids = {p["id"] for p in plugins}
    assert "function_calling" in ids
    assert "voice_core" in ids
    assert "vision_agent" in ids
    assert "home_gateway" in ids
    assert "audio_stack" in ids
    assert "media_stack" in ids
    assert "reconexion_perifericos" in ids


def test_activar_perifericas_level9():
    from cognicion.capas.loader import inicializar_capas
    from cognicion.plugins.cargador import estado_level9, reiniciar_registro

    reiniciar_registro()
    # Reset loader flag
    import cognicion.capas.loader as loader

    loader._inicializado = False
    res = inicializar_capas(None, force=True)
    assert res.get("voice_core") is True
    assert res.get("home_gateway") is True
    st = estado_level9()
    assert st["level"] == 9
    assert st["total"] >= 7
    assert st["activos"] >= 3
    assert st["ok"] is True


def test_hot_plug_sin_apagar_nucleo():
    from cognicion.plugins.cargador import hot_plug, reiniciar_registro

    reiniciar_registro()
    pack = hot_plug("voice_core", app=None)
    assert pack["ok"] is True
    assert pack["hot_plug"] is True
    assert pack["nucleo"] == "sin_apagado"


def test_api_level9():
    from fastapi.testclient import TestClient

    from app import app

    with TestClient(app) as client:
        r = client.get("/api/level9")
        assert r.status_code == 200
        data = r.json()
        assert data.get("level") == 9
        assert data.get("motor") == "plugins_capas"
        assert isinstance(data.get("plugins"), list)
        assert data.get("total", 0) >= 7
