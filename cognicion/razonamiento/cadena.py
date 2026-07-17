# -*- coding: utf-8 -*-
"""
Chain of Thought v60 — ciclo obligatorio:
Análisis → Planificación → Ejecución → Verificación (+ Pensamiento Crítico).
"""

from __future__ import annotations

import re

PALABRAS_TECNICAS = (
    "código", "codigo", "error", "bug", "implementa", "implementar",
    "función", "funcion", "corregir", "corrección", "correccion",
    "debug", "arregla", "arreglar", "refactor", "api", "endpoint",
    "backend", "frontend", "react", "python", "fastapi", "gemini",
    "integrar", "módulo", "modulo", "archivo", "deploy", "configura",
    "typescript", "javascript", "css", "html", "c++", "cpp",
    "base de datos", "arquitectura", "algoritmo", "optimiza", "optimizar",
    "suma", "multiplica", "calcula", "ecuación", "ecuacion", "math",
    "programa", "script", "clase", "class", "def ",
)

PALABRAS_COMPLEJAS = (
    "explica", "diseñar", "diseña", "compara", "analiza",
    "planifica", "estrategia", "por qué", "porque", "cómo harías",
    "como harias", "paso a paso", "ventaja", "riesgo",
)

MARCADOR_RESPUESTA = "---RESPUESTA---"
CICLO_COT = ("analisis", "planificacion", "ejecucion", "verificacion")


def requiere_razonamiento(entrada: str) -> bool:
    """Detecta tareas técnicas o complejas que requieren CoT."""
    texto = (entrada or "").lower()
    if any(palabra in texto for palabra in PALABRAS_TECNICAS):
        return True
    if any(palabra in texto for palabra in PALABRAS_COMPLEJAS) and len(texto) > 40:
        return True
    return False


def pensamiento_critico_viable(entrada: str) -> dict[str, str | bool]:
    """Evalúa viabilidad interna antes de comprometer una solución."""
    texto = (entrada or "").strip()
    lower = texto.lower()
    riesgos: list[str] = []
    if any(x in lower for x in ("borra", "eliminar todo", "rm -rf", "drop table")):
        riesgos.append("operacion_destructiva")
    if any(x in lower for x in ("camera-engine", "studio/dist/camera", "hot-swap")):
        riesgos.append("nucleo_camara_protegido")
    if len(texto) < 8:
        riesgos.append("peticion_ambigua")
    viable = "operacion_destructiva" not in riesgos
    return {
        "viable": viable,
        "riesgos": ", ".join(riesgos) if riesgos else "ninguno",
        "alcance": "codigo" if requiere_razonamiento(texto) else "general",
    }


def aplicar_cadena_de_pensamiento(entrada: str, *, tono_bloque: str = "") -> str:
    """Envuelve la entrada con el ciclo APVE + pensamiento crítico."""
    critico = pensamiento_critico_viable(entrada)
    tono = f"\n{tono_bloque}\n" if tono_bloque else "\n"
    return f"""[Cognitive Core v60 — Chain of Thought / Software Vivo Pensante]

Ciclo OBLIGATORIO (interno, no lo muestres al usuario):
1) ANÁLISIS — qué pide Israel exactamente y qué restricciones hay.
2) PLANIFICACIÓN — pasos concretos en orden.
3) EJECUCIÓN — aplicar la solución (código, cálculo o explicación).
4) VERIFICACIÓN — revisar fallos, edge cases y coherencia con Salomón AI Studio.

Pensamiento crítico de viabilidad:
- viable={critico["viable"]}
- riesgos={critico["riesgos"]}
- alcance={critico["alcance"]}
Si viable=False o hay riesgo de núcleo de cámara, rechaza con calma y propone alternativa segura.
{tono}
Luego escribe la respuesta final para Israel DESPUÉS de la línea exacta:
{MARCADOR_RESPUESTA}

La respuesta final debe ser clara, en español dominicano natural, y lista para usar.
Si entregas código, empieza la respuesta final con:
"He analizado tu petición, he diseñado esta lógica, y aquí está el código optimizado para tu proyecto Salomón AI".

Tarea del usuario:
{entrada}"""


def extraer_respuesta_final(texto: str) -> str:
    """Extrae la respuesta final si el modelo usó el marcador CoT."""
    if MARCADOR_RESPUESTA in texto:
        partes = texto.split(MARCADOR_RESPUESTA, 1)
        final = partes[1].strip()
        return final if final else texto.strip()

    texto = re.sub(
        r"(?i)^\s*\[razonamiento interno\].*?(?=\n\n|\Z)",
        "",
        texto,
        flags=re.DOTALL,
    )
    texto = re.sub(
        r"(?i)^\s*\[Cognitive Core v60.*?\]\s*",
        "",
        texto,
        flags=re.DOTALL,
    )
    return texto.strip() or texto
