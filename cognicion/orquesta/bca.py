"""
Branch de Control Autónomo (BCA) — Colsub.

Supervisa el servidor en :8000:
- Autoreload con watchdog al guardar código
- Reinicio automático si el proceso cae
- Escribe estado en data/bca/estado.json para la UI
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Raíz del proyecto (dos niveles arriba de cognicion/orquesta)
ROOT = Path(__file__).resolve().parents[2]
ESTADO_DIR = ROOT / "data" / "bca"
ESTADO_PATH = ESTADO_DIR / "estado.json"
PID_PATH = ESTADO_DIR / "supervisor.pid"
PUERTO = int(os.getenv("COLSUB_PORT", "8000"))
# Health checks siempre a loopback; el servidor escucha en 0.0.0.0
HOST = "127.0.0.1"
POLL_S = float(os.getenv("BCA_POLL_S", "2.0"))
DEBOUNCE_S = float(os.getenv("BCA_DEBOUNCE_S", "1.2"))
HEALTH_FAILS = int(os.getenv("BCA_HEALTH_FAILS", "3"))

_WATCH_EXTS = {".py", ".env", ".toml", ".json", ".html", ".js", ".css"}
_IGNORE_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "data",
    "dist",  # solo dist de builds grandes; studio/dist sí se mira vía html
    ".cursor",
}


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def escribir_estado(payload: dict[str, Any]) -> None:
    ESTADO_DIR.mkdir(parents=True, exist_ok=True)
    base = {
        "hub": "Colsub BCA",
        "bca_activo": True,
        "puerto": PUERTO,
        "actualizado": _ahora(),
        "pid_supervisor": os.getpid(),
    }
    base.update(payload)
    tmp = ESTADO_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(ESTADO_PATH)


def leer_estado() -> dict[str, Any]:
    if not ESTADO_PATH.exists():
        return {
            "bca_activo": False,
            "servidor_ok": False,
            "necesita_intervencion": True,
            "motivo": "bca_no_iniciado",
        }
    try:
        data = json.loads(ESTADO_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {
            "bca_activo": False,
            "servidor_ok": False,
            "necesita_intervencion": True,
            "motivo": "estado_corrupto",
        }
    # ¿Sigue vivo el supervisor?
    pid = int(data.get("pid_supervisor") or 0)
    vivo = _pid_vivo(pid) if pid else False
    data["bca_activo"] = vivo
    if not vivo:
        data["necesita_intervencion"] = True
        data["motivo"] = data.get("motivo") or "supervisor_muerto"
    return data


def _pid_vivo(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        import psutil

        return psutil.pid_exists(pid)
    except Exception:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def puerto_ocupado(puerto: int = PUERTO, host: str = HOST) -> bool:
    try:
        with socket.create_connection((host, puerto), timeout=0.8):
            return True
    except OSError:
        return False


def salud_http(puerto: int = PUERTO) -> bool:
    try:
        import urllib.request

        url = f"http://127.0.0.1:{puerto}/api/salud"
        with urllib.request.urlopen(url, timeout=2.5) as r:
            return 200 <= getattr(r, "status", 200) < 500
    except Exception:
        return puerto_ocupado(puerto)


def matar_puerto(puerto: int = PUERTO) -> list[int]:
    """Mata procesos que escuchan en el puerto. Devuelve PIDs terminados."""
    muertos: list[int] = []
    try:
        import psutil

        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr and conn.laddr.port == puerto and conn.pid:
                try:
                    p = psutil.Process(conn.pid)
                    # No matar al propio supervisor
                    if p.pid == os.getpid():
                        continue
                    p.terminate()
                    try:
                        p.wait(timeout=3)
                    except Exception:
                        p.kill()
                    muertos.append(conn.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
    except Exception:
        # Fallback Windows
        if sys.platform == "win32":
            try:
                out = subprocess.check_output(
                    ["netstat", "-ano"], text=True, errors="ignore"
                )
                for line in out.splitlines():
                    if f":{puerto}" in line and "LISTENING" in line:
                        parts = line.split()
                        pid = int(parts[-1])
                        if pid and pid != os.getpid():
                            subprocess.run(
                                ["taskkill", "/F", "/PID", str(pid)],
                                capture_output=True,
                            )
                            muertos.append(pid)
            except Exception:
                pass
        else:
            try:
                out = subprocess.check_output(
                    ["lsof", "-ti", f":{puerto}"], text=True, errors="ignore"
                )
                for pid_s in out.split():
                    pid = int(pid_s)
                    if pid != os.getpid():
                        os.kill(pid, signal.SIGTERM)
                        muertos.append(pid)
            except Exception:
                pass
    time.sleep(0.4)
    return muertos


class BranchControlAutonomo:
    """Supervisa uvicorn: autoreload + recuperación ante caídas."""

    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._restart_pendiente = threading.Event()
        self._stop = threading.Event()
        self._reinicios = 0
        self._ultimo_motivo = "inicio"
        self._fallos_salud = 0
        self._ultimo_cambio = ""

    def _cmd_servidor(self) -> list[str]:
        # Sin reload de uvicorn: el BCA es dueño del reinicio
        return [
            sys.executable,
            "-m",
            "uvicorn",
            "app:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(PUERTO),
            "--log-level",
            "info",
        ]

    def _asegurar_tunel(self) -> None:
        """Activa localtunnel una vez y reimprime Public URL."""
        try:
            from cognicion.red.tunel import iniciar_tunel_si_habilitado, obtener_tunel

            t = obtener_tunel()
            if t and t.proc and t.proc.poll() is None and t.public_url:
                print(f"[BCA] Public URL (móvil): {t.public_url}", flush=True)
                return
            t = iniciar_tunel_si_habilitado(PUERTO)
            if t and t.public_url:
                self._publicar("ok")
        except Exception as exc:
            print(f"[BCA] Túnel no disponible: {exc}", flush=True)

    def arrancar_servidor(self, motivo: str = "manual") -> None:
        with self._lock:
            self._ultimo_motivo = motivo
            if self._proc and self._proc.poll() is None:
                try:
                    self._proc.terminate()
                    self._proc.wait(timeout=4)
                except Exception:
                    try:
                        self._proc.kill()
                    except Exception:
                        pass
            matar_puerto(PUERTO)
            env = os.environ.copy()
            env["BCA_SUPERVISOR"] = "1"
            env["BCA_PID"] = str(os.getpid())
            self._proc = subprocess.Popen(
                self._cmd_servidor(),
                cwd=str(ROOT),
                env=env,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
            self._reinicios += 1
            self._fallos_salud = 0
        self._publicar("reiniciando" if motivo != "inicio" else "arrancando")

    def detener(self) -> None:
        self._stop.set()
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=5)
                except Exception:
                    self._proc.kill()
            matar_puerto(PUERTO)
        escribir_estado(
            {
                "bca_activo": False,
                "servidor_ok": False,
                "necesita_intervencion": True,
                "motivo": "bca_detenido",
                "reinicios": self._reinicios,
            }
        )

    def solicitar_reinicio(self, motivo: str, archivo: str = "") -> None:
        self._ultimo_motivo = motivo
        self._ultimo_cambio = archivo
        self._restart_pendiente.set()

    def _publicar(self, fase: str) -> None:
        ok = salud_http(PUERTO) if fase == "ok" else puerto_ocupado(PUERTO)
        vivo_hijo = bool(self._proc and self._proc.poll() is None)
        necesita = not (ok and vivo_hijo) and fase not in ("arrancando", "reiniciando")
        escribir_estado(
            {
                "fase": fase,
                "servidor_ok": ok,
                "proceso_hijo_vivo": vivo_hijo,
                "pid_servidor": self._proc.pid if self._proc else None,
                "necesita_intervencion": necesita and fase == "caido",
                "motivo": self._ultimo_motivo,
                "ultimo_cambio": self._ultimo_cambio,
                "reinicios": self._reinicios,
                "fallos_salud": self._fallos_salud,
                "color_ui": "verde" if (ok and vivo_hijo) else (
                    "ambar" if fase in ("arrancando", "reiniciando") else "rojo"
                ),
                "public_url": self._url_tunel(),
            }
        )

    def _url_tunel(self) -> str | None:
        try:
            from cognicion.red.tunel import leer_estado_tunel

            return leer_estado_tunel().get("public_url")
        except Exception:
            return None

    def _bucle_salud(self) -> None:
        while not self._stop.is_set():
            # Reinicio solicitado por watchdog
            if self._restart_pendiente.is_set():
                self._restart_pendiente.clear()
                time.sleep(DEBOUNCE_S)
                # coalescer eventos extra
                while self._restart_pendiente.is_set():
                    self._restart_pendiente.clear()
                    time.sleep(0.3)
                print(f"[BCA] Reinicio por {self._ultimo_motivo}: {self._ultimo_cambio}")
                self.arrancar_servidor(self._ultimo_motivo)
                # Esperar a que levante
                for _ in range(40):
                    if self._stop.is_set():
                        return
                    if salud_http(PUERTO):
                        self._publicar("ok")
                        break
                    time.sleep(0.5)
                else:
                    self._publicar("caido")

            hijo_muerto = self._proc is None or self._proc.poll() is not None
            if hijo_muerto:
                self._fallos_salud += 1
                self._publicar("caido")
                if self._fallos_salud >= 1:
                    print("[BCA] Proceso caído — reinicio autónomo")
                    self.arrancar_servidor("crash_recovery")
                    time.sleep(2)
                time.sleep(POLL_S)
                continue

            if salud_http(PUERTO):
                self._fallos_salud = 0
                self._publicar("ok")
            else:
                self._fallos_salud += 1
                self._publicar("degradado")
                if self._fallos_salud >= HEALTH_FAILS:
                    print("[BCA] Salud :8000 fallida — reinicio autónomo")
                    self.arrancar_servidor("health_recovery")
                    time.sleep(2)
            time.sleep(POLL_S)

    def _montar_watchdog(self) -> Any:
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError as exc:
            raise SystemExit(
                "Falta watchdog. Instala con: pip install watchdog"
            ) from exc

        bca = self

        class Handler(FileSystemEventHandler):
            def on_any_event(self, event):  # type: ignore[no-untyped-def]
                if getattr(event, "is_directory", False):
                    return
                path = getattr(event, "src_path", "") or ""
                p = Path(path)
                if any(part in _IGNORE_DIRS for part in p.parts):
                    return
                # Ignorar estado del propio BCA
                if "data" in p.parts and "bca" in p.parts:
                    return
                if p.suffix.lower() not in _WATCH_EXTS and p.name != ".env":
                    return
                # Evitar reiniciar por el propio supervisor
                if p.name in ("bca.py", "estado.json", "supervisor.pid"):
                    if "orquesta" in p.parts and p.name == "bca.py":
                        pass  # sí reiniciar si cambia bca.py
                    elif p.name != "bca.py":
                        return
                bca.solicitar_reinicio("file_change", str(p.relative_to(ROOT)) if ROOT in p.parents else str(p))

        observer = Observer()
        # Vigilar raíz con filtros por extensión en el handler
        observer.schedule(Handler(), str(ROOT), recursive=True)
        observer.start()
        return observer

    def ejecutar(self) -> None:
        ESTADO_DIR.mkdir(parents=True, exist_ok=True)
        PID_PATH.write_text(str(os.getpid()), encoding="utf-8")
        print(f"[BCA] Branch de Control Autónomo activo · puerto {PUERTO}")
        print(f"[BCA] PID supervisor={os.getpid()} · cwd={ROOT}")
        observer = self._montar_watchdog()
        self.arrancar_servidor("inicio")
        # Esperar primer health
        for _ in range(50):
            if salud_http(PUERTO):
                self._publicar("ok")
                break
            time.sleep(0.4)
        self._asegurar_tunel()
        try:
            self._bucle_salud()
        except KeyboardInterrupt:
            print("\n[BCA] Deteniendo…")
        finally:
            observer.stop()
            observer.join(timeout=3)
            try:
                from cognicion.red.tunel import obtener_tunel

                t = obtener_tunel()
                if t:
                    t.detener()
            except Exception:
                pass
            self.detener()


def main() -> None:
    os.chdir(ROOT)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    BranchControlAutonomo().ejecutar()


if __name__ == "__main__":
    main()
