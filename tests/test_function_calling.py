"""Tests de la capa function-calling (Fase 2 OS)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


def test_schemas_genera_herramientas():
    from cognicion.capas.function_calling.schemas import construir_esquemas_openai, herramientas_permitidas

    esquemas = construir_esquemas_openai()
    nombres = {e["function"]["name"] for e in esquemas}
    assert "corregir" in nombres
    assert "traducir" in nombres
    assert "cli" not in nombres
    assert len(esquemas) == len(herramientas_permitidas())


def test_detector_activa_con_palabra_clave():
    from cognicion.capas.function_calling.detector import debe_usar_function_calling

    activar, sugeridas = debe_usar_function_calling("Por favor traduce esto al inglés")
    assert activar is True
    assert "traducir" in sugeridas


def test_detector_no_activa_chat_normal(monkeypatch):
    import settings

    monkeypatch.setattr(settings, "FUNCTION_CALLING_SIEMPRE", False)
    from cognicion.capas.function_calling.detector import debe_usar_function_calling

    activar, _ = debe_usar_function_calling("Hola, ¿cómo estás?")
    assert activar is False


def test_ejecutor_corregir():
    from cognicion.capas.function_calling.ejecutor import ejecutar_llamada

    res = ejecutar_llamada("corregir", {"texto": "hola munod"})
    assert res.exito is True
    assert res.herramienta_id == "corregir"


def test_ejecutor_rechaza_cli():
    from cognicion.capas.function_calling.ejecutor import ejecutar_llamada

    res = ejecutar_llamada("cli", {"comando": "help"})
    assert res.exito is False
    assert "no permitida" in (res.error or "").lower()


def test_puente_fallback_sin_proveedor(monkeypatch):
    import settings

    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    from cognicion.capas.function_calling.puente import chat_con_herramientas

    res = chat_con_herramientas("traduce hola", [], "Eres Salomón")
    assert res.usado is False


def test_puente_ejecuta_herramienta_mock(monkeypatch):
    import settings

    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")

    tool_call = MagicMock()
    tool_call.id = "call_1"
    tool_call.function.name = "ayuda"
    tool_call.function.arguments = "{}"

    msg_tools = MagicMock()
    msg_tools.content = ""
    msg_tools.tool_calls = [tool_call]

    msg_final = MagicMock()
    msg_final.content = "Aquí tienes la ayuda del sistema."
    msg_final.tool_calls = None

    choice_tools = MagicMock()
    choice_tools.message = msg_tools
    choice_final = MagicMock()
    choice_final.message = msg_final

    resp_tools = MagicMock()
    resp_tools.choices = [choice_tools]
    resp_final = MagicMock()
    resp_final.choices = [choice_final]

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [resp_tools, resp_final]

    with patch("cognicion.capas.function_calling.puente._cliente_openai", return_value=(mock_client, "gpt-4o-mini")):
        from cognicion.capas.function_calling.puente import chat_con_herramientas

        res = chat_con_herramientas("necesito ayuda del sistema", [], "Eres Salomón")
        assert res.usado is True
        assert "ayuda" in res.texto.lower() or len(res.texto) > 0
        assert res.metadata.get("herramientas_usadas")


def test_api_estado_capa():
    from app import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    res = client.get("/api/capas/function-calling/estado")
    assert res.status_code == 200
    data = res.json()
    assert data["capa"] == "function_calling"
    assert "herramientas_llm" in data
