# -*- coding: utf-8 -*-
"""
Auditoría de capas: trigger_ai_core / request_ui_action + integridad 6ef23f2.
Ejecutar: python -m unittest audit_system_flow.py
"""

from __future__ import annotations

import unittest


class AuditSystemFlow(unittest.TestCase):
    def test_app_state_enum(self):
        from cognicion.core_control import AppState

        self.assertEqual(AppState.IDLE.value, 0)
        self.assertEqual(AppState.AI_PROCESSING.value, 1)
        self.assertEqual(AppState.UI_LOCKED.value, 2)

    def test_request_ui_action_blocks_during_ai(self):
        from cognicion import ai_lock
        from cognicion.core_control import request_ui_action

        ai_lock.liberar(reason="audit_reset")
        ok = request_ui_action("camera")
        self.assertTrue(ok.get("allowed"))
        self.assertEqual(ok.get("status"), "OK")

        ai_lock.activar(reason="audit")
        blocked = request_ui_action("camera")
        self.assertEqual(blocked.get("status"), "BLOCKED")
        self.assertEqual(blocked.get("reason"), "AI_PRIORITY_ACTIVE")
        self.assertTrue(blocked.get("blocked"))
        ai_lock.liberar(reason="audit_done")

    def test_trigger_ai_core_only_activate_keeps_lock(self):
        from cognicion import ai_lock
        from cognicion.core_control import AppState, get_system_state, trigger_ai_core

        ai_lock.liberar(reason="reset")
        pack = trigger_ai_core({}, only_activate=True)
        self.assertTrue(pack.get("is_ai_active"))
        self.assertEqual(get_system_state()["status"], AppState.AI_PROCESSING.name)
        ai_lock.liberar(reason="done")
        self.assertEqual(get_system_state()["status"], AppState.IDLE.name)

    def test_trigger_ai_core_finally_restores(self):
        from cognicion import ai_lock, core_control

        ai_lock.liberar(reason="reset")
        core_control._system_state["status"] = core_control.AppState.IDLE

        def _boom(*_a, **_k):
            raise RuntimeError("fallo_simulado")

        original = core_control.execute_brain_sync
        core_control.execute_brain_sync = _boom  # type: ignore
        try:
            pack = core_control.trigger_ai_core(
                {"mensaje": "hola"},
                obtener_sesion=lambda _sid: ("s1", object()),
            )
            self.assertFalse(pack.get("ok"))
            self.assertTrue(pack.get("restaurado"))
            self.assertEqual(
                core_control._system_state["status"], core_control.AppState.IDLE
            )
            self.assertFalse(ai_lock.is_ai_active())
        finally:
            core_control.execute_brain_sync = original  # type: ignore

    def test_commit_6ef23f2_llm_helper_exists(self):
        """Integridad del fix de fallback LLM (commit 6ef23f2) + ruta Gemini."""
        from types import SimpleNamespace

        from cognicion import llm
        from settings import GEMINI_MODEL

        self.assertTrue(hasattr(llm, "_modelo_para_proveedor"))
        groq = SimpleNamespace(nombre="groq")
        self.assertIsNone(llm._modelo_para_proveedor(groq, "gemini-2.0-flash"))

        gemini = SimpleNamespace(nombre="gemini")
        self.assertEqual(
            llm._modelo_para_proveedor(gemini, "gemini-2.0-flash"),
            "gemini-2.0-flash",
        )
        self.assertEqual(llm._modelo_para_proveedor(gemini, None), GEMINI_MODEL)

    def test_voice_id_casing_adam_n_minuscula(self):
        """pNINz6... / ...Gcf... se normalizan a Adam con n minúscula."""
        from settings import ELEVENLABS_VOICE_ADAM, ELEVENLABS_VOICE_ID

        self.assertEqual(ELEVENLABS_VOICE_ADAM, "pNInz6obpgDQGcFmaJgB")
        self.assertIn("NIn", ELEVENLABS_VOICE_ADAM)
        if ELEVENLABS_VOICE_ID:
            self.assertEqual(ELEVENLABS_VOICE_ID.lower(), ELEVENLABS_VOICE_ADAM.lower())

    def test_api_secondary_blocked_when_locked(self):
        from fastapi.testclient import TestClient

        from app import app

        with TestClient(app) as client:
            r = client.post("/api/ai/lock", json={"activo": True, "reason": "audit"})
            self.assertEqual(r.status_code, 200)
            s = client.post("/api/ai/secondary", json={"accion": "camera"})
            self.assertEqual(s.status_code, 200)
            body = s.json()
            self.assertTrue(body.get("blocked") or body.get("status") == "BLOCKED")
            client.post("/api/ai/lock", json={"activo": False, "reason": "audit_done"})


if __name__ == "__main__":
    unittest.main()
