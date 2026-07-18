"""
Configuración central del proyecto Salomón AI.
Todas las rutas y variables de entorno se definen aquí.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

DATA_DIR = ROOT_DIR / "data"
MEMORIA_DIR = DATA_DIR / "memoria_chroma"
SESIONES_DB = DATA_DIR / "sesiones.db"
AGENTE_BACKUP_DIR = DATA_DIR / "agente_backups"

# ── Google Gemini ──────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-2.0-flash").strip()
GEMINI_MAX_TURNOS = int(os.getenv("GEMINI_MAX_TURNOS", "20"))
GEMINI_MODELOS_RESPALDO = [
    m.strip()
    for m in os.getenv(
        "GEMINI_MODELOS_RESPALDO",
        "gemini-2.0-flash-lite,gemini-2.0-flash",
    ).split(",")
    if m.strip()
]

# ── OpenWeatherMap ─────────────────────────────────────────────────────────
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "").strip()

# ── TTS — Cartesia Sonic-3.5 (motor de alta gama) ──────────────────────────
CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY", "").strip()
CARTESIA_VOICE_ID = os.getenv("CARTESIA_VOICE_ID", "").strip()
CARTESIA_MODEL_ID = os.getenv("CARTESIA_MODEL_ID", "sonic-3.5").strip() or "sonic-3.5"
CARTESIA_LANGUAGE = os.getenv("CARTESIA_LANGUAGE", "es").strip() or "es"
CARTESIA_SAMPLE_RATE = int(os.getenv("CARTESIA_SAMPLE_RATE", "44100") or "44100")

# Compatibilidad de flags de orquestación (sin motores legacy)
TTS_RATE = int(os.getenv("TTS_RATE", "185"))
TTS_VOLUME = float(os.getenv("TTS_VOLUME", "0.95"))
TTS_ASYNC = os.getenv("TTS_ASYNC", "false").strip().lower() in ("1", "true", "yes", "on")

# ── OpenAI (proveedor alternativo) ───────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip()

# ── Groq (OpenAI-compatible, gratis sin tarjeta) ───────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()

# ── Cognición ──────────────────────────────────────────────────────────────
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
AGENTE_AUTONOMO_HABILITADO = os.getenv("AGENTE_AUTONOMO", "false").strip().lower() in (
    "1", "true", "yes", "on",
)
AGENTE_MAX_ARCHIVOS = int(os.getenv("AGENTE_MAX_ARCHIVOS", "4"))
AGENTE_MAX_BYTES = int(os.getenv("AGENTE_MAX_BYTES", "80000"))

# ── Seguridad API ───────────────────────────────────────────────────────────
SALOMON_API_KEY = os.getenv("SALOMON_API_KEY", "").strip()
SALOMON_ADMIN_KEY = os.getenv("SALOMON_ADMIN_KEY", "").strip()
SEGURIDAD_HABILITADA = os.getenv("SEGURIDAD_HABILITADA", "true").strip().lower() in (
    "1", "true", "yes", "on",
)

# ── Proveedor LLM ──────────────────────────────────────────────────────────
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "gemini").strip().lower()

# ── Fallback LLM ───────────────────────────────────────────────────────────
LLM_FALLBACK = os.getenv("LLM_FALLBACK", "true").strip().lower() in (
    "1", "true", "yes", "on",
)
LLM_LOCAL_FALLBACK = os.getenv("LLM_LOCAL_FALLBACK", "true").strip().lower() in (
    "1", "true", "yes", "on",
)

# ── Búsqueda web (Tavily preferido; DDG/noticias como respaldo) ────────────
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
BUSQUEDA_WEB_AUTO = os.getenv("BUSQUEDA_WEB_AUTO", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)

# ── Colsub Media — Multi-Model Routing (Pro/Ultra) ─────────────────────────
MEDIA_CALIDAD_FORZADA = os.getenv("MEDIA_CALIDAD_FORZADA", "pro_ultra").strip()
MEDIA_FORZAR_PRO = os.getenv("MEDIA_FORZAR_PRO", "true").strip().lower() in (
    "1", "true", "yes", "on",
)
MEDIA_PREFER_IMAGEN = os.getenv("MEDIA_PREFER_IMAGEN", "flux").strip().lower()
MEDIA_PREFER_VIDEO = os.getenv("MEDIA_PREFER_VIDEO", "runway").strip().lower()
MEDIA_PROMPT_ENHANCER = os.getenv("MEDIA_PROMPT_ENHANCER", "true").strip().lower() in (
    "1", "true", "yes", "on",
)
FLUX_API_KEY = os.getenv("FLUX_API_KEY", "").strip()
FLUX_API_URL = os.getenv("FLUX_API_URL", "").strip()
FLUX_MODEL = os.getenv("FLUX_MODEL", "flux-1-pro").strip()
MIDJOURNEY_API_KEY = os.getenv("MIDJOURNEY_API_KEY", "").strip()
MIDJOURNEY_API_URL = os.getenv("MIDJOURNEY_API_URL", "").strip()
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY", "").strip()
RUNWAY_API_URL = os.getenv("RUNWAY_API_URL", "").strip()
RUNWAY_MODEL = os.getenv("RUNWAY_MODEL", "gen3a_alpha").strip()
RUNWAY_MODEL_PRO = os.getenv("RUNWAY_MODEL_PRO", "gen3a_alpha").strip()
KLING_API_KEY = os.getenv("KLING_API_KEY", "").strip()
KLING_API_URL = os.getenv("KLING_API_URL", "").strip()
KLING_MODEL = os.getenv("KLING_MODEL", "kling-v1-pro").strip()
KREA_API_KEY = os.getenv("KREA_API_KEY", "").strip()
KREA_API_URL = os.getenv("KREA_API_URL", "").strip()

# ── Colsub — techos Render Free Tier (Ultra-Light) ─────────────────────────
COLSUB_MAX_AGENTES = int(os.getenv("COLSUB_MAX_AGENTES", "2"))
COLSUB_MAX_WORKERS = int(os.getenv("COLSUB_MAX_WORKERS", "1"))
COLSUB_CPU_CRITICO = float(os.getenv("COLSUB_CPU_CRITICO", "75"))
COLSUB_RAM_CRITICO = float(os.getenv("COLSUB_RAM_CRITICO", "68"))

# ── Máxima Eficiencia v95 ──────────────────────────────────────────────────
RENDER_FREE_TIER = os.getenv("RENDER_FREE_TIER", "true").strip().lower() in (
    "1", "true", "yes", "on",
)
MAX_SESIONES_RAM = int(os.getenv("MAX_SESIONES_RAM", "2" if RENDER_FREE_TIER else "8"))
MEDIA_HTTP_TIMEOUT = float(os.getenv("MEDIA_HTTP_TIMEOUT", "45"))
MEDIA_HTTP_TIMEOUT_POLL = float(os.getenv("MEDIA_HTTP_TIMEOUT_POLL", "30"))
MEDIA_ASYNC_DEFAULT = os.getenv("MEDIA_ASYNC_DEFAULT", "true").strip().lower() in (
    "1", "true", "yes", "on",
)
BOOT_LIGHT = os.getenv("BOOT_LIGHT", "true" if RENDER_FREE_TIER else "false").strip().lower() in (
    "1", "true", "yes", "on",
)

# ── Caché conectores ───────────────────────────────────────────────────────
CACHE_TTL_SEGUNDOS = int(os.getenv("CACHE_TTL_SEGUNDOS", "900"))

# ── Logging ────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper()

# ── Aprendizaje async ──────────────────────────────────────────────────────
APRENDIZAJE_ASYNC = os.getenv("APRENDIZAJE_ASYNC", "true").strip().lower() in (
    "1", "true", "yes", "on",
)

# ── Function-calling (Fase 2 OS) ───────────────────────────────────────────
FUNCTION_CALLING_HABILITADO = os.getenv("FUNCTION_CALLING_HABILITADO", "true").strip().lower() in (
    "1", "true", "yes", "on",
)
FUNCTION_CALLING_SIEMPRE = os.getenv("FUNCTION_CALLING_SIEMPRE", "false").strip().lower() in (
    "1", "true", "yes", "on",
)
FUNCTION_CALLING_MAX_ITER = int(os.getenv("FUNCTION_CALLING_MAX_ITER", "3"))

# ── VDCP — Visión Dinámica de Campo Profundo ───────────────────────────────
VDCP_MAX_FOVEAS = int(os.getenv("VDCP_MAX_FOVEAS", "12"))
VDCP_OCR_ENGINE = os.getenv("VDCP_OCR_ENGINE", "").strip().lower()  # paddle|tesseract|easyocr|gemini
VDCP_YOLO_WEIGHTS = os.getenv(
    "VDCP_YOLO_WEIGHTS",
    str(DATA_DIR / "modelos" / "vdcp" / "yolov8n.pt"),
).strip()
VDCP_YOLO_CONF = float(os.getenv("VDCP_YOLO_CONF", "0.25"))
VDCP_USAR_GEMINI = os.getenv("VDCP_USAR_GEMINI", "false").strip().lower() in (
    "1", "true", "yes", "on",
)
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "").strip()

# ── Túnel móvil (localtunnel) + puerto canónico v104 ───────────────────────
def _puerto_env_default() -> int:
    """Puerto dinámico HA: PORT → COLSUB_PORT → libre; tipografía 800→8000."""
    import socket

    raw = os.getenv("PORT") or os.getenv("COLSUB_PORT")
    if raw is not None and str(raw).strip() != "":
        try:
            p = int(str(raw).strip())
        except Exception:
            p = 8000
        if p == 800:
            p = 8000
        if 1 <= p <= 65535:
            return p
    for candidate in (8000, 8001, 8080, 8888, 10000):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("0.0.0.0", candidate))
                return candidate
        except OSError:
            continue
    return 8000


COLSUB_PORT = _puerto_env_default()
COLSUB_HOST = os.getenv("COLSUB_HOST", "0.0.0.0").strip() or "0.0.0.0"
# Memoria: solo filesystem local (nunca HttpClient puerto 800/8000)
MEMORIA_SOLO_LOCAL = os.getenv("MEMORIA_SOLO_LOCAL", "true").strip().lower() in (
    "1", "true", "yes", "on",
)
TUNEL_HABILITADO = os.getenv("TUNEL_HABILITADO", "true").strip().lower() in (
    "1", "true", "yes", "on",
)
TUNEL_AUTO = os.getenv("TUNEL_AUTO", "true").strip().lower() in (
    "1", "true", "yes", "on",
)
TUNEL_SUBDOMAIN = os.getenv("TUNEL_SUBDOMAIN", "salomon-ai").strip()
