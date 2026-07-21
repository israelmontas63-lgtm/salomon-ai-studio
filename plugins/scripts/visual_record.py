# -*- coding: utf-8 -*-
"""
Grabación biométrica con interfaz visual (tkinter).
- Ventana: GRABANDO... + botón DETENER
- Medidor de nivel en tiempo real
- Guarda: security/credentials/voice_signature.wav
- NO enrola

Uso (desde la raíz del repo):
  python scripts/visual_record.py
"""

from __future__ import annotations

import queue
import threading
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
import tkinter as tk
from tkinter import ttk

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "security" / "credentials" / "voice_signature.wav"
RATE = 44100
CHANNELS = 1


class VisualRecorder:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("SBI-PRO — Captura de voz")
        self.root.geometry("420x220")
        self.root.resizable(False, False)
        self.root.configure(bg="#111111")

        self._q: queue.Queue[float] = queue.Queue()
        self._chunks: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None
        self._recording = False
        self._peak = -120.0

        self.lbl = tk.Label(
            self.root,
            text="GRABANDO...",
            font=("Segoe UI", 22, "bold"),
            fg="#E8C547",
            bg="#111111",
        )
        self.lbl.pack(pady=(24, 8))

        self.hint = tk.Label(
            self.root,
            text='Di: "Salomón, autentica a Israel"',
            font=("Segoe UI", 10),
            fg="#CCCCCC",
            bg="#111111",
        )
        self.hint.pack()

        self.level_var = tk.DoubleVar(value=0.0)
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Level.Horizontal.TProgressbar",
            troughcolor="#222222",
            background="#3DDC84",
            thickness=22,
        )
        self.bar = ttk.Progressbar(
            self.root,
            orient="horizontal",
            length=340,
            mode="determinate",
            maximum=100,
            variable=self.level_var,
            style="Level.Horizontal.TProgressbar",
        )
        self.bar.pack(pady=16)

        self.db_lbl = tk.Label(
            self.root,
            text="Nivel: --- dB",
            font=("Consolas", 11),
            fg="#AAAAAA",
            bg="#111111",
        )
        self.db_lbl.pack()

        self.btn = tk.Button(
            self.root,
            text="DETENER",
            font=("Segoe UI", 12, "bold"),
            bg="#8B1E1E",
            fg="#FFFFFF",
            activebackground="#B02A2A",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=24,
            pady=8,
            command=self.detener,
        )
        self.btn.pack(pady=14)

        self.status = tk.Label(
            self.root,
            text="Micrófono activo — habla ahora",
            font=("Segoe UI", 9),
            fg="#888888",
            bg="#111111",
        )
        self.status.pack()

        self.root.protocol("WM_DELETE_WINDOW", self.detener)
        self.root.after(80, self._tick_ui)
        self._start_stream()

    def _audio_cb(self, indata, frames, time_info, status) -> None:  # noqa: ANN001
        if not self._recording:
            return
        mono = indata.copy().reshape(-1)
        with self._lock:
            self._chunks.append(mono.copy())
        rms = float(np.sqrt(np.mean(np.square(mono.astype(np.float64)))))
        db = 20.0 * np.log10(rms + 1e-12)
        try:
            self._q.put_nowait(db)
        except queue.Full:
            pass

    def _start_stream(self) -> None:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        self._recording = True
        self._stream = sd.InputStream(
            samplerate=RATE,
            channels=CHANNELS,
            dtype="float32",
            callback=self._audio_cb,
            blocksize=int(RATE * 0.05),
        )
        self._stream.start()

    def _tick_ui(self) -> None:
        latest = None
        while True:
            try:
                latest = self._q.get_nowait()
            except queue.Empty:
                break
        if latest is not None:
            self._peak = max(self._peak, latest)
            # Map -60..0 dB → 0..100
            pct = max(0.0, min(100.0, (latest + 60.0) * (100.0 / 60.0)))
            self.level_var.set(pct)
            self.db_lbl.config(text=f"Nivel: {latest:5.1f} dB   pico: {self._peak:5.1f} dB")
            if latest > -45:
                self.lbl.config(fg="#3DDC84")
            else:
                self.lbl.config(fg="#E8C547")
        if self._recording:
            self.root.after(80, self._tick_ui)

    def detener(self) -> None:
        if not self._recording:
            return
        self._recording = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        with self._lock:
            chunks = list(self._chunks)
        if not chunks:
            self.status.config(text="ERROR: no se capturó audio", fg="#FF6666")
            self.lbl.config(text="SIN AUDIO")
            self.root.after(1500, self.root.destroy)
            return

        audio = np.concatenate(chunks)
        peak = float(np.max(np.abs(audio))) or 1.0
        pcm = (audio / peak * 30000.0).astype(np.int16)
        with wave.open(str(OUT), "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(RATE)
            wf.writeframes(pcm.tobytes())

        self.lbl.config(text="GUARDADO", fg="#3DDC84")
        self.status.config(
            text=f"Archivo: {OUT} ({OUT.stat().st_size} bytes) — sin enrolar",
            fg="#3DDC84",
        )
        self.btn.config(state="disabled", text="LISTO")
        print(f"--- GRABACION VISUAL GUARDADA: {OUT} bytes={OUT.stat().st_size} ---", flush=True)
        self.root.after(1200, self.root.destroy)

    def run(self) -> None:
        print("--- VENTANA VISUAL ABIERTA: GRABANDO... ---", flush=True)
        print(f"Salida prevista: {OUT}", flush=True)
        self.root.mainloop()


def main() -> int:
    try:
        VisualRecorder().run()
    except Exception as exc:
        print(f"[VISUAL] ERROR: {type(exc).__name__}: {exc}", flush=True)
        return 1
    if OUT.is_file():
        print(f"OK voice_signature.wav existe ({OUT.stat().st_size} bytes)", flush=True)
        return 0
    print("CANCELADO o sin archivo", flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
