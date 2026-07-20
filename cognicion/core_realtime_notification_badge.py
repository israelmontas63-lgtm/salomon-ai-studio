# -*- coding: utf-8 -*-
"""
[FILE: core_realtime_notification_badge.py] — Badge post-deploy en tuerquita.
Created by Israel Monta - Salomón AI Studio
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def get_realtime_badge_instruction() -> str:
    notification_spec = {
        "event_trigger": "post_deploy_success",
        "target_ui_element": "settings_gear_icon (tuerquita)",
        "badge_specs": {
            "type": "micro_notification_card",
            "visibility": "human_readable_micro",
            "position": "anchored_top_right_of_gear",
        },
        "action": "Display real-time notification badge instantly upon deployment.",
        "client": "static/js/realtime_notification_badge.js",
        "stream": "/api/deploy/stream",
        "poll": "/api/version",
    }
    return json.dumps(notification_spec, indent=2)


def verify_assets() -> dict:
    js = ROOT / "static" / "js" / "realtime_notification_badge.js"
    css = ROOT / "static" / "css" / "update_styles.css"
    html = ROOT / "templates" / "index.html"
    ok = js.is_file() and "deploy-badge" in html.read_text(encoding="utf-8")
    ok = ok and "deploy-badge" in css.read_text(encoding="utf-8")
    return {"ok": ok, "js": str(js.relative_to(ROOT))}


if __name__ == "__main__":
    print(get_realtime_badge_instruction())
    print(verify_assets())
