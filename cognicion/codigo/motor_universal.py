# -*- coding: utf-8 -*-
"""
Universal Code Engine v60 — ingeniería de software autogestionada.
Soporta Python, JS, HTML, C++ + operaciones lógico-matemáticas seguras.
"""

from __future__ import annotations

import ast
import operator
import re
from dataclasses import dataclass
from typing import Any

from cognicion.seguridad.sandbox import ejecutar_aislado

LENGUAJES = ("python", "javascript", "js", "html", "c++", "cpp", "typescript", "ts")

_PALABRAS_CODIGO = (
    "código", "codigo", "función", "funcion", "script", "programa",
    "python", "javascript", "html", "c++", "cpp", "typescript",
    "implementa", "implementar", "escribe una función", "escribe una funcion",
    "genera código", "genera codigo", "debug", "optimiza", "refactor",
)

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


@dataclass
class ResultadoMotorCodigo:
    activo: bool
    tipo: str
    detalle: str | None = None
    valor: Any = None
    bloque_contexto: str | None = None

    def to_dict(self) -> dict:
        return {
            "activo": self.activo,
            "tipo": self.tipo,
            "detalle": self.detalle,
            "valor": self.valor,
            "engine": "UniversalCodeEngine",
            "version": "60.0.0",
        }


def requiere_motor_codigo(entrada: str) -> bool:
    texto = (entrada or "").lower()
    return any(p in texto for p in _PALABRAS_CODIGO)


def _eval_nodo(node: ast.AST) -> float | int:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_nodo(node.operand))  # type: ignore[operator]
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_nodo(node.left), _eval_nodo(node.right))  # type: ignore[operator]
    raise ValueError("expresion_no_permitida")


def evaluar_matematica_segura(entrada: str) -> ResultadoMotorCodigo | None:
    """Evalúa expresiones aritméticas puras vía AST (sin eval libre)."""
    texto = (entrada or "").strip().lower()
    # Extraer expresión tipo "cuanto es 12*(3+4)" o "calcula 2**10"
    m = re.search(
        r"(?:calcula|cu[aá]nto es|suma|multiplica|resuelve)?\s*([0-9\.\s\+\-\*\/\%\(\)\^]+)\s*$",
        texto,
        flags=re.IGNORECASE,
    )
    expr = None
    if m:
        expr = m.group(1).strip().replace("^", "**")
    elif re.fullmatch(r"[0-9\.\s\+\-\*\/\%\(\)\^]+", texto):
        expr = texto.replace("^", "**")
    if not expr or not re.search(r"\d", expr):
        return None
    if len(expr) > 120:
        return None

    def _run() -> float | int:
        tree = ast.parse(expr, mode="eval")
        return _eval_nodo(tree.body)

    sand = ejecutar_aislado(_run, timeout_seg=2)
    if not sand.exito:
        return ResultadoMotorCodigo(
            activo=True,
            tipo="matematica",
            detalle=sand.error or "fallo_sandbox",
        )
    return ResultadoMotorCodigo(
        activo=True,
        tipo="matematica",
        detalle="evaluacion_ast_sandbox",
        valor=sand.resultado,
        bloque_contexto=(
            "[Universal Code Engine — Matemática verificada]\n"
            f"Expresión: {expr}\n"
            f"Resultado sandbox: {sand.resultado}\n"
            "Usa este resultado exacto en tu respuesta."
        ),
    )


def bloque_motor_codigo(entrada: str) -> ResultadoMotorCodigo:
    """
    Prepara contexto de ingeniería de software + intenta matemática segura.
    """
    math = evaluar_matematica_segura(entrada)
    if math and math.valor is not None:
        return math

    if not requiere_motor_codigo(entrada):
        return ResultadoMotorCodigo(activo=False, tipo="idle")

    return ResultadoMotorCodigo(
        activo=True,
        tipo="ingenieria",
        detalle="prompt_uce",
        bloque_contexto=(
            "[Universal Code Engine v60 — Ingeniería autogestionada]\n"
            "Lenguajes activos: Python, JavaScript, HTML, C++ (y TypeScript si aplica).\n"
            "Protocolo de entrega:\n"
            "1) Diseña la lógica (breve).\n"
            "2) Escribe el código limpio y tipado cuando ayude.\n"
            "3) Explica la lógica en 2-4 frases.\n"
            "4) Indica cómo probarlo (ejemplo de input/output o assert mental).\n"
            "5) Auto-revisa fallos obvios (null, bordes, seguridad) antes de entregar.\n"
            "Frase de apertura obligatoria al entregar código:\n"
            '"He analizado tu petición, he diseñado esta lógica, y aquí está el código '
            'optimizado para tu proyecto Salomón AI".\n'
            "No toques camera-engine.js ni el Golden State de cámara sin AUTORIZADO."
        ),
    )
