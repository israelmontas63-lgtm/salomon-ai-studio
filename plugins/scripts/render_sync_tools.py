# -*- coding: utf-8 -*-
"""
Sincroniza DEEPSEEK / TAVILY / EXA (y media opcional) local → Render Environment.

Requiere en .env (nunca imprime valores):
  RENDER_API_KEY=rnd_...
  RENDER_SERVICE_ID=srv-...   (opcional)

Uso:
  python plugins/scripts/render_sync_tools.py
  python plugins/scripts/render_sync_tools.py --dry-run
  python plugins/scripts/render_sync_tools.py --redeploy
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

API = "https://api.render.com/v1"
LIVE = "https://salomon-ai-studio-1.onrender.com"
SERVICE_NAME_HINTS = ("salomon-ai-studio-1", "salomon-ai-studio", "salomon-ai")

TOOL_KEYS = (
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_MODEL",
    "DEEPSEEK_BASE_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_MODEL",
    "CEREBRAS_API_KEY",
    "CEREBRAS_MODEL",
    "MISTRAL_API_KEY",
    "MISTRAL_MODEL",
    "TAVILY_API_KEY",
    "TAVILY_SEARCH_DEPTH",
    "EXA_API_KEY",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_VOICE_ID",
    "DEEPGRAM_API_KEY",
    "FAL_KEY",
    "REPLICATE_API_TOKEN",
    "REPLICATE_API_KEY",
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
    "COHERE_API_KEY",
    "GEMINI_API_KEY",
    "TTS_ASYNC",
    "MEDIA_ASYNC_DEFAULT",
    "MODO_EJECUCION",
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
            "  1) Dashboard → Account Settings → API Keys\n"
            "  2) .env: RENDER_API_KEY=rnd_...\n"
            "  3) python plugins/scripts/render_sync_tools.py --redeploy"
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
                print(f"[Render] Servicio: {name} ({sid})", flush=True)
                return sid
    listing = ", ".join(n for n, _ in names) or "(ninguno)"
    raise SystemExit(
        "[Render] Añade RENDER_SERVICE_ID=srv-... en .env\n"
        f"Servicios: {listing}"
    )


def _tools_payload() -> dict[str, str]:
    out: dict[str, str] = {}
    missing: list[str] = []
    defaults = {
        "DEEPSEEK_MODEL": "deepseek-chat",
        "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
        "OPENROUTER_MODEL": "deepseek/deepseek-chat",
        "CEREBRAS_MODEL": "llama-3.3-70b",
        "MISTRAL_MODEL": "mistral-small-latest",
        "TAVILY_SEARCH_DEPTH": "advanced",
        "ELEVENLABS_VOICE_ID": "pNInz6obpgDQGcFmaJgB",
        "TTS_ASYNC": "false",
        "MEDIA_ASYNC_DEFAULT": "false",
        "MODO_EJECUCION": "true",
    }
    # REPLICATE: prefer TOKEN canónico; si solo hay KEY, sincronizar ambas.
    for k in TOOL_KEYS:
        v = (os.getenv(k) or "").strip() or defaults.get(k, "")
        if k == "REPLICATE_API_TOKEN" and not v:
            v = (os.getenv("REPLICATE_API_KEY") or "").strip()
        if k == "REPLICATE_API_KEY" and not v:
            v = (os.getenv("REPLICATE_API_TOKEN") or "").strip()
        if not v and k.endswith("_API_KEY") and k not in (
            "REPLICATE_API_KEY",  # alias opcional
        ):
            # No abortar por opcionales; solo marcar críticas
            if k in (
                "DEEPSEEK_API_KEY",
                "ELEVENLABS_API_KEY",
                "FAL_KEY",
                "TAVILY_API_KEY",
            ):
                missing.append(k)
            continue
        if v:
            out[k] = v
    if missing:
        raise SystemExit("[Render] Faltan en .env local: " + ", ".join(missing))
    return out


def upsert_env_vars(
    client: httpx.Client, token: str, service_id: str, payload: dict[str, str]
) -> None:
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
                f"[Render] Falló {key}: HTTP {res.status_code} {res.text[:240]}"
            )
        print(f"[Render] OK {key} (len={len(value)})", flush=True)


def trigger_deploy(client: httpx.Client, token: str, service_id: str) -> str:
    res = client.post(
        f"{API}/services/{service_id}/deploys",
        headers=_headers(token),
        json={"clearCache": "do_not_clear"},
        timeout=60.0,
    )
    if res.status_code >= 400:
        raise SystemExit(f"[Render] Deploy: HTTP {res.status_code} {res.text[:240]}")
    body = res.json()
    deploy = body.get("deploy") or body
    did = deploy.get("id") or "?"
    print(f"[Render] Redeploy: {did}", flush=True)
    return str(did)


def wait_tools(timeout_s: float = 420.0) -> dict:
    url = f"{LIVE}/api/tools/conectividad"
    t0 = time.time()
    last = ""
    with httpx.Client(timeout=45.0) as c:
        while time.time() - t0 < timeout_s:
            try:
                r = c.get(url)
                if r.status_code == 200:
                    data = r.json()
                    keys = ((data.get("llm") or {}).get("keys") or {})
                    web = data.get("web") or {}
                    ok = bool(keys.get("deepseek")) and bool(
                        web.get("tavily_key") or web.get("exa_key")
                    )
                    print(
                        f"[Tools] deepseek={keys.get('deepseek')} "
                        f"tavily={web.get('tavily_key')} exa={web.get('exa_key')}",
                        flush=True,
                    )
                    if ok:
                        return data
                    last = "keys aún missing en runtime"
                else:
                    last = f"HTTP {r.status_code}"
            except Exception as exc:
                last = str(exc)
            print(f"[Tools] esperando… ({last})", flush=True)
            time.sleep(12)
    raise SystemExit(f"[Tools] Timeout: {last}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--redeploy", action="store_true")
    ap.add_argument("--wait", action="store_true")
    args = ap.parse_args()

    payload = _tools_payload()
    print("[Local] keys a sincronizar:", ", ".join(payload.keys()), flush=True)
    if args.dry_run:
        for k, v in payload.items():
            print(f"  {k}=set:{len(v)}c", flush=True)
        return 0

    token = _require_token()
    with httpx.Client(timeout=60.0) as client:
        sid = _resolve_service_id(client, token)
        upsert_env_vars(client, token, sid, payload)
        if args.redeploy:
            trigger_deploy(client, token, sid)
    if args.wait or args.redeploy:
        wait_tools()
        print("[OK] Render tools conectados", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
