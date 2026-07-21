# -*- coding: utf-8 -*-
"""
Sincroniza variables SBI-PRO locales → Render Environment + redeploy + health.

Requiere en .env (nunca se imprime el valor):
  RENDER_API_KEY=rnd_...
  RENDER_SERVICE_ID=srv-...   (opcional; si falta, busca por nombre)

Uso:
  python scripts/render_sync_sbi.py
  python scripts/render_sync_sbi.py --enroll
  python scripts/render_sync_sbi.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "security" / "credentials" / "sbi.env", override=True)

API = "https://api.render.com/v1"
LIVE = "https://salomon-ai-studio-1.onrender.com"
SERVICE_NAME_HINTS = ("salomon-ai-studio-1", "salomon-ai-studio", "salomon-ai")

# Mantener SBI_ENABLED=false en Render hasta enroll Live OK
SBI_KEYS = (
    "SBI_MODE",
    "SBI_THRESHOLD",
    "SBI_OWNER_NAME",
    "SBI_CHALLENGE_PHRASE",
    "SBI_TEMPLATE_PATH",
    "SBI_ENROLL_TOKEN",
    "SBI_RECOVERY_KEY",
    "SBI_TEMPLATE_SECRET",
)


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _require_token() -> str:
    tok = (os.getenv("RENDER_API_KEY") or os.getenv("RENDER_API_TOKEN") or "").strip()
    if not tok:
        raise SystemExit(
            "[Render] Falta RENDER_API_KEY en .env.\n"
            "  1) Dashboard → Account Settings → API Keys → Create API Key\n"
            "  2) Pégalo en .env: RENDER_API_KEY=rnd_...\n"
            "  3) Vuelve a ejecutar: python scripts/render_sync_sbi.py"
        )
    return tok


def _resolve_service_id(client: httpx.Client, token: str) -> str:
    sid = (os.getenv("RENDER_SERVICE_ID") or "").strip()
    if sid:
        return sid
    res = client.get(f"{API}/services?limit=50", headers=_headers(token))
    res.raise_for_status()
    items = res.json()
    names: list[tuple[str, str]] = []
    for row in items:
        svc = row.get("service") or row
        name = (svc.get("name") or "").strip()
        sid = (svc.get("id") or "").strip()
        if name and sid:
            names.append((name, sid))
    for hint in SERVICE_NAME_HINTS:
        for name, sid in names:
            if hint.lower() in name.lower():
                print(f"[Render] Servicio detectado: {name} ({sid})", flush=True)
                return sid
    listing = ", ".join(n for n, _ in names) or "(ninguno)"
    raise SystemExit(
        "[Render] No pude detectar el service id. Añade en .env:\n"
        f"  RENDER_SERVICE_ID=srv-...\nServicios visibles: {listing}"
    )


def _sbi_payload() -> dict[str, str]:
    out: dict[str, str] = {"SBI_ENABLED": "false"}
    missing: list[str] = []
    for k in SBI_KEYS:
        v = (os.getenv(k) or "").strip()
        if k == "SBI_TEMPLATE_PATH" and not v:
            v = "security/credentials/sbi_israel.json"
        if not v and k in (
            "SBI_ENROLL_TOKEN",
            "SBI_RECOVERY_KEY",
            "SBI_TEMPLATE_SECRET",
        ):
            missing.append(k)
        elif v:
            out[k] = v
        else:
            # defaults no secretos
            defaults = {
                "SBI_MODE": "soft",
                "SBI_THRESHOLD": "0.82",
                "SBI_OWNER_NAME": "Israel Monta",
                "SBI_CHALLENGE_PHRASE": "Salomon autentica a Israel",
                "SBI_TEMPLATE_PATH": "security/credentials/sbi_israel.json",
            }
            if k in defaults:
                out[k] = defaults[k]
    if missing:
        raise SystemExit(
            "[Render] Faltan secretos SBI locales: " + ", ".join(missing)
        )
    return out


def upsert_env_vars(
    client: httpx.Client, token: str, service_id: str, payload: dict[str, str]
) -> None:
    """Actualiza clave a clave (no reemplaza todo el Environment del servicio)."""
    for key, value in payload.items():
        url = f"{API}/services/{service_id}/env-vars/{key}"
        res = client.put(
            url,
            headers=_headers(token),
            json={"value": value},
            timeout=60.0,
        )
        if res.status_code >= 400:
            raise SystemExit(
                f"[Render] Falló upsert {key}: HTTP {res.status_code} {res.text[:300]}"
            )
        print(f"[Render] OK env {key} (len={len(value)})", flush=True)


def trigger_deploy(client: httpx.Client, token: str, service_id: str) -> str:
    res = client.post(
        f"{API}/services/{service_id}/deploys",
        headers=_headers(token),
        json={"clearCache": "do_not_clear"},
        timeout=60.0,
    )
    if res.status_code >= 400:
        raise SystemExit(f"[Render] Deploy falló: HTTP {res.status_code} {res.text[:300]}")
    body = res.json()
    deploy = body.get("deploy") or body
    did = deploy.get("id") or "?"
    print(f"[Render] Redeploy disparado: {did}", flush=True)
    return str(did)


def wait_health(timeout_s: float = 420.0) -> dict:
    url = f"{LIVE}/api/salud"
    t0 = time.time()
    last_err = ""
    with httpx.Client(timeout=45.0) as c:
        while time.time() - t0 < timeout_s:
            try:
                r = c.get(url)
                if r.status_code == 200:
                    print(f"[Health] OK {url}", flush=True)
                    try:
                        return r.json()
                    except Exception:
                        return {"raw": r.text[:200]}
                last_err = f"HTTP {r.status_code}"
            except Exception as exc:
                last_err = str(exc)
            print(f"[Health] esperando… ({last_err})", flush=True)
            time.sleep(12)
    raise SystemExit(f"[Health] Timeout tras {timeout_s}s: {last_err}")


def health_sbi() -> dict:
    with httpx.Client(timeout=60.0) as c:
        r = c.get(f"{LIVE}/api/sbi/estado")
        r.raise_for_status()
        return r.json()


def enroll_live() -> int:
    wav = ROOT / "security" / "credentials" / "voice_signature.wav"
    if not wav.is_file():
        raise SystemExit(f"[Enroll] Falta WAV: {wav}")
    from api.sbi.enroll import main as enroll_main

    sys.argv = [
        "enroll.py",
        str(wav),
        "--base",
        LIVE,
    ]
    return int(enroll_main())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--enroll",
        action="store_true",
        help="Tras health OK, enrollar voice_signature.wav en Live",
    )
    parser.add_argument("--skip-deploy", action="store_true")
    args = parser.parse_args()

    payload = _sbi_payload()
    print("[Render] Claves a sincronizar:", ", ".join(sorted(payload)), flush=True)
    print("[Render] SBI_ENABLED forzado a false hasta enroll Live", flush=True)

    if args.dry_run:
        print("[Render] dry-run: no se llama a la API", flush=True)
        return 0

    token = _require_token()
    with httpx.Client() as client:
        sid = _resolve_service_id(client, token)
        upsert_env_vars(client, token, sid, payload)
        if not args.skip_deploy:
            trigger_deploy(client, token, sid)

    wait_health()
    st = health_sbi()
    print(
        "[SBI Live]",
        {
            "enabled": st.get("enabled"),
            "enrolled": st.get("enrolled"),
            "recovery_configurada": st.get("recovery_configurada"),
            "owner": st.get("owner"),
        },
        flush=True,
    )
    if not st.get("recovery_configurada"):
        print(
            "[Aviso] recovery_configurada=false → secretos aún no visibles en el proceso. "
            "Espera el redeploy o revisa Environment en Dashboard.",
            flush=True,
        )

    if args.enroll:
        if not st.get("recovery_configurada"):
            raise SystemExit("[Enroll] Abortado: tokens SBI no están en Live todavía.")
        code = enroll_live()
        st2 = health_sbi()
        print("[SBI Live post-enroll]", st2, flush=True)
        return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
