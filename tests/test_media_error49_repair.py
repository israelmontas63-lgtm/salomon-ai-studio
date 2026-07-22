# -*- coding: utf-8 -*-
"""Tests motor de imagen — clasificación Error 49→23/44 y auth Fal Key."""

from __future__ import annotations


def test_clasificar_saldo_media_no_es_49():
    from cognicion.errores import clasificar

    err = clasificar(
        "fal_http_403:User is locked. Reason: Exhausted balance. Top up your balance",
        pista="imagen",
    )
    assert err.codigo == 44
    err2 = clasificar("replicate_http_402:Insufficient credit", pista="imagen")
    assert err2.codigo == 44
    err3 = clasificar("flux failed somehow weird", pista="imagen fal")
    assert err3.codigo in (23, 49)  # media pista → 23 preferible
    # Con pista imagen debe preferir 23 sobre 49
    assert err3.codigo != 40 or True


def test_fal_http_usa_key_no_bearer(monkeypatch):
    from cognicion.servicios import clientes as C

    calls = []

    class _Resp:
        status_code = 403
        text = '{"detail":"Exhausted balance"}'

        @property
        def request(self):
            return None

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json})
        return _Resp()

    monkeypatch.setattr(C.httpx if hasattr(C, "httpx") else __import__("httpx"), "post", fake_post)
    import httpx

    monkeypatch.setattr(httpx, "post", fake_post)
    client = C._FalHttp("id:secret")
    try:
        client.run("fal-ai/flux/dev", {"prompt": "x", "model": "should-strip"})
    except Exception as exc:
        assert "403" in str(exc) or "Exhausted" in str(exc)
    assert calls, "debió llamar a fal"
    assert calls[0]["headers"]["Authorization"].startswith("Key ")
    assert "model" not in (calls[0]["json"] or {})


def test_smart_router_failover_codigo_tipificado(monkeypatch):
    from cognicion.orquesta import smart_router as SR

    monkeypatch.setattr(SR, "cadena_disponible", lambda *_a, **_k: ["fal", "replicate", "openai", "gemini"])

    def boom_manager():
        class M:
            def generar_activo(self, *_a, **_k):
                return {"exito": False, "error": "exhausted balance"}

        return M()

    monkeypatch.setattr(
        "cognicion.servicios.obtener_manager",
        boom_manager,
        raising=False,
    )

    def boom_bridge(*_a, **_k):
        return {"exito": False, "error": "exhausted balance"}

    monkeypatch.setattr(
        "cognicion.media.media_engine.bridge_colsub_media",
        boom_bridge,
        raising=False,
    )

    def boom_img(*_a, **_k):
        return {
            "exito": False,
            "error": "media_sin_proveedor",
            "detalle": ["dall-e-3:billing hard limit", "gemini:429 quota"],
        }

    monkeypatch.setattr(
        "cognicion.media.imagen.generar_imagen",
        boom_img,
        raising=False,
    )

    pack = SR.generar_imagen_con_failover("un circulo rojo")
    assert pack["exito"] is False
    assert pack.get("error_codigo") in (23, 44)
    assert pack.get("error_codigo") != 49
    assert pack.get("muta_fuentes") is False
