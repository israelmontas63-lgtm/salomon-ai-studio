"""Tests registry de herramientas."""

from __future__ import annotations

import herramientas


def test_registry_registra_todas_las_herramientas():
    ids = {h.id for h in herramientas.listar_herramientas()}
    esperados = {
        "planes",
        "analiticas",
        "solar",
        "optimizar",
        "seguridad",
        "ayuda",
        "corregir",
        "traducir",
        "cli",
        "resumir",
        "backup_export",
        "backup_import",
    }
    assert esperados.issubset(ids)
    assert len(ids) >= len(esperados)


def test_ejecutar_herramienta_corregir():
    resultado = herramientas.ejecutar_herramienta("corregir", texto="hola mundo")
    assert "corregido" in resultado
    assert resultado["corregido"].endswith(".")


def test_ejecutar_herramienta_desconocida():
    resultado = herramientas.ejecutar_herramienta("no_existe")
    assert resultado["exito"] is False


def test_catalogo_herramientas():
    catalogo = herramientas.catalogo_herramientas()
    assert catalogo["total"] >= 12
    assert all("ruta" in h for h in catalogo["herramientas"])
