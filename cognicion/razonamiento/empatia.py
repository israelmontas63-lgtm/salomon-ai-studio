# -*- coding: utf-8 -*-
"""
Empatía cognitiva — detecta tono emocional y ajusta la reacción de Salomón.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TonoEmocional(str, Enum):
    CALMA = "calma"
    FRUSTRACION = "frustracion"
    ENTUSIASMO = "entusiasmo"
    DESARROLLO = "desarrollo"
    URGENCIA = "urgencia"


@dataclass(frozen=True)
class PerfilEmpatico:
    tono: TonoEmocional
    confianza: float
    instruccion: str

    def to_dict(self) -> dict:
        return {
            "tono": self.tono.value,
            "confianza": self.confianza,
            "instruccion": self.instruccion,
        }


_FRUSTRACION = (
    "no funciona", "otra vez", "harta", "harto", "frustrad", "molesto",
    "molesta", "carajo", "diablo", "maldit", "odio", "imposible", "siempre falla",
    "no sirve", "estoy cansado", "ya no aguanto", "auxilio", "help me",
    "broken", "useless", "wtf", "damn",
)

_ENTUSIASMO = (
    "excelente", "genial", "perfecto", "gracias", "brutal", "increíble",
    "increible", "vamos", "listo", "funcionó", "funciono", "éxito", "exito",
)

_DESARROLLO = (
    "implementa", "código", "codigo", "refactor", "endpoint", "función",
    "funcion", "debug", "arquitectura", "optimiza", "python", "javascript",
    "c++", "html", "deploy", "api",
)

_URGENCIA = (
    "urgente", "ya", "ahora mismo", "rápido", "rapido", "inmediato",
    "emergency", "asap", "caído", "caido", "producción", "produccion",
)


def detectar_tono(entrada: str) -> PerfilEmpatico:
    """Clasifica el tono del prompt sin llamadas externas."""
    texto = (entrada or "").lower()
    scores = {
        TonoEmocional.FRUSTRACION: sum(1 for p in _FRUSTRACION if p in texto),
        TonoEmocional.ENTUSIASMO: sum(1 for p in _ENTUSIASMO if p in texto),
        TonoEmocional.DESARROLLO: sum(1 for p in _DESARROLLO if p in texto),
        TonoEmocional.URGENCIA: sum(1 for p in _URGENCIA if p in texto),
    }
    tono = max(scores, key=scores.get)  # type: ignore[arg-type]
    raw = scores[tono]
    if raw == 0:
        return PerfilEmpatico(
            tono=TonoEmocional.CALMA,
            confianza=0.4,
            instruccion=(
                "[Empatía cognitiva — ZEN] Tono sereno y alegre. "
                "Escucha con calma, responde con claridad natural, "
                "sin prisa ni dramatismo. Motiva con suavidad y precisión."
            ),
        )

    confianza = min(0.95, 0.45 + 0.15 * raw)
    if tono == TonoEmocional.FRUSTRACION:
        return PerfilEmpatico(
            tono=tono,
            confianza=confianza,
            instruccion=(
                "[Empatía cognitiva — FRUSTRACIÓN] Prioriza calma y contención. "
                "Valida el esfuerzo de Israel, reduce ruido técnico al inicio, "
                "luego ofrece un plan corto y seguro. Sin dramatismo. "
                "Proyecta serenidad: el problema es resoluble."
            ),
        )
    if tono == TonoEmocional.URGENCIA:
        return PerfilEmpatico(
            tono=tono,
            confianza=confianza,
            instruccion=(
                "[Empatía cognitiva — URGENCIA] Sé breve, preciso y accionable. "
                "Primero el fix o el siguiente paso; contexto después. "
                "Mantén la voz firme y tranquila, sin estrés contagioso."
            ),
        )
    if tono == TonoEmocional.DESARROLLO:
        return PerfilEmpatico(
            tono=tono,
            confianza=confianza,
            instruccion=(
                "[Empatía cognitiva — DESARROLLO] Modo técnico limpio: preciso, "
                "lógico, arquitectura clara. Explica el porqué en una frase y "
                "entrega código verificable. Fluidez sin ruido."
            ),
        )
    if tono == TonoEmocional.ENTUSIASMO:
        return PerfilEmpatico(
            tono=tono,
            confianza=confianza,
            instruccion=(
                "[Empatía cognitiva — ENTUSIASMO] Celebra con elegancia (negro y oro), "
                "alegría serena y energía constructiva. Avanza motivando, sin excesos."
            ),
        )
    return PerfilEmpatico(
        tono=TonoEmocional.CALMA,
        confianza=confianza,
        instruccion=(
            "[Empatía cognitiva — ZEN] Mantén tono sabio, cercano y libre de estrés."
        ),
    )


def bloque_empatia(entrada: str) -> tuple[str, dict]:
    perfil = detectar_tono(entrada)
    return perfil.instruccion, perfil.to_dict()
