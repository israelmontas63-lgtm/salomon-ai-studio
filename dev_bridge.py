"""
Salomón AI — Dev Bridge (Etapa 1: desarrollo móvil).

uvicorn app:app --reload + túnel público:
  1) ngrok (si NGROK_AUTHTOKEN)
  2) Cloudflare quick tunnel (cloudflared)
  3) LAN

Escribe ACCESS_URL.txt — ábrelo en el celular.
Hot-reload: al guardar HTML/CSS/JS/Python, refresca el teléfono.
"""

from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACCESS_FILE = ROOT / "ACCESS_URL.txt"
TUNNEL_LOG = ROOT / ".tunnel.log"
PARENT_ENV = ROOT.parent / ".env"


def _load_env() -> None:
    for env_path in (ROOT / ".env", PARENT_ENV):
        if env_path.is_file():
            try:
                from dotenv import load_dotenv

                load_dotenv(env_path, override=False)
            except Exception:
                pass


def _lan_url(port: int) -> str:
    ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except OSError:
        pass
    return f"http://{ip}:{port}"


def _write_access_url(url: str, *, source: str) -> None:
    ACCESS_FILE.write_text(
        f"{url}\n"
        f"# source={source}\n"
        f"# Etapa 1 — Desarrollo. Abre en el celular.\n"
        f"# Tras validar: git push → Render (Etapa 2).\n",
        encoding="utf-8",
    )
    print(f"\n>>> LINK PARA TU CELULAR:\n>>> {url}\n", flush=True)


def _wait_salud(port: int, timeout: float = 90.0) -> bool:
    url = f"http://127.0.0.1:{port}/api/salud"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.5)
    return False


def _start_uvicorn(host: str, port: int) -> subprocess.Popen:
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app:app",
        "--host",
        host,
        "--port",
        str(port),
        "--reload",
        f"--reload-dir={ROOT}",
        "--reload-include=*.py",
        "--reload-include=*.html",
        "--reload-include=*.js",
        "--reload-include=*.css",
        "--reload-include=*.json",
        "--reload-include=*.svg",
        "--reload-exclude=data/*",
        "--reload-exclude=*/seguridad_backups/*",
        "--log-level",
        "info",
    ]
    return subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )


def _start_ngrok(port: int) -> str:
    token = (os.getenv("NGROK_AUTHTOKEN") or "").strip()
    if not token:
        return ""
    try:
        from pyngrok import ngrok

        ngrok.set_auth_token(token)
        domain = (os.getenv("NGROK_DOMAIN") or "").strip()
        if domain:
            tunnel = ngrok.connect(addr=port, proto="http", hostname=domain)
        else:
            tunnel = ngrok.connect(addr=port, proto="http")
        public_url = tunnel.public_url
        if public_url.startswith("http://"):
            public_url = "https://" + public_url[len("http://") :]
        return public_url
    except Exception as exc:  # noqa: BLE001
        print(f"[dev_bridge] ngrok falló: {exc}", file=sys.stderr)
        return ""


def _find_cloudflared() -> str | None:
    found = shutil.which("cloudflared")
    if found:
        return found
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links" / "cloudflared.exe",
        Path("C:/Program Files (x86)/cloudflared/cloudflared.exe"),
        Path("C:/Program Files/cloudflared/cloudflared.exe"),
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if base.is_dir():
        for p in base.glob("Cloudflare.cloudflared*/cloudflared.exe"):
            return str(p)
    return None


def _start_cloudflared(port: int) -> tuple[str, subprocess.Popen | None]:
    binary = _find_cloudflared()
    if not binary:
        print("[dev_bridge] cloudflared no encontrado.", file=sys.stderr)
        return "", None

    print(f"[dev_bridge] Túnel Cloudflare: {binary}", flush=True)
    if TUNNEL_LOG.exists():
        TUNNEL_LOG.unlink(missing_ok=True)

    proc = subprocess.Popen(
        [binary, "tunnel", "--url", f"http://127.0.0.1:{port}", "--no-autoupdate"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(ROOT),
    )

    url = ""
    pattern = re.compile(rb"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
    deadline = time.time() + 75
    assert proc.stdout is not None
    chunks: list[bytes] = []
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        if line:
            chunks.append(line)
            try:
                text = line.decode("utf-8", errors="replace").rstrip()
            except Exception:
                text = repr(line)
            print(text, flush=True)
            match = pattern.search(line)
            if match:
                url = match.group(0).decode("ascii")
                break

    TUNNEL_LOG.write_bytes(b"".join(chunks))

    if url:

        def _drain() -> None:
            try:
                assert proc.stdout is not None
                while True:
                    more = proc.stdout.readline()
                    if not more:
                        break
                    with TUNNEL_LOG.open("ab") as fh:
                        fh.write(more)
            except Exception:  # noqa: BLE001
                pass

        threading.Thread(target=_drain, daemon=True).start()
        return url, proc

    print("[dev_bridge] No se obtuvo URL Cloudflare a tiempo.", file=sys.stderr)
    proc.terminate()
    return "", None


def main() -> None:
    os.chdir(ROOT)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    _load_env()

    host = os.getenv("DEV_HOST", "0.0.0.0")
    port = int(os.getenv("DEV_PORT", "8000"))

    print("=" * 60)
    print("  Salomón AI — Dev Bridge (Etapa 1 · móvil)")
    print("  Capas: templates/ + static/css|js|assets")
    print("=" * 60)

    server = _start_uvicorn(host, port)
    print(f"[dev_bridge] Esperando :{port}/api/salud ...", flush=True)
    if not _wait_salud(port):
        print("[dev_bridge] El servidor no respondió.", file=sys.stderr)
        server.terminate()
        sys.exit(1)
    print("[dev_bridge] Servidor OK.", flush=True)

    public_url = _start_ngrok(port)
    source = "ngrok"
    tunnel_proc: subprocess.Popen | None = None
    if not public_url:
        public_url, tunnel_proc = _start_cloudflared(port)
        source = "cloudflare"
    if not public_url:
        public_url = _lan_url(port)
        source = "lan"

    _write_access_url(public_url, source=source)
    print(f"  Fuente: {source}", flush=True)
    print(f"  Archivo: {ACCESS_FILE}", flush=True)
    print("  Hot-reload ON. Ctrl+C para detener.", flush=True)

    try:
        server.wait()
    except KeyboardInterrupt:
        print("\n[dev_bridge] Deteniendo...", flush=True)
    finally:
        if tunnel_proc and tunnel_proc.poll() is None:
            tunnel_proc.terminate()
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    main()
