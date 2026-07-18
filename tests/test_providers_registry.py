# -*- coding: utf-8 -*-
"""Provider Pattern — selección y validación de claves Render."""

from __future__ import annotations

import config.providers as providers
from cognicion.servicios.registry import ServiceRegistry


def test_cadena_llm_prioriza_gemini(monkeypatch):
    monkeypatch.setattr("settings.GEMINI_API_KEY", "g-key", raising=False)
    monkeypatch.setattr("settings.GROQ_API_KEY", "q-key", raising=False)
    monkeypatch.setattr("settings.OPENAI_API_KEY", "o-key", raising=False)
    # Re-import settings attrs used inside cadenas via settings module
    import settings as S

    monkeypatch.setattr(S, "GEMINI_API_KEY", "g-key")
    monkeypatch.setattr(S, "GROQ_API_KEY", "q-key")
    monkeypatch.setattr(S, "OPENAI_API_KEY", "o-key")

    slot = providers.seleccionar(providers.Servicio.LLM)
    assert slot is not None
    assert slot.nombre == "gemini"
    assert providers.cadena_nombres(providers.Servicio.LLM) == [
        "gemini",
        "groq",
        "openai",
    ]


def test_fallback_llm_sin_gemini(monkeypatch):
    import settings as S

    monkeypatch.setattr(S, "GEMINI_API_KEY", "")
    monkeypatch.setattr(S, "GROQ_API_KEY", "q-key")
    monkeypatch.setattr(S, "OPENAI_API_KEY", "o-key")

    slot = providers.seleccionar(providers.Servicio.LLM)
    assert slot is not None
    assert slot.nombre == "groq"


def test_validar_strict_sin_llm(monkeypatch):
    import settings as S

    monkeypatch.setattr(S, "GEMINI_API_KEY", "")
    monkeypatch.setattr(S, "GROQ_API_KEY", "")
    monkeypatch.setattr(S, "OPENAI_API_KEY", "")
    monkeypatch.setattr(S, "SBI_MODE", "soft")
    monkeypatch.setattr(S, "SBI_ENABLED", False)
    monkeypatch.setattr(S, "PROVIDERS_STRICT", True)

    try:
        providers.validar_entorno(strict=True)
        assert False, "debía lanzar ProviderConfigError"
    except providers.ProviderConfigError as exc:
        assert "LLM" in str(exc)


def test_sbi_flags_en_registry(monkeypatch):
    import settings as S

    monkeypatch.setattr(S, "SBI_ENABLED", True)
    monkeypatch.setattr(S, "SBI_MODE", "strict")
    reg = ServiceRegistry()
    sbi = reg.sbi_activo()
    assert sbi["enabled"] is True
    assert sbi["agents_gated"] is True


def test_media_cadena(monkeypatch):
    import settings as S

    monkeypatch.setattr(S, "FAL_KEY", "")
    monkeypatch.setattr(S, "REPLICATE_API_TOKEN", "r-token")
    slot = providers.seleccionar(providers.Servicio.MEDIA)
    assert slot is not None
    assert slot.nombre == "replicate"
