import json
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "lighthouse-pwa.json"
if not p.is_file():
    raise SystemExit("missing lighthouse-pwa.json")

d = json.loads(p.read_text(encoding="utf-8"))
pwa = d.get("categories", {}).get("pwa", {})
print("PWA score:", pwa.get("score"))

audits = d.get("audits", {})
keys = [
    "installable-manifest",
    "service-worker",
    "splash-screen",
    "themed-omnibox",
    "maskable-icon",
    "content-width",
    "viewport",
    "apple-touch-icon",
    "is-on-https",
]
for k in keys:
    a = audits.get(k)
    if not a:
        continue
    print(f"{k}: score={a.get('score')} | {a.get('title')}")
    details = a.get("details") or {}
    for it in (details.get("items") or [])[:12]:
        print("  -", it.get("reason") or it.get("label") or it)

print("--- ZERO SCORES (relevant) ---")
for k, a in audits.items():
    if a.get("score") != 0:
        continue
    if any(x in k for x in ("install", "service", "maskable", "splash", "viewport", "https", "manifest", "pwa")):
        desc = (a.get("description") or "").replace("\n", " ")[:200]
        print(f"{k}: {a.get('title')} | {desc}")
