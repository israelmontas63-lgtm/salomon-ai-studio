# -*- coding: utf-8 -*-
"""
[FILE: fix_central_button_alignment.py] — Corrección Geométrica de UI
Centrado absoluto del botón 'S' en #nav_bar_container.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CENTERING_CSS = """
/* [force_absolute_center] Botón S — centro geométrico exacto (50%) */
#nav_bar_container.control-bar,
#nav_bar_container.nav-bar-container,
footer#nav_bar_container {
  display: grid !important;
  grid-template-columns: 1fr auto 1fr !important;
  align-items: center !important;
  justify-items: stretch !important;
  column-gap: 0 !important;
  gap: 0 0 !important;
}

#nav_bar_container #side-close {
  grid-column: 1;
  justify-self: start;
  width: auto;
  max-width: 100%;
}

#nav_bar_container #smart-button {
  grid-column: 2;
  justify-self: center;
  margin: 0 !important;
  margin-left: 0 !important;
  margin-right: 0 !important;
  position: relative;
  left: auto;
  right: auto;
  transform: none;
}

#nav_bar_container #side-aa {
  grid-column: 3;
  justify-self: end;
  width: auto;
  max-width: 100%;
}
"""


def get_centering_calculation() -> str:
    """
    Cálculo de ingeniería para centrar el botón 'S'.
    Grid 1fr | auto | 1fr → espacio izquierdo = espacio derecho (50% viewport del bar).
    """
    print("[UI_ENGINEERING] Calculando centro absoluto para el boton 'S'...")
    centering_instruction = {
        "action": "force_absolute_center",
        "target": "central_navigation_button",
        "method": "CSS Grid 1fr auto 1fr",
        "verification_points": ["equal_space_left", "equal_space_right"],
        "css_file": "static/css/boton.css",
        "selector": "#nav_bar_container #smart-button",
    }
    return json.dumps(centering_instruction, indent=2)


def apply_centering_patch() -> dict:
    """Asegura que boton.css contenga la regla de centrado absoluto."""
    css_path = ROOT / "static" / "css" / "boton.css"
    text = css_path.read_text(encoding="utf-8")
    marker = "/* [force_absolute_center]"
    if marker in text:
        return {"ok": True, "patched": False, "path": str(css_path)}
    css_path.write_text(text.rstrip() + "\n\n" + CENTERING_CSS.strip() + "\n", encoding="utf-8")
    return {"ok": True, "patched": True, "path": str(css_path)}


if __name__ == "__main__":
    print(get_centering_calculation())
    print(apply_centering_patch())
