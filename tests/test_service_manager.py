# -*- coding: utf-8 -*-
"""ServiceManager — despliegue neuronal / modo ejecución."""

from __future__ import annotations

from cognicion.servicios import ServiceManager, obtener_manager


def test_manager_singleton_es_ejecucion(monkeypatch):
    import settings as S

    monkeypatch.setattr(S, "MODO_EJECUCION", True)
    monkeypatch.setattr(S, "SBI_ENABLED", True)
    monkeypatch.setattr(S, "SBI_MODE", "soft")
    m = obtener_manager()
    assert isinstance(m, ServiceManager)
    assert m.modo_ejecucion() is True
    infra = m.infraestructura_lista()
    assert infra["modo"] == "ejecucion"
    assert infra["web_agentes"] is True


def test_hablar_texto_vacio():
    r = obtener_manager().hablar("   ")
    assert r.tts_disponible is False
    assert r.error == "texto_vacio"


def test_web_bloqueada_sin_autorizacion(monkeypatch):
    import settings as S

    monkeypatch.setattr(S, "MODO_EJECUCION", False)
    monkeypatch.setattr(S, "SBI_ENABLED", False)
    out = obtener_manager().buscar_web("noticias de hoy", origen="agente")
    assert out.get("ok") is False
    assert out.get("error") == "web_no_autorizada"
