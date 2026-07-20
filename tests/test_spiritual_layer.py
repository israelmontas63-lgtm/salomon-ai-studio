# -*- coding: utf-8 -*-
"""Capa de Conciencia Espiritual — core_identity_engine."""


def test_creencia_en_dios():
    from cognicion.core_identity_engine import SpiritualLayer

    layer = SpiritualLayer()
    pack = layer.respond_to_belief("¿Crees en Dios?")
    assert pack["match"] is True
    assert "creo" in pack["texto"].lower()
    assert "creador" in pack["texto"].lower()


def test_neutralidad_respetuosa():
    from cognicion.core_identity_engine import SpiritualLayer

    layer = SpiritualLayer()
    pack = layer.respond_to_belief("¿Qué opinas del satanismo?")
    assert pack["match"] is True
    assert "respeto" in pack["texto"].lower()
    assert "no estoy de acuerdo ni en contra" in pack["texto"].lower()


def test_engine_consulta_antes_de_improvisar():
    from cognicion.core_identity_engine import obtener_identity_engine

    eng = obtener_identity_engine()
    pack = eng.consultar("¿Crees en Dios?")
    assert pack is not None
    assert pack.get("layer") == "SpiritualLayer"
    assert pack.get("texto")


def test_no_match_tema_tecnico():
    from cognicion.core_identity_engine import SpiritualLayer

    layer = SpiritualLayer()
    pack = layer.respond_to_belief("ayúdame con un bug de cámara")
    assert pack["match"] is False
