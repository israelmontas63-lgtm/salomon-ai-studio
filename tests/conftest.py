"""Fixtures — desactiva protección API en tests automáticos."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _tests_sin_salomon_api_key(monkeypatch):
    """Los tests no envían X-API-Key; evita 401 si .env tiene SALOMON_API_KEY."""
    monkeypatch.setenv("SALOMON_API_KEY", "")
    monkeypatch.setenv("SALOMON_ADMIN_KEY", "")
    import settings

    monkeypatch.setattr(settings, "SALOMON_API_KEY", "")
    monkeypatch.setattr(settings, "SALOMON_ADMIN_KEY", "")
    try:
        import app as app_module

        monkeypatch.setattr(app_module, "SALOMON_API_KEY", "")
    except ImportError:
        pass
