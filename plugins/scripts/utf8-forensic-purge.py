# -*- coding: utf-8 -*-
"""Forensic UTF-8 purge helpers for Salomón UI v31."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def patch_welcome_bundle() -> None:
    p = ROOT / "studio/dist/assets/index-BdcDx9nN.js"
    data = p.read_bytes()
    start = data.find(b"var ie=[")
    end = data.find(b"],ae=[")
    if start < 0 or end < 0:
        raise SystemExit("welcome array not found in bundle")
    new = "var ie=[`Hola, Israel. Soy Salomón.`],ae=[".encode("utf-8")
    data2 = data[:start] + new + data[end + len(b"],ae=[") :]
    p.write_bytes(data2)
    assert b"Hola, Israel. Soy Salom" in p.read_bytes()
    assert b"Bienvenido. Soy Salom" not in p.read_bytes()
    print("bundle_welcome_ok")


def write_constants() -> None:
    p = ROOT / "studio/src/data/constants.js"
    p.write_text(
        'export const WELCOME_MESSAGES = [\n'
        '  "Hola, Israel. Soy Salomón.",\n'
        "];\n\n"
        "export const TOOLS_MENU = [];\n\n"
        "export const ACCOUNT_MENU = [];\n",
        encoding="utf-8",
        newline="\n",
    )
    print("constants_ok")


def patch_update_js() -> None:
    for rel in ("studio/dist/salomon-update.js", "studio/public/salomon-update.js"):
        p = ROOT / rel
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8", errors="replace")
        t2 = t
        t2 = re.sub(
            r'el\.textContent = "Versi[^"]+";',
            'el.textContent = "Versión: " + ver;',
            t2,
        )
        t2 = re.sub(
            r'toast\("Actualizando Salom[^"]+"\)',
            'toast("Actualizando Salomón…")',
            t2,
        )
        t2 = re.sub(
            r'toast\("Reintentando actualizaci[^"]+"\)',
            'toast("Reintentando actualización…")',
            t2,
        )
        t2 = re.sub(
            r'title="Forzar actualizaci[^"]+"',
            'title="Forzar actualización desde Render"',
            t2,
        )
        if t2 != t:
            p.write_text(t2, encoding="utf-8", newline="\n")
            print("patched", rel)
        else:
            print("skip", rel)


def write_version() -> None:
    v = {
        "timestamp_iso": "2026-07-17T18:50:00Z",
        "timestamp": 1752787800,
        "version": "31.0.0",
        "channel": "main",
        "label": "ui-utf8-forensic-purge",
        "stability": "STABLE_PRODUCTION_READY",
        "notes": "UTF-8 enforcement index.html + welcome plain text. Camera core unchanged.",
    }
    (ROOT / "version.json").write_text(
        json.dumps(v, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("version_ok")


def verify_index() -> None:
    html = (ROOT / "studio/dist/index.html").read_text(encoding="utf-8")
    head = html[:250]
    assert 'charset="UTF-8"' in head
    assert "Content-Type" in head and "charset=UTF-8" in head
    assert "<title>Salomón</title>" in html
    assert "Ã" not in html
    assert "Limpiando memoria de interfaz" in html
    print("index_utf8_ok")


if __name__ == "__main__":
    patch_welcome_bundle()
    write_constants()
    patch_update_js()
    write_version()
    # sync public index
    src = ROOT / "studio/dist/index.html"
    (ROOT / "studio/public/index.html").write_bytes(src.read_bytes())
    verify_index()
    print("DONE_v31")
