# -*- coding: utf-8 -*-
"""
Reproducción visual de la firma de voz (antes de enrolar).
Abre ventana: ESCUCHANDO... + barra de progreso + DETENER.

Uso:
  python scripts/visual_playback.py
  python scripts/visual_playback.py --archivo security/credentials/voice_signature.wav
"""

from __future__ import annotations

import argparse
import threading
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
import tkinter as tk
from tkinter import ttk

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "security" / "credentials" / "voice_signature.wav"


class VisualPlayback:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.root = tk.Tk()
        self.root.title("SBI-PRO — Escuchar firma de voz")
        self.root.geometry("440x200")
        self.root.resizable(False, False)
        self.root.configure(bg="#111111")

        self._stop = threading.Event()
        self._stream: sd.OutputStream | None = None
        self._pos = 0
        self._audio = np.zeros(1, dtype=np.float32)
        self._rate = 44100

        self.lbl = tk.Label(
            self.root,
            text="ESCUCHANDO...",
            font=("Segoe UI", 20, "bold"),
            fg="#E8C547",
            bg="#111111",
        )
        self.lbl.pack(pady=(20, 6))

        self.info = tk.Label(
            self.root,
            text=str(path),
            font=("Consolas", 8),
            fg="#888888",
            bg="#111111",
            wraplength=400,
        )
        self.info.pack()

        self.prog = tk.DoubleVar(value=0.0)
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Play.Horizontal.TProgressbar",
            troughcolor="#222222",
            background="#4AA3FF",
            thickness=18,
        )
        ttk.Progressbar(
            self.root,
            orient="horizontal",
            length=360,
            mode="determinate",
            maximum=100,
            variable=self.prog,
            style="Play.Horizontal.TProgressbar",
        ).pack(pady=14)

        self.meta = tk.Label(
            self.root,
            text="",
            font=("Consolas", 10),
            fg="#AAAAAA",
            bg="#111111",
        )
        self.meta.pack()

        btn_row = tk.Frame(self.root, bg="#111111")
        btn_row.pack(pady=12)
        tk.Button(
            btn_row,
            text="REPETIR",
            font=("Segoe UI", 10, "bold"),
            bg="#2A4A6B",
            fg="#FFFFFF",
            relief="flat",
            padx=16,
            pady=6,
            command=self.repetir,
        ).pack(side="left", padx=8)
        tk.Button(
            btn_row,
            text="CERRAR",
            font=("Segoe UI", 10, "bold"),
            bg="#8B1E1E",
            fg="#FFFFFF",
            relief="flat",
            padx=16,
            pady=6,
            command=self.cerrar,
        ).pack(side="left", padx=8)

        self.root.protocol("WM_DELETE_WINDOW", self.cerrar)
        if not self._load():
            self.lbl.config(text="SIN ARCHIVO", fg="#FF6666")
            self.meta.config(text="No existe voice_signature.wav")
            return
        self.root.after(100, self._start_play)
        self.root.after(80, self._tick)

    def _load(self) -> bool:
        if not self.path.is_file():
            return False
        with wave.open(str(self.path), "rb") as wf:
            self._rate = wf.getframerate()
            ch = wf.getnchannels()
            sw = wf.getsampwidth()
            raw = wf.readframes(wf.getnframes())
        if sw != 2:
            self.meta.config(text=f"Formato no soportado (sampwidth={sw})")
            return False
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        if ch > 1:
            data = data.reshape(-1, ch).mean(axis=1)
        self._audio = data
        dur = len(data) / float(self._rate)
        self.meta.config(
            text=f"{self.path.stat().st_size} bytes · {self._rate} Hz · {dur:.1f}s"
        )
        return True

    def _callback(self, outdata, frames, time_info, status) -> None:  # noqa: ANN001
        if self._stop.is_set():
            outdata.fill(0)
            raise sd.CallbackStop
        end = self._pos + frames
        chunk = self._audio[self._pos : end]
        if len(chunk) < frames:
            out = np.zeros(frames, dtype=np.float32)
            out[: len(chunk)] = chunk
            outdata[:] = out.reshape(-1, 1)
            self._pos = len(self._audio)
            raise sd.CallbackStop
        outdata[:] = chunk.reshape(-1, 1)
        self._pos = end

    def _start_play(self) -> None:
        self._stop.clear()
        self._pos = 0
        self.lbl.config(text="ESCUCHANDO...", fg="#E8C547")
        try:
            self._stream = sd.OutputStream(
                samplerate=self._rate,
                channels=1,
                dtype="float32",
                callback=self._callback,
            )
            self._stream.start()
        except Exception as exc:
            self.lbl.config(text="ERROR AUDIO", fg="#FF6666")
            self.meta.config(text=str(exc)[:120])

    def _tick(self) -> None:
        if len(self._audio) > 0:
            pct = min(100.0, 100.0 * self._pos / len(self._audio))
            self.prog.set(pct)
            if self._pos >= len(self._audio) and not self._stop.is_set():
                self.lbl.config(text="FIN DE LA TOMA", fg="#3DDC84")
        if not self._stop.is_set():
            self.root.after(80, self._tick)

    def repetir(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self._start_play()
        self.root.after(80, self._tick)

    def cerrar(self) -> None:
        self._stop.set()
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
        self.root.destroy()

    def run(self) -> None:
        print(f"--- REPRODUCIENDO: {self.path} ---", flush=True)
        self.root.mainloop()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--archivo", type=Path, default=DEFAULT)
    args = p.parse_args()
    path = args.archivo if args.archivo.is_absolute() else (ROOT / args.archivo)
    if not path.is_file():
        print(f"ERROR: no existe {path}", flush=True)
        return 1
    VisualPlayback(path).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
