"""Tests maqueta Fase 1 — Salomón autónomo."""

from cognicion.autonoma.agentes_fase1 import agente_sintesis
from cognicion.autonoma.fase1 import ejecutar_fase1, iter_eventos_fase1
from cognicion.vision.analizador import analizar_escena


def test_fase1_saludo_sin_orquesta():
    pack = ejecutar_fase1("hola")
    assert pack.get("exito")
    assert "Israel" in (pack.get("texto") or "")
    assert (pack.get("metadata") or {}).get("fase") == "1"


def test_fase1_eventos_incluyen_pensando_y_done(monkeypatch):
    def fake_correr(consulta, vision_texto="", on_progress=None):
        if on_progress:
            on_progress("pensando", {"mensaje": "Estoy pensando…"})
            on_progress("buscando", {"mensaje": "Estoy buscando…"})
            on_progress("sintetizando", {"mensaje": "Estoy pensando la respuesta…"})
        return {
            "texto": "Israel, síntesis de prueba sobre " + consulta,
            "pack_busqueda": {"agentes_ok": ["web"], "total_hallazgos": 1},
            "hallazgos_texto": "dato",
            "agentes": ["busqueda", "sintesis"],
            "fase": "1",
        }

    monkeypatch.setattr(
        "cognicion.autonoma.fase1.correr_busqueda_y_sintesis_paralelo",
        fake_correr,
    )
    eventos = list(iter_eventos_fase1("Qué es la fotosíntesis según fuentes abiertas"))
    tipos = [e.get("type") for e in eventos]
    assert "status" in tipos
    assert tipos[-1] == "done"
    assert "Israel" in (eventos[-1].get("texto") or "")


def test_sintesis_respeta_israel():
    texto = agente_sintesis(
        "prueba",
        {
            "exito": True,
            "informes": [
                {
                    "agente": "web",
                    "exito": True,
                    "motor": "test",
                    "resumen": "La fotosíntesis convierte luz en energía química.",
                    "hallazgos": [],
                }
            ],
            "agentes_ok": ["web"],
            "agentes_fallidos": [],
            "total_hallazgos": 1,
            "consulta": "prueba",
        },
    )
    assert "Israel" in texto


def test_analizar_escena_sin_imagen():
    r = analizar_escena("")
    assert not r.exito
    assert r.error == "imagen_vacia"
