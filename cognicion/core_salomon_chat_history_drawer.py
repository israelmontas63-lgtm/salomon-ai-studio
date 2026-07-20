# -*- coding: utf-8 -*-
"""
[FILE: core_salomon_chat_history_drawer.py]
Gestor de Historial y Carpeta de Chats (Salomón AI).
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class SalomonChatHistoryDrawer:
    def __init__(self) -> None:
        self.module = "SalomonChatHistoryDrawer"
        self.target_ui = "Tools_Menu_Chat_Directory"

    def compile_chat_drawer_spec(self) -> str:
        spec = {
            "component": "Chat_History_Drawer_And_Selector",
            "features": [
                "Dedicated 'Chat' folder inside tools menu",
                "Displays the most recent chat session instantly upon opening",
                "Selector to switch between active chats and saved conversations",
            ],
            "assets": {
                "js": "static/js/chat_history_drawer.js",
                "css": "static/css/chat_history_drawer.css",
                "apis": ["/api/chats", "/api/chats/{id}/guardar", "/api/historial"],
            },
            "deployment": (
                "Auto-commit, push to Render production, and hot-load PWA with update badge."
            ),
        }
        return json.dumps(spec, indent=2)

    def verify(self) -> dict[str, Any]:
        js = (ROOT / "static" / "js" / "chat_history_drawer.js").read_text(
            encoding="utf-8", errors="ignore"
        )
        css = (ROOT / "static" / "css" / "chat_history_drawer.css").read_text(
            encoding="utf-8", errors="ignore"
        )
        settings = (ROOT / "static" / "js" / "settings_manager.js").read_text(
            encoding="utf-8", errors="ignore"
        )
        sesiones = (ROOT / "persistencia" / "sesiones.py").read_text(
            encoding="utf-8", errors="ignore"
        )
        ok = (
            "openDrawer" in js
            and "guardados" in js
            and "chat-drawer" in css
            and 'action: "chatDrawer"' in settings
            and "listar_sesiones" in sesiones
            and "marcar_sesion_guardada" in sesiones
        )
        return {"ok": ok, "module": self.module, "target_ui": self.target_ui}


if __name__ == "__main__":
    drawer = SalomonChatHistoryDrawer()
    print("[INICIANDO CONFIGURACION DE LA CARPETA DE CHATS EN SALOMON AI]")
    print(drawer.compile_chat_drawer_spec())
    print(drawer.verify())
