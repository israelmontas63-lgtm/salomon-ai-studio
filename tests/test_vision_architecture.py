# -*- coding: utf-8 -*-
"""SalomonVisionArchitecture — aislamiento de capas y macro/micro."""


def test_physical_dirs_and_isolation():
    from cognicion.core_vision_engine import obtener_vision_architecture

    arch = obtener_vision_architecture()
    pack = arch.verify_layer_isolation()
    assert pack["ok"] is True
    assert pack["layers"]["ui_layer"]["exists"]
    assert pack["layers"]["capture_layer"]["exists"]
    assert pack["layers"]["macro_micro_engine"]["exists"]
    assert pack["layers"]["brain_bridge"]["exists"]


def test_resolve_focus_modes():
    from cognicion.core_vision_engine import obtener_vision_architecture

    arch = obtener_vision_architecture()
    assert arch.resolve_focus_mode("macro") == "macro"
    assert arch.resolve_focus_mode("micro") == "micro"
    assert arch.resolve_focus_mode("continuous") == "continuous"
    prompt_m = arch.analysis_prompt("macro", "mira esto")
    assert "MACRO" in prompt_m
    prompt_w = arch.analysis_prompt("micro", "escena")
    assert "panorámico" in prompt_w.lower() or "MICRO" in prompt_w


def test_normalize_capture_layer():
    from views.capture import normalize_frame_payload

    # 1x1 PNG
    tiny = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    frame = normalize_frame_payload("data:image/png;base64," + tiny, mime="image/png")
    assert frame["ok"] is True
    assert frame["layer"] == "capture_layer"
    assert frame["imagen_mime"] == "image/png"


def test_ui_layer_does_not_import_analysis_logic():
    import views.ui_layer as ui
    import views.analysis as analysis

    assert "analyze_frame_modes" not in dir(ui)
    assert hasattr(analysis, "analyze_frame_modes")
    st = ui.ui_layer_status()
    assert st["mixes_with_analysis"] is False


def test_brain_bridge_status():
    from core.brain_connector import bridge_status

    st = bridge_status()
    assert st["middleware"] is False
    assert "brain_connector" in st["path"]
