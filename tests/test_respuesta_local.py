"""Tests respuesta local sin LLM en la nube."""

from cognicion.respuesta_local import respuesta_local_chat


def test_respuesta_local_con_bloque_wikipedia():
    mensaje = """[Wikipedia — Python]
Python es un lenguaje de programación.

Pregunta del usuario: qué es Python"""
    texto = respuesta_local_chat(mensaje, [], "")
    assert "Python" in texto
    assert "Israel" in texto


def test_respuesta_local_sin_contexto():
    texto = respuesta_local_chat("Hola Salomón", [], "")
    assert "Israel" in texto
    assert "nube" in texto.lower() or "aquí estoy" in texto.lower()
