# -*- coding: utf-8 -*-
"""Tests Self-Debug — clasificación y reparación segura (sin mutar fuentes)."""

from __future__ import annotations


def test_clasificar_cuota_y_saldo():
    from cognicion.autonoma.self_debug import clasificar_fallo

    assert clasificar_fallo(status_http=429) == "cuota"
    assert clasificar_fallo(mensaje="Insufficient Balance") == "saldo"
    assert clasificar_fallo(status_http=401) == "auth_key"
    assert clasificar_fallo(mensaje="elevenlabs timeout") == "multimedia_tts"


def test_registrar_y_reparar_no_muta_fuentes():
    from cognicion.autonoma.self_debug import registrar_fallo, estado_self_debug

    pack = registrar_fallo(
        origen="test.unit",
        mensaje="rate limit quota exceeded",
        status_http=429,
        auto_reparar=True,
    )
    assert pack["categoria"] == "cuota"
    assert pack["reparacion"].get("muta_fuentes") is False
    assert "propuesta" in pack
    st = estado_self_debug()
    assert st["muta_fuentes"] is False
    assert st["autopreservacion"] is True
    assert st["stats"]["capturados"] >= 1


def test_ciclo_autodiagnostico():
    from cognicion.autonoma.self_debug import ciclo_autodiagnostico

    ciclo = ciclo_autodiagnostico(reparar=True)
    assert ciclo["protocol"] == "SELF_DEBUG_AUTOREPAIR"
    assert ciclo["muta_fuentes"] is False
    assert "despues" in ciclo
