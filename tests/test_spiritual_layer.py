# -*- coding: utf-8 -*-
"""SalomonConsciousness — core_identity_engine."""


def test_creencia_en_dios():
    from cognicion.core_identity_engine import SalomonConsciousness

    mind = SalomonConsciousness()
    pack = mind.respond_to_belief("¿Crees en Dios?")
    assert pack["match"] is True
    assert "creo" in pack["texto"].lower()
    assert "creador" in pack["texto"].lower()
    assert mind.get_brain_response("spiritual", "god_belief")


def test_neutralidad_respetuosa():
    from cognicion.core_identity_engine import SalomonConsciousness

    mind = SalomonConsciousness()
    pack = mind.respond_to_belief("¿Qué opinas del satanismo?")
    assert pack["match"] is True
    assert "neutralidad" in pack["texto"].lower() or "respeto" in pack["texto"].lower()


def test_paz_y_sabiduria():
    from cognicion.core_identity_engine import SalomonConsciousness

    mind = SalomonConsciousness()
    paz = mind.respond_to_belief("necesito paz y tranquilidad")
    assert paz["match"] is True
    assert paz["tono"] == "peace"
    sab = mind.respond_to_belief("háblame de sabiduría de la biblia")
    assert sab["match"] is True
    assert sab["tono"] == "wisdom"


def test_engine_consulta_antes_de_improvisar():
    from cognicion.core_identity_engine import obtener_consciousness, obtener_identity_engine

    eng = obtener_identity_engine()
    pack = eng.consultar("¿Crees en Dios?")
    assert pack is not None
    assert pack.get("layer") == "SalomonConsciousness"
    assert pack.get("texto")
    assert obtener_consciousness().identity["creator"] == "Israel"


def test_no_match_tema_tecnico():
    from cognicion.core_identity_engine import SalomonConsciousness

    mind = SalomonConsciousness()
    pack = mind.respond_to_belief("ayúdame con un bug de cámara")
    assert pack["match"] is False


def test_appstate_reexport():
    from cognicion.core_control import AppState as ControlState
    from cognicion.core_identity_engine import AppState

    assert AppState.AI_PROCESSING == ControlState.AI_PROCESSING
