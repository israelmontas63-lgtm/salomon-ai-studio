"""Verificación interna — Núcleo v1.3 (voz, memoria, conectividad)."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_voice_orchestrator_activo():
    path = ROOT / "voice-orchestrator.py"
    assert path.is_file()
    spec = importlib.util.spec_from_file_location("voice_orchestrator", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    estado = mod.estado_voz()
    assert estado["flujo_salida_activo"] is True
    assert estado["audio_mime_default"] == "audio/mpeg"
    assert estado["version"] == "1.3"


def test_memory_controller_guardar_recuperar(tmp_path, monkeypatch):
    from cognicion.memoria import memory_controller as mc

    monkeypatch.setattr(mc, "_SESSIONS_JSON", tmp_path / "memoria_sesiones.json")
    ctrl = mc.MemoryController("test-v13")
    meta = ctrl.recordar_turno(
        "Mi proyecto se llama Salomón AI Studio",
        "Entendido, Israel. Lo recordaré.",
    )
    assert meta["historial_turnos"] >= 2
    ctx, info = ctrl.contexto_para_turno("¿Recuerdas cómo se llama mi proyecto?")
    assert "Salomón" in ctx or info.get("sesion_json")
    estado = ctrl.estado()
    assert estado["session_id"] == "test-v13"
    assert estado["historial_sesion"] >= 2


def test_busqueda_web_agente_importable():
    from cognicion.busqueda import necesita_busqueda_web, responder_con_busqueda
    from cognicion.busqueda import agente as agente_mod
    from settings import BUSQUEDA_WEB_AUTO

    assert BUSQUEDA_WEB_AUTO is True or BUSQUEDA_WEB_AUTO is False
    assert callable(necesita_busqueda_web)
    assert callable(responder_con_busqueda)
    assert hasattr(agente_mod, "buscar_web")
    assert necesita_busqueda_web(
        "Busca en la web sobre el clima de hoy en Santo Domingo"
    )
    assert not necesita_busqueda_web("qué película sobre el azul")
    assert not necesita_busqueda_web("busca películas")


def test_mime_defaults_mpeg():
    from cerebro import RespuestaSalomon
    from app import ChatResponse, TtsResponse, SessionResponse

    assert RespuestaSalomon(texto="ok").audio_mime == "audio/mpeg"
    assert ChatResponse.model_fields["audio_mime"].default == "audio/mpeg"
    assert TtsResponse.model_fields["audio_mime"].default == "audio/mpeg"
    assert SessionResponse.model_fields["audio_mime"].default == "audio/mpeg"


def test_orquestador_tiene_memory_y_busqueda():
    import inspect
    from cognicion.orquestador import MotorCognicion

    src = inspect.getsource(MotorCognicion.enriquecer_mensaje)
    assert "responder_con_busqueda" in src
    assert "MemoryController" in inspect.getsource(MotorCognicion) or "memory_controller" in src.lower()
    motor = MotorCognicion("test-orq-v13")
    assert motor.memory.session_id == "test-orq-v13"


def test_bridge_tts_fallback_presente():
    bridge = (ROOT / "studio" / "dist" / "salomon-orchestrator-bridge.js").read_text(
        encoding="utf-8"
    )
    assert "ensureVoiceOut" in bridge
    assert "nucleo-v1.3" in bridge
    assert "/api/tts" in bridge
