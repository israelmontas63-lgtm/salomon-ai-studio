# -*- coding: utf-8 -*-
"""Tests unitarios SBI-PRO — autenticación biométrica de voz (ligera)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from cognicion.seguridad import sbi_pro


@pytest.fixture()
def sbi_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    plantilla = tmp_path / "sbi_israel.json"
    monkeypatch.setenv("SBI_ENABLED", "true")
    monkeypatch.setenv("SBI_MODE", "soft")
    monkeypatch.setenv("SBI_THRESHOLD", "0.82")
    monkeypatch.setenv("SBI_ENROLL_TOKEN", "token-enroll-test")
    monkeypatch.setenv("SBI_RECOVERY_KEY", "recovery-israel-test")
    monkeypatch.setenv("SBI_TEMPLATE_SECRET", "firma-test")
    monkeypatch.setenv("SBI_OWNER_NAME", "Israel Monta")
    monkeypatch.setenv("SBI_TEMPLATE_PATH", str(plantilla))
    # settings ya cargó dotenv; el módulo lee os.getenv en runtime via _cfg()
    return plantilla


def test_estado_desactivado_por_defecto(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SBI_ENABLED", "false")
    st = sbi_pro.estado_sbi()
    assert st["protocolo"] == "SBI-PRO"
    assert st["enabled"] is False
    assert st["systemguard"] == "respetado"
    assert st["deps_pesadas"] is False


def test_enroll_y_verify_mismo_timbre(sbi_env: Path):
    wav = sbi_pro.sintetizar_wav_pcm16(seconds=1.2, freq=180.0, seed=7)
    b64 = sbi_pro.wav_a_base64(wav)

    out = sbi_pro.enrollar(
        b64,
        mime="audio/wav",
        enroll_token="token-enroll-test",
    )
    assert out["ok"] is True
    assert out["enrolled"] is True
    assert sbi_env.is_file()

    res = sbi_pro.verificar(b64, mime="audio/wav")
    assert res.autenticado is True
    assert res.motivo == "sbi_match"
    assert res.score is not None and res.score >= 0.82


def test_verify_rechaza_timbre_distinto(sbi_env: Path):
    # Tono armónico (enrollment) vs ruido blanco (intruso)
    wav_a = sbi_pro.sintetizar_wav_pcm16(seconds=1.2, freq=180.0, seed=7)
    rng = __import__("numpy").random.default_rng(123)
    noise = (rng.normal(0, 0.35, size=int(1.2 * 16000)) * 30000).astype("int16")
    import wave
    from io import BytesIO

    bio = BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(noise.tobytes())
    wav_b = bio.getvalue()

    sbi_pro.enrollar(
        sbi_pro.wav_a_base64(wav_a),
        enroll_token="token-enroll-test",
    )
    res = sbi_pro.verificar(sbi_pro.wav_a_base64(wav_b))
    assert res.autenticado is False
    assert res.motivo == "sbi_no_match"
    assert res.score is not None and res.score < 0.82


def test_enroll_sin_token_falla(sbi_env: Path):
    wav = sbi_pro.sintetizar_wav_pcm16(seed=1)
    out = sbi_pro.enrollar(sbi_pro.wav_a_base64(wav), enroll_token="malo")
    assert out["ok"] is False
    assert out["error"] == "sbi_enroll_no_autorizado"


def test_recovery_key(sbi_env: Path):
    wav = sbi_pro.sintetizar_wav_pcm16(seed=3)
    sbi_pro.enrollar(
        sbi_pro.wav_a_base64(wav),
        enroll_token="token-enroll-test",
    )
    ok = sbi_pro.verificar(None, recovery_key="recovery-israel-test")
    assert ok.autenticado is True
    assert ok.motivo == "sbi_recovery_ok"

    bad = sbi_pro.verificar(None, recovery_key="wrong")
    assert bad.autenticado is False


def test_passthrough_si_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SBI_ENABLED", "false")
    res = sbi_pro.verificar(None)
    assert res.autenticado is True
    assert res.motivo == "sbi_desactivado_passthrough"


def test_api_estado_y_verify_flow(sbi_env: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SBI_ENABLED", "true")
    import settings

    monkeypatch.setattr(settings, "SALOMON_API_KEY", "")
    from fastapi.testclient import TestClient
    from app import app

    client = TestClient(app)
    st = client.get("/api/sbi/estado")
    assert st.status_code == 200
    assert st.json()["protocolo"] == "SBI-PRO"

    wav = sbi_pro.sintetizar_wav_pcm16(seconds=1.2, freq=180.0, seed=7)
    b64 = sbi_pro.wav_a_base64(wav)
    en = client.post(
        "/api/sbi/enroll",
        json={"audio_base64": b64, "audio_mime": "audio/wav"},
        headers={"X-SBI-Enroll-Token": "token-enroll-test"},
    )
    assert en.status_code == 200
    assert en.json().get("ok") is True

    ver = client.post(
        "/api/sbi/verify",
        json={"audio_base64": b64, "audio_mime": "audio/wav"},
    )
    assert ver.status_code == 200
    body = ver.json()
    assert body["autenticado"] is True
    assert body["motivo"] == "sbi_match"
