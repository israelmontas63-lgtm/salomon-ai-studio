# -*- coding: utf-8 -*-
"""
SBI-PRO — Speaker Biometric Identity (Israel Monta).

Huella de voz ligera (numpy / FFT). Sin torch ni deps pesadas (SystemGuard / Free Tier).
Modos: off | soft (verificar sin bloquear) | strict (listo para gatear rutas).
Clave de recuperación evita auto-bloqueo si falla el micrófono.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np

from settings import ROOT_DIR

PROTOCOLO = "SBI-PRO"
VERSION = "1.0.0"
OWNER_DEFAULT = "Israel Monta"
FEATURE_DIM = 64


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cfg() -> dict[str, Any]:
    import os

    mode = (os.getenv("SBI_MODE", "soft") or "soft").strip().lower()
    if mode not in ("off", "soft", "strict"):
        mode = "soft"
    enabled = os.getenv("SBI_ENABLED", "false").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    threshold = float(os.getenv("SBI_THRESHOLD", "0.82") or "0.82")
    threshold = min(0.99, max(0.50, threshold))
    rel = (
        os.getenv("SBI_TEMPLATE_PATH", "security/credentials/sbi_israel.json") or ""
    ).strip()
    path = Path(rel)
    if not path.is_absolute():
        path = ROOT_DIR / path
    return {
        "enabled": enabled and mode != "off",
        "mode": mode if enabled else "off",
        "threshold": threshold,
        "recovery_key": (os.getenv("SBI_RECOVERY_KEY", "") or "").strip(),
        "enroll_token": (os.getenv("SBI_ENROLL_TOKEN", "") or "").strip(),
        "owner": (os.getenv("SBI_OWNER_NAME", OWNER_DEFAULT) or OWNER_DEFAULT).strip(),
        "challenge": (
            os.getenv("SBI_CHALLENGE_PHRASE", "Salomon autentica a Israel") or ""
        ).strip(),
        "template_path": path,
        "template_secret": (os.getenv("SBI_TEMPLATE_SECRET", "") or "").strip(),
    }


@dataclass
class ResultadoSBI:
    ok: bool
    autenticado: bool
    motivo: str
    score: float | None = None
    modo: str = "off"
    owner: str = OWNER_DEFAULT
    protocolo: str = PROTOCOLO

    def a_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "autenticado": self.autenticado,
            "motivo": self.motivo,
            "score": self.score,
            "modo": self.modo,
            "owner": self.owner,
            "protocolo": self.protocolo,
            "version": VERSION,
        }


def _pcm_from_wav_bytes(raw: bytes) -> tuple[np.ndarray, int]:
    bio = BytesIO(raw)
    with wave.open(bio, "rb") as wf:
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    if sampwidth != 2:
        raise ValueError("sbi_wav_debe_ser_pcm16")
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    if samples.size < rate // 4:
        raise ValueError("sbi_audio_demasiado_corto")
    # Normalizar
    peak = float(np.max(np.abs(samples))) or 1.0
    samples = samples / peak
    return samples, rate


def _pcm_from_base64(audio_b64: str, mime: str = "audio/wav") -> tuple[np.ndarray, int]:
    raw = base64.b64decode(audio_b64)
    mime_l = (mime or "audio/wav").lower()
    if "wav" in mime_l or raw[:4] == b"RIFF":
        return _pcm_from_wav_bytes(raw)
    # PCM16 mono 16 kHz por defecto
    if len(raw) < 4000:
        raise ValueError("sbi_audio_demasiado_corto")
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    peak = float(np.max(np.abs(samples))) or 1.0
    return samples / peak, 16000


def extraer_huella(samples: np.ndarray, rate: int) -> np.ndarray:
    """Vector de características espectrales L2-normalizado (dim fija)."""
    win = max(512, min(2048, rate // 16))
    hop = win // 2
    if samples.size < win:
        samples = np.pad(samples, (0, win - samples.size))

    n_bandas = FEATURE_DIM - 8
    bandas = np.zeros(n_bandas, dtype=np.float64)
    centros: list[float] = []
    energias: list[float] = []
    zcr: list[float] = []
    flatness: list[float] = []
    pico_rel: list[float] = []

    n_frames = 0
    for start in range(0, samples.size - win, hop):
        frame = samples[start : start + win]
        n_frames += 1
        energias.append(float(np.mean(frame * frame)))
        zcr.append(float(np.mean(np.abs(np.diff(np.sign(frame)))) / 2.0))
        espec = np.abs(np.fft.rfft(frame * np.hanning(win))) + 1e-12
        freqs = np.fft.rfftfreq(win, d=1.0 / rate)
        mag_sum = float(np.sum(espec))
        centros.append(float(np.sum(freqs * espec) / mag_sum))
        # Spectral flatness (ruido ≈ 1, tono ≈ 0)
        log_mean = float(np.mean(np.log(espec)))
        flatness.append(float(np.exp(log_mean) / (np.mean(espec))))
        pico_rel.append(float(np.max(espec) / mag_sum))
        # Bandas log-frecuencia (más peso al timbre)
        edges = np.geomspace(1, max(2, espec.size), n_bandas + 1).astype(int)
        edges = np.clip(edges, 0, espec.size)
        for i in range(n_bandas):
            a, b = int(edges[i]), int(edges[i + 1])
            if b <= a:
                b = min(espec.size, a + 1)
            segment = espec[a:b]
            bandas[i] += float(np.mean(segment))

    if n_frames == 0:
        raise ValueError("sbi_sin_frames")

    bandas /= float(n_frames)
    # Contraste relativo entre bandas (invariante a ganancia)
    bandas = bandas / (float(np.sum(bandas)) + 1e-12)
    stats = np.array(
        [
            float(np.mean(centros) / max(rate / 2, 1.0)),
            float(np.std(centros) / max(rate / 2, 1.0)),
            float(np.mean(zcr)),
            float(np.std(zcr)),
            float(np.mean(flatness)),
            float(np.mean(pico_rel)),
            float(np.percentile(energias, 50)),
            float(np.percentile(energias, 90)),
        ],
        dtype=np.float64,
    )
    vec = np.concatenate([stats * 2.0, bandas * 4.0])  # prioriza forma espectral
    vec = np.log1p(np.abs(vec))
    norm = float(np.linalg.norm(vec)) or 1.0
    return (vec / norm).astype(np.float64)


def huella_desde_base64(audio_b64: str, mime: str = "audio/wav") -> np.ndarray:
    samples, rate = _pcm_from_base64(audio_b64, mime)
    return extraer_huella(samples, rate)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
    return float(np.dot(a, b) / denom)


def _firmar_vector(vec: list[float], secret: str) -> str:
    payload = json.dumps(vec, separators=(",", ":")).encode("utf-8")
    if secret:
        return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hashlib.sha256(payload).hexdigest()


def plantilla_existe() -> bool:
    cfg = _cfg()
    return cfg["template_path"].is_file()


def cargar_plantilla() -> dict[str, Any] | None:
    cfg = _cfg()
    path: Path = cfg["template_path"]
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    vec = data.get("huella")
    if not isinstance(vec, list) or len(vec) != FEATURE_DIM:
        return None
    sig = data.get("firma") or ""
    expected = _firmar_vector(vec, cfg["template_secret"])
    if sig and not hmac.compare_digest(sig, expected):
        raise ValueError("sbi_plantilla_firma_invalida")
    return data


def estado_sbi() -> dict[str, Any]:
    cfg = _cfg()
    enrolled = plantilla_existe()
    return {
        "protocolo": PROTOCOLO,
        "version": VERSION,
        "enabled": cfg["enabled"],
        "modo": cfg["mode"],
        "owner": cfg["owner"],
        "enrolled": enrolled,
        "threshold": cfg["threshold"],
        "challenge": cfg["challenge"],
        "recovery_configurada": bool(cfg["recovery_key"]),
        "systemguard": "respetado",
        "deps_pesadas": False,
    }


def enrollar(
    audio_b64: str,
    *,
    mime: str = "audio/wav",
    enroll_token: str | None = None,
    admin_ok: bool = False,
) -> dict[str, Any]:
    """Registra la huella de Israel. Requiere token de enroll o admin."""
    cfg = _cfg()
    token_cfg = cfg["enroll_token"]
    if token_cfg:
        if not enroll_token or not hmac.compare_digest(enroll_token, token_cfg):
            if not admin_ok:
                return {
                    "ok": False,
                    "error": "sbi_enroll_no_autorizado",
                    "protocolo": PROTOCOLO,
                }
    elif not admin_ok:
        return {
            "ok": False,
            "error": "sbi_enroll_requiere_admin_o_token",
            "protocolo": PROTOCOLO,
        }

    try:
        vec = huella_desde_base64(audio_b64, mime)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "protocolo": PROTOCOLO}

    lista = [float(x) for x in vec.tolist()]
    path: Path = cfg["template_path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    # No tocar rutas SystemGuard críticas
    if "studio/dist" in str(path).replace("\\", "/"):
        return {"ok": False, "error": "sbi_ruta_template_prohibida", "protocolo": PROTOCOLO}

    payload = {
        "protocolo": PROTOCOLO,
        "version": VERSION,
        "owner": cfg["owner"],
        "created_at": _utc(),
        "feature_dim": FEATURE_DIM,
        "huella": lista,
        "firma": _firmar_vector(lista, cfg["template_secret"]),
        "challenge": cfg["challenge"],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        rel = str(path.relative_to(ROOT_DIR)).replace("\\", "/")
    except ValueError:
        rel = str(path)
    return {
        "ok": True,
        "enrolled": True,
        "owner": cfg["owner"],
        "path": rel,
        "protocolo": PROTOCOLO,
        "version": VERSION,
    }


def verificar(
    audio_b64: str | None = None,
    *,
    mime: str = "audio/wav",
    recovery_key: str | None = None,
) -> ResultadoSBI:
    cfg = _cfg()
    owner = cfg["owner"]
    modo = cfg["mode"]

    if not cfg["enabled"]:
        return ResultadoSBI(
            ok=True,
            autenticado=True,
            motivo="sbi_desactivado_passthrough",
            modo="off",
            owner=owner,
        )

    # Recuperación (nunca dejar a Israel fuera sin escape)
    if recovery_key and cfg["recovery_key"]:
        if hmac.compare_digest(recovery_key, cfg["recovery_key"]):
            return ResultadoSBI(
                ok=True,
                autenticado=True,
                motivo="sbi_recovery_ok",
                score=1.0,
                modo=modo,
                owner=owner,
            )
        return ResultadoSBI(
            ok=False,
            autenticado=False,
            motivo="sbi_recovery_invalida",
            modo=modo,
            owner=owner,
        )

    if not audio_b64:
        return ResultadoSBI(
            ok=False,
            autenticado=False,
            motivo="sbi_audio_requerido",
            modo=modo,
            owner=owner,
        )

    try:
        plantilla = cargar_plantilla()
    except ValueError as exc:
        return ResultadoSBI(
            ok=False,
            autenticado=False,
            motivo=str(exc),
            modo=modo,
            owner=owner,
        )

    if not plantilla:
        return ResultadoSBI(
            ok=False,
            autenticado=False,
            motivo="sbi_sin_enrollment",
            modo=modo,
            owner=owner,
        )

    try:
        vec = huella_desde_base64(audio_b64, mime)
    except Exception as exc:
        return ResultadoSBI(
            ok=False,
            autenticado=False,
            motivo=str(exc),
            modo=modo,
            owner=owner,
        )

    ref = np.array(plantilla["huella"], dtype=np.float64)
    score = _cosine(vec, ref)
    ok = score >= cfg["threshold"]
    return ResultadoSBI(
        ok=ok,
        autenticado=ok,
        motivo="sbi_match" if ok else "sbi_no_match",
        score=round(score, 4),
        modo=modo,
        owner=owner,
    )


def sintetizar_wav_pcm16(
    *,
    seconds: float = 1.2,
    rate: int = 16000,
    freq: float = 180.0,
    seed: int = 7,
) -> bytes:
    """WAV sintético determinista para tests (no es voz real)."""
    rng = np.random.default_rng(seed)
    n = int(seconds * rate)
    t = np.arange(n, dtype=np.float64) / rate
    # Timbre estable + armónicos (misma semilla ≈ misma huella)
    signal = (
        0.55 * np.sin(2 * math.pi * freq * t)
        + 0.25 * np.sin(2 * math.pi * (freq * 2) * t)
        + 0.12 * np.sin(2 * math.pi * (freq * 3) * t)
        + 0.04 * rng.normal(0, 1, size=n)
    )
    signal = signal / (np.max(np.abs(signal)) or 1.0)
    pcm = (signal * 30000).astype(np.int16)
    bio = BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm.tobytes())
    return bio.getvalue()


def wav_a_base64(wav_bytes: bytes) -> str:
    return base64.b64encode(wav_bytes).decode("ascii")
