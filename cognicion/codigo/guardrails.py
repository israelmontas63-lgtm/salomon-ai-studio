# -*- coding: utf-8 -*-
"""
Guardrails de código — sandboxing estático interno antes de entregar a Israel.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field


@dataclass
class InformeGuardrails:
    ok: bool = True
    lenguaje: str | None = None
    advertencias: list[str] = field(default_factory=list)
    bloqueos: list[str] = field(default_factory=list)
    bloques_revisados: int = 0

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "lenguaje": self.lenguaje,
            "advertencias": self.advertencias,
            "bloqueos": self.bloqueos,
            "bloques_revisados": self.bloques_revisados,
            "sandbox": "interno",
        }


_FENCE = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL | re.IGNORECASE)

_PATRONES_PELIGROSOS = (
    (r"\brm\s+-rf\b", "comando destructivo rm -rf"),
    (r"\bos\.system\s*\(", "os.system"),
    (r"\bsubprocess\.(call|run|Popen)\b", "subprocess"),
    (r"\beval\s*\(", "eval dinámico"),
    (r"\bexec\s*\(", "exec dinámico"),
    (r"__import__\s*\(", "__import__ dinámico"),
    (r"camera-engine\.js", "toque a CameraEngine protegido"),
    (r"studio/dist/camera", "ruta de cámara Golden State"),
    (r"\bDROP\s+TABLE\b", "SQL DROP TABLE"),
    (r"document\.cookie", "acceso a cookies"),
)


def extraer_bloques_codigo(texto: str) -> list[tuple[str, str]]:
    """Devuelve lista de (lenguaje, codigo)."""
    out: list[tuple[str, str]] = []
    for m in _FENCE.finditer(texto or ""):
        lang = (m.group(1) or "text").lower().strip()
        code = (m.group(2) or "").strip()
        if code:
            out.append((lang, code))
    return out


def _analizar_python_ast(codigo: str, informe: InformeGuardrails) -> None:
    try:
        tree = ast.parse(codigo)
    except SyntaxError as exc:
        informe.advertencias.append(f"syntax_error: {exc.msg}")
        return
    prohibidos = {"eval", "exec", "compile", "__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in prohibidos:
            informe.bloqueos.append(f"ast:{node.id}")
        if isinstance(node, ast.Attribute) and node.attr in {"system", "popen"}:
            informe.advertencias.append(f"attr_riesgosa:{node.attr}")


def analizar_codigo(codigo: str, lenguaje: str = "text") -> InformeGuardrails:
    informe = InformeGuardrails(lenguaje=lenguaje, bloques_revisados=1)
    lower = codigo.lower()
    for pat, label in _PATRONES_PELIGROSOS:
        if re.search(pat, codigo, flags=re.IGNORECASE):
            if "camera" in label or "destructivo" in label or "DROP" in label:
                informe.bloqueos.append(label)
            else:
                informe.advertencias.append(label)
    if lenguaje in {"python", "py"}:
        _analizar_python_ast(codigo, informe)
    if "while true" in lower or "while (true)" in lower:
        informe.advertencias.append("posible_bucle_infinito")
    informe.ok = not informe.bloqueos
    return informe


def analizar_respuesta_codigo(texto: str) -> InformeGuardrails:
    """Sandbox interno sobre todos los fences de la respuesta."""
    bloques = extraer_bloques_codigo(texto)
    if not bloques:
        return InformeGuardrails(ok=True, bloques_revisados=0)

    acumulado = InformeGuardrails(bloques_revisados=len(bloques))
    for lang, code in bloques:
        parcial = analizar_codigo(code, lang)
        acumulado.lenguaje = lang
        acumulado.advertencias.extend(parcial.advertencias)
        acumulado.bloqueos.extend(parcial.bloqueos)
    acumulado.ok = not acumulado.bloqueos
    return acumulado
