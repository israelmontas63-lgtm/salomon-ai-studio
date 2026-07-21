# -*- coding: utf-8 -*-
"""Añade 'Actualizar' al menú H del bundle de producción (UTF-8)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "studio" / "dist" / "assets" / "index-BdcDx9nN.js"


def main() -> None:
    data = BUNDLE.read_text(encoding="utf-8")
    changed = False

    if "`Actualizar`]" not in data and ",`Actualizar`]," not in data:
        old = ",`Gestor de APIs`],oe=["
        new = ",`Gestor de APIs`,`Actualizar`],oe=["
        if old not in data:
            raise SystemExit("ae anchor not found")
        data = data.replace(old, new, 1)
        changed = True
        print("ae: Actualizar added")
    else:
        print("ae: Actualizar already present")

    if "if(e===`Actualizar`)" not in data:
        needle = "if(e===`Gestor de APIs`)"
        handler = (
            "if(e===`Actualizar`){"
            "try{window.SalomonUpdate&&window.SalomonUpdate.apply?"
            "window.SalomonUpdate.apply():"
            "(window.location.href=`/?_salomon_force=`+Date.now())}"
            "catch(t){}"
            "d(!1);return}"
            "if(e===`Gestor de APIs`)"
        )
        if needle not in data:
            raise SystemExit("handler anchor not found")
        data = data.replace(needle, handler, 1)
        changed = True
        print("handler: Actualizar inserted")
    else:
        print("handler: already present")

    if changed:
        BUNDLE.write_text(data, encoding="utf-8", newline="\n")
    print("ok", "Actualizar count=", data.count("Actualizar"))


if __name__ == "__main__":
    main()
