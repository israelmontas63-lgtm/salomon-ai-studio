# -*- coding: utf-8 -*-
"""
Redeploy Render — VISIBLE. Solo dispara deploy + smoke CSS HUD.
Uso: python scripts_redeploy_camera_hud.py
"""
import os
import time
import httpx
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

tok = (os.getenv("RENDER_API_KEY") or os.getenv("RENDER_API_TOKEN") or "").strip()
if not tok:
    raise SystemExit("Falta RENDER_API_KEY en .env (visible para el creador)")

headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
base = "https://api.render.com/v1"

service_id = (os.getenv("RENDER_SERVICE_ID") or "").strip()
if not service_id:
    r = httpx.get(f"{base}/services?limit=50", headers=headers, timeout=60)
    r.raise_for_status()
    for row in r.json():
        svc = row.get("service") or row
        name = (svc.get("name") or "").lower()
        if "salomon" in name:
            service_id = svc["id"]
            print("SERVICE", svc.get("name"), service_id)
            break

if not service_id:
    raise SystemExit("No service id")

print("POST deploy", service_id)
deploy = httpx.post(
    f"{base}/services/{service_id}/deploys",
    headers={**headers, "Content-Type": "application/json"},
    json={"clearCache": "do_not_clear"},
    timeout=60,
)
print("status", deploy.status_code)
print(deploy.text[:400])
deploy.raise_for_status()
dep = deploy.json()
deploy_id = dep.get("id") or (dep.get("deploy") or {}).get("id")
print("deploy_id", deploy_id)

for i in range(90):
    time.sleep(8)
    st = httpx.get(
        f"{base}/services/{service_id}/deploys/{deploy_id}",
        headers=headers,
        timeout=60,
    )
    st.raise_for_status()
    body = st.json()
    status = body.get("status") or (body.get("deploy") or {}).get("status")
    print(f"[{i}] {status}")
    if status in ("live", "update_failed", "canceled", "deactivated", "build_failed"):
        break

live = "https://salomon-ai-studio-1.onrender.com"
css = httpx.get(f"{live}/static/css/camera_hud.css?v=110.22.15", timeout=60, follow_redirects=True)
print("css", css.status_code)
print("has camera-btn-back", "camera-btn-back" in css.text)
print("has bottom: 36px", "bottom: 36px" in css.text)
print("has width: 72px", "width: 72px" in css.text)
ver = httpx.get(f"{live}/version.json", timeout=60, follow_redirects=True)
print("version", ver.status_code, ver.text[:220])
html = httpx.get(live + "/", timeout=60, follow_redirects=True)
print("html has camera-hud", "camera-hud" in html.text and "camera-btn-capture" in html.text)
