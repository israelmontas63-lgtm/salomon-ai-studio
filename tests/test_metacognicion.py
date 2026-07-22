# -*- coding: utf-8 -*-
"""Tests metacognición estructural — auto-consciencia y límites."""

from __future__ import annotations


def test_explicar_fallo_pide_ingenieria():
    from cognicion.autonoma.metacognicion import explicar_fallo_a_israel

    msg = explicar_fallo_a_israel(
        "tts",
        error="elevenlabs auth failed",
        categoria="auth_key",
    )
    assert "Israel" in msg
    assert "Capa 4" in msg
    assert "metacognitivo" in msg.lower() or "Diagnóstico" in msg


def test_pregunta_metacognitiva_y_respuesta():
    from cognicion.autonoma.metacognicion import (
        es_pregunta_metacognitiva,
        respuesta_autoconciencia,
    )
    from cognicion.core_identity_engine import obtener_identity_engine

    assert es_pregunta_metacognitiva("¿Cuáles son tus límites?")
    texto = respuesta_autoconciencia("tus capacidades")
    assert "Salomón" in texto
    assert "8 capas" in texto or "capas" in texto.lower()

    pack = obtener_identity_engine().consultar("¿Cuáles son tus límites?")
    assert pack and pack.get("match")
    assert pack.get("protocolo") == "METACOGNICION_ESTRUCTURAL"
    assert "Israel" in (pack.get("texto") or "")


def test_estado_capacidades_no_secretos():
    from cognicion.autonoma.metacognicion import estado_capacidades, registrar_y_explicar

    st = estado_capacidades()
    assert st["ok"] is True
    assert st["muta_fuentes"] is False
    assert "capacidades" in st
    assert "llm" in st["capacidades"]
    blob = str(st)
    assert "sk-" not in blob

    pack = registrar_y_explicar(
        capacidad="media_imagen",
        origen="test",
        error="fal timeout",
        auto_reparar=True,
    )
    assert pack["muta_fuentes"] is False
    assert pack.get("mensaje_israel")
    assert pack.get("diagnostico", {}).get("layer_id") == 6
