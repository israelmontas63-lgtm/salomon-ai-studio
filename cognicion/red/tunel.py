"""
Túnel público — localtunnel (npx) para acceso móvil inalámbrico a :8000.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from settings import DATA_DIR, ROOT_DIR

ESTADO_TUNEL = DATA_DIR / "bca" / "tunel.json"
_URL_RE = re.compile(
    r"https?://[a-zA-Z0-9][-a-zA-Z0-9]*\.(?:loca\.lt|localtunnel\.me)[^\s]*",
    re.I,
)


class TunelLocal:
    """Lanza `npx localtunnel --port N` y captura la Public URL."""

    def __init__(self, puerto: int = 8000) -> None:
        self.puerto = puerto
        self.proc: subprocess.Popen | None = None
        self.public_url: str | None = None
        self.error: str | None = None
        self._hilo: threading.Thread | None = None
        self._stop = threading.Event()

    def _escribir(self) -> None:
        ESTADO_TUNEL.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "activo": bool(self.proc and self.proc.poll() is None),
            "public_url": self.public_url,
            "puerto": self.puerto,
            "error": self.error,
            "actualizado": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        ESTADO_TUNEL.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _leer_salida(self) -> None:
        assert self.proc and self.proc.stdout
        for raw in self.proc.stdout:
            if self._stop.is_set():
                break
            line = raw.decode("utf-8", errors="ignore").strip()
            if not line:
                continue
            print(f"[túnel] {line}", flush=True)
            m = _URL_RE.search(line)
            if m and not self.public_url:
                self.public_url = m.group(0).rstrip(").,;")
                self._escribir()
                print("", flush=True)
                print("=" * 60, flush=True)
                print(f"  Public URL (móvil): {self.public_url}", flush=True)
                print("  Abre esa URL en el navegador del teléfono.", flush=True)
                print("  Si localtunnel pide password: usa tu IP pública", flush=True)
                print("  (https://loca.lt/mytunnelpassword).", flush=True)
                print("=" * 60, flush=True)
                print("", flush=True)

    def iniciar(self) -> bool:
        if self.proc and self.proc.poll() is None:
            return True
        npx = "npx.cmd" if sys.platform == "win32" else "npx"
        subdomain = (
            os.getenv("TUNEL_SUBDOMAIN", "").strip()
            or getattr(
                __import__("settings", fromlist=["TUNEL_SUBDOMAIN"]),
                "TUNEL_SUBDOMAIN",
                "salomon-ai",
            )
            or "salomon-ai"
        )
        cmd = [npx, "--yes", "localtunnel", "--port", str(self.puerto)]
        if subdomain:
            cmd.extend(["--subdomain", subdomain])
            print(f"[túnel] subdomain fijo → https://{subdomain}.loca.lt", flush=True)
        try:
            self.proc = subprocess.Popen(
                cmd,
                cwd=str(ROOT_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            self.error = "npx_no_encontrado_instala_nodejs"
            self._escribir()
            print(f"[túnel] ERROR: {self.error}", flush=True)
            return False
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            self._escribir()
            print(f"[túnel] ERROR: {self.error}", flush=True)
            return False

        self._stop.clear()
        self._hilo = threading.Thread(target=self._leer_salida, daemon=True)
        self._hilo.start()
        self._escribir()
        print(
            f"[túnel] localtunnel arrancando → puerto {self.puerto}…",
            flush=True,
        )
        # Esperar URL un rato
        for _ in range(40):
            if self.public_url or self._stop.is_set():
                break
            if self.proc.poll() is not None:
                self.error = "localtunnel_termino_prematuro"
                self._escribir()
                break
            time.sleep(0.25)
        return bool(self.public_url) or (self.proc.poll() is None)

    def detener(self) -> None:
        self._stop.set()
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=4)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        self.proc = None
        self._escribir()

    def estado(self) -> dict[str, Any]:
        return {
            "activo": bool(self.proc and self.proc.poll() is None),
            "public_url": self.public_url,
            "puerto": self.puerto,
            "error": self.error,
        }


_tunel_global: TunelLocal | None = None


def obtener_tunel() -> TunelLocal | None:
    return _tunel_global


def leer_estado_tunel() -> dict[str, Any]:
    if ESTADO_TUNEL.exists():
        try:
            return json.loads(ESTADO_TUNEL.read_text(encoding="utf-8"))
        except Exception:
            pass
    if _tunel_global:
        return _tunel_global.estado()
    return {"activo": False, "public_url": None}


def iniciar_tunel_si_habilitado(puerto: int | None = None) -> TunelLocal | None:
    """Activa localtunnel si TUNEL_AUTO / TUNEL_HABILITADO está on."""
    global _tunel_global
    flag = os.getenv("TUNEL_AUTO", os.getenv("TUNEL_HABILITADO", "true")).strip().lower()
    if flag not in ("1", "true", "yes", "on"):
        return None
    try:
        import settings as st

        puerto_f = int(puerto or getattr(st, "COLSUB_PORT", 8000) or 8000)
        if not getattr(st, "TUNEL_HABILITADO", True):
            return None
    except Exception:
        puerto_f = int(puerto or os.getenv("COLSUB_PORT", "8000"))

    if _tunel_global and _tunel_global.proc and _tunel_global.proc.poll() is None:
        return _tunel_global
    t = TunelLocal(puerto=puerto_f)
    t.iniciar()
    _tunel_global = t
    return t
