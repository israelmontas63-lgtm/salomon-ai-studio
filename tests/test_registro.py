"""Tests registro estructurado."""

from cognicion.registro import configurar_registro, obtener_logger


def test_configurar_registro_idempotente():
    configurar_registro("WARNING")
    configurar_registro("WARNING")
    logger = obtener_logger("test")
    assert logger.name == "salomon.test"
    assert logger.level <= 30  # WARNING o más verboso según jerarquía
