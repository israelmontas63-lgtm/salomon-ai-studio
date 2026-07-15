"""Configuración del módulo de cognición — reexporta settings central."""

from __future__ import annotations

from settings import (
    AGENTE_AUTONOMO_HABILITADO,
    AGENTE_BACKUP_DIR,
    AGENTE_MAX_ARCHIVOS,
    AGENTE_MAX_BYTES,
    DATA_DIR,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_VISION_MODEL,
    MEMORIA_DIR,
    RAG_TOP_K,
    ROOT_DIR,
)

CONOCIMIENTO_BASE = [
    {
        "id": "pref-diseno-negro-oro",
        "texto": (
            "Preferencia de diseño del proyecto Salomón AI Studio: "
            "estética negro (#000000) y oro champán (#C5A059), elegante, "
            "futurista, minimalista, con acentos plateados. Interfaz mobile-first."
        ),
        "tipo": "preferencia",
        "categoria": "diseno",
    },
    {
        "id": "estructura-proyecto",
        "texto": (
            "Estructura del proyecto Salomón AI: "
            "app.py (API FastAPI) → cerebro.py (núcleo) → cognicion/ (5 pilares) → "
            "persistencia/ (SQLite), clima.py, herramientas.py, "
            "studio/ (React UI), static/ (UI legacy), scripts/ (demos)."
        ),
        "tipo": "configuracion",
        "categoria": "proyecto",
    },
    {
        "id": "usuario-israel",
        "texto": (
            "Usuario principal: Israel, creador de Salomón AI. "
            "Tratarlo por su nombre con naturalidad cuando sea apropiado."
        ),
        "tipo": "preferencia",
        "categoria": "usuario",
    },
]
