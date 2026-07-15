"""Tests LLM multi-proveedor, TTS async y noticias."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient


def test_proveedores_registrados():
    from cognicion.llm import listar_proveedores

    nombres = listar_proveedores()
    assert "gemini" in nombres
    assert "openai" in nombres
    assert "groq" in nombres
    assert "local" in nombres


def test_llm_disponible_con_alguna_clave():
    from cognicion.llm import gemini_disponible, llm_disponible

    assert isinstance(llm_disponible(), bool)
    assert isinstance(gemini_disponible(), bool)


def test_fallback_local_cuando_todos_fallan(monkeypatch):
    import cognicion.llm as llm_mod

    class _Falla:
        nombre = "gemini"

        def disponible(self) -> bool:
            return True

        def chat_con_historial(self, *args, **kwargs) -> str:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")

        def generar_texto(self, *args, **kwargs) -> str:
            raise RuntimeError("429")

        def analizar_imagen(self, *args, **kwargs) -> str:
            raise RuntimeError("429")

    monkeypatch.setattr(llm_mod, "obtener_proveedor", lambda nombre=None: _Falla())
    monkeypatch.setattr(llm_mod, "_PROVEEDORES", {"gemini": _Falla(), "local": llm_mod.LocalProvider()})
    monkeypatch.setattr(llm_mod, "LLM_FALLBACK", True)
    monkeypatch.setattr(llm_mod, "LLM_LOCAL_FALLBACK", True)

    texto = llm_mod.chat_con_historial("Hola", [], "Eres Salomón")
    assert "Israel" in texto
    assert llm_mod.ultimo_uso_llm()["proveedor"] == "local"


def test_openai_provider_sin_clave():
    from cognicion.llm import OpenAIProvider

    proveedor = OpenAIProvider()
    assert proveedor.nombre == "openai"


def test_api_tts_endpoint():
    from app import app

    client = TestClient(app)
    res = client.post("/api/tts", json={"texto": "Hola"})
    assert res.status_code == 200
    data = res.json()
    assert "tts_disponible" in data
    assert "audio_base64" in data


def test_salud_incluye_tts_async():
    from app import app

    client = TestClient(app)
    res = client.get("/api/salud")
    assert res.status_code == 200
    assert "tts_async" in res.json()["cognicion"]


def test_conectores_incluye_noticias():
    from cognicion.conectores import es_consulta_noticias, listar_conectores

    assert "noticias" in listar_conectores()
    assert es_consulta_noticias("Últimas noticias de tecnología") is True


def test_consultar_noticias_mock_rss():
    rss = """<?xml version="1.0"?>
    <rss><channel>
      <item><title>Noticia A</title><link>https://example.com/a</link></item>
      <item><title>Noticia B</title><link>https://example.com/b</link></item>
    </channel></rss>"""

    with patch("cognicion.conectores._http_get_text", return_value=rss):
        from cognicion.conectores import consultar_noticias

        resultado = consultar_noticias("tecnología")

    assert resultado is not None
    assert resultado.nombre == "noticias"
    assert "Noticia A" in resultado.contexto


def test_clasificar_intencion_noticias():
    from cognicion.razonamiento.intencion import Intencion, clasificar_intencion

    assert clasificar_intencion("Noticias sobre inteligencia artificial") == Intencion.INVESTIGACION
