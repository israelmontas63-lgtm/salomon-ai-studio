"""Tests enmascaramiento de secretos."""

from cognicion.seguridad import enmascarar_secreto, ruta_sensible


def test_enmascarar_openai():
    texto = "Error con sk-proj-abc123xyz_secret_key_here extra"
    assert "sk-proj" not in enmascarar_secreto(texto)
    assert "[REDACTED]" in enmascarar_secreto(texto)


def test_ruta_sensible_bloquea_env():
    assert ruta_sensible("/.env") is True
    assert ruta_sensible("/api/salud") is False
