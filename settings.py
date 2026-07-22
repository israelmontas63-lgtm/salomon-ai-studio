"""
Configuración central del proyecto Salomón AI.
Todas las rutas y variables de entorno se definen aquí.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
# Local: cargar .env. En Render NUNCA pisar secretos de plataforma.
_ON_RENDER = bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID"))
load_dotenv(ROOT_DIR / ".env", override=not _ON_RENDER)
load_dotenv(ROOT_DIR.parent / ".env", override=not _ON_RENDER)
_sbi_env = ROOT_DIR / "security" / "credentials" / "sbi.env"
if _sbi_env.exists():
    load_dotenv(_sbi_env, override=not _ON_RENDER)

# Persistencia: DATA_DIR / SESIONES_DB via env (disco Render o ruta externa)
_data_env = os.getenv("DATA_DIR", "").strip()
DATA_DIR = Path(_data_env) if _data_env else (ROOT_DIR / "data")
CREDENTIALS_DIR = ROOT_DIR / "security" / "credentials"
MEMORIA_DIR = Path(os.getenv("MEMORIA_DIR", "").strip() or (DATA_DIR / "memoria_chroma"))
_sesiones_db_env = os.getenv("SESIONES_DB", "").strip()
SESIONES_DB = Path(_sesiones_db_env) if _sesiones_db_env else (DATA_DIR / "sesiones.db")
AGENTE_BACKUP_DIR = DATA_DIR / "agente_backups"
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

# ── Google Gemini ──────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite").strip()
GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-2.0-flash").strip()
# Free Tier: historial corto (menos latencia / menos contaminación de contexto)
_GEMINI_TURNOS_DEFAULT = "8" if os.getenv("RENDER_FREE_TIER", "true").strip().lower() in (
    "1", "true", "yes", "on",
) else "16"
GEMINI_MAX_TURNOS = int(os.getenv("GEMINI_MAX_TURNOS", _GEMINI_TURNOS_DEFAULT))
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
# Hotfix voz: con ElevenLabs activo, NO diferir por defecto (Salomón debe hablar).
# Override explícito: TTS_ASYNC=true|false en .env / Render.
_eleven_presente = bool(os.getenv("ELEVENLABS_API_KEY", "").strip())
_tts_async_default = (
    "false"
    if _eleven_presente
    else (
        "true"
        if os.getenv("RENDER_FREE_TIER", "true").strip().lower() in ("1", "true", "yes", "on")
        else "false"
    )
)
TTS_ASYNC = os.getenv("TTS_ASYNC", _tts_async_default).strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
# Tope duro de espera TTS en rutas síncronas (segundos)
TTS_SYNC_TIMEOUT_S = float(os.getenv("TTS_SYNC_TIMEOUT_S", "12"))

# ── OpenAI (proveedor alternativo) ───────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip()

# ── DeepSeek (razonamiento / lógica / depuración — OpenAI-compatible) ─────
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
DEEPSEEK_BASE_URL = (
    os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
    or "https://api.deepseek.com"
)

# ── OpenRouter / Cerebras / Mistral (LLM failover OpenAI-compatible) ─────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = (
    os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat").strip()
    or "deepseek/deepseek-chat"
)
OPENROUTER_BASE_URL = (
    os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
    or "https://openrouter.ai/api/v1"
)
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "").strip()
CEREBRAS_MODEL = (
    os.getenv("CEREBRAS_MODEL", "llama-3.3-70b").strip() or "llama-3.3-70b"
)
CEREBRAS_BASE_URL = (
    os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1").strip()
    or "https://api.cerebras.ai/v1"
)
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "").strip()
MISTRAL_MODEL = (
    os.getenv("MISTRAL_MODEL", "mistral-small-latest").strip()
    or "mistral-small-latest"
)
MISTRAL_BASE_URL = (
    os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1").strip()
    or "https://api.mistral.ai/v1"
)

# ── Groq (OpenAI-compatible, gratis sin tarjeta) ───────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()

# ── Cohere (RAG / embeddings) ─────────────────────────────────────────────
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "").strip()
COHERE_EMBED_MODEL = os.getenv("COHERE_EMBED_MODEL", "embed-multilingual-v3.0").strip()

# ── Deepgram (STT — voz a texto) ──────────────────────────────────────────
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "").strip()
DEEPGRAM_MODEL = os.getenv("DEEPGRAM_MODEL", "nova-2").strip() or "nova-2"
DEEPGRAM_LANGUAGE = os.getenv("DEEPGRAM_LANGUAGE", "es").strip() or "es"

# ── ElevenLabs (TTS — texto a voz) ────────────────────────────────────────
# Adam (case-sensitive). 'n' minúscula en NInz; F mayúscula en GcF.
# Exacto: pNInz6obpgDQGcFmaJgB  — NO pNINz6... / NO ...Gcf...
ELEVENLABS_VOICE_ADAM = "pNInz6obpgDQGcFmaJgB"
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
_raw_voice = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
# Normaliza typos de casing; si falta Voice ID → Adam por defecto (producción)
if not _raw_voice:
    ELEVENLABS_VOICE_ID = ELEVENLABS_VOICE_ADAM
elif _raw_voice.lower() == ELEVENLABS_VOICE_ADAM.lower():
    ELEVENLABS_VOICE_ID = ELEVENLABS_VOICE_ADAM
else:
    ELEVENLABS_VOICE_ID = _raw_voice
ELEVENLABS_MODEL_ID = os.getenv(
    "ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"
).strip() or "eleven_multilingual_v2"

# ── Fal.ai + Replicate (imagen / video) ───────────────────────────────────
FAL_KEY = os.getenv("FAL_KEY", "").strip()
# Alias: algunos paneles usan REPLICATE_API_KEY; el código canónico es REPLICATE_API_TOKEN.
REPLICATE_API_TOKEN = (
    os.getenv("REPLICATE_API_TOKEN", "").strip()
    or os.getenv("REPLICATE_API_KEY", "").strip()
)

# Validación estricta de claves (false en Free Tier / local; true en prod)
PROVIDERS_STRICT = os.getenv("PROVIDERS_STRICT", "false").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)

# Modo ejecución neuronal (producción Render) — sin simulaciones
MODO_EJECUCION = os.getenv("MODO_EJECUCION", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)

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

# ── SBI-PRO — Speaker Biometric Identity (Israel Monta) ─────────────────────
# off/soft/strict vía módulo; vault en security/credentials/ (gitignored).
SBI_ENABLED = os.getenv("SBI_ENABLED", "false").strip().lower() in (
    "1", "true", "yes", "on",
)
SBI_MODE = (os.getenv("SBI_MODE", "soft") or "soft").strip().lower()
SBI_THRESHOLD = float(os.getenv("SBI_THRESHOLD", "0.82") or "0.82")
SBI_RECOVERY_KEY = os.getenv("SBI_RECOVERY_KEY", "").strip()
SBI_ENROLL_TOKEN = os.getenv("SBI_ENROLL_TOKEN", "").strip()
SBI_TEMPLATE_SECRET = os.getenv("SBI_TEMPLATE_SECRET", "").strip()
SBI_OWNER_NAME = os.getenv("SBI_OWNER_NAME", "Israel Monta").strip() or "Israel Monta"
SBI_CHALLENGE_PHRASE = os.getenv(
    "SBI_CHALLENGE_PHRASE", "Salomon autentica a Israel"
).strip()
SBI_TEMPLATE_PATH = os.getenv(
    "SBI_TEMPLATE_PATH", "security/credentials/sbi_israel.json"
).strip()

# ── Cerebro Ejecutivo (Israel Montas — propiedad privada) ──────────────────
EJECUTIVO_ENABLED = os.getenv("EJECUTIVO_ENABLED", "true").strip().lower() in (
    "1", "true", "yes", "on",
)
NUMVERIFY_API_KEY = os.getenv("NUMVERIFY_API_KEY", "").strip()

# ── Proveedor LLM ──────────────────────────────────────────────────────────
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "gemini").strip().lower()
# Temperatura baja = menos alucinación / basura creativa (rango óptimo 0.3–0.5)
try:
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.4") or "0.4")
except Exception:
    LLM_TEMPERATURE = 0.4
LLM_TEMPERATURE = max(0.0, min(1.0, LLM_TEMPERATURE))
try:
    LLM_TOP_P = float(os.getenv("LLM_TOP_P", "0.9") or "0.9")
except Exception:
    LLM_TOP_P = 0.9
LLM_TOP_P = max(0.1, min(1.0, LLM_TOP_P))

# ── Fallback LLM ───────────────────────────────────────────────────────────
LLM_FALLBACK = os.getenv("LLM_FALLBACK", "true").strip().lower() in (
    "1", "true", "yes", "on",
)
# En ejecución: no degradar a local si hay claves cloud (salvo override explícito).
# Free Tier Render: local ON por defecto para no colgar el chat si Gemini falla.
_llm_local_raw = os.getenv("LLM_LOCAL_FALLBACK")
_render_free = os.getenv("RENDER_FREE_TIER", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
if _llm_local_raw is None:
    LLM_LOCAL_FALLBACK = (not MODO_EJECUCION) or _render_free
else:
    LLM_LOCAL_FALLBACK = _llm_local_raw.strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

# ── Búsqueda web (Tavily + Exa → Wikipedia/DDG) ───────────────────────────
# Cortex absoluto: por defecto OFF. La web solo entra con frase canónica
# («Busca en la web sobre…») vía autoriza_web — nunca por heurística factual.
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
EXA_API_KEY = os.getenv("EXA_API_KEY", "").strip()
# advanced = extracción profunda (vista de águila); basic = más rápido
TAVILY_SEARCH_DEPTH = (
    os.getenv("TAVILY_SEARCH_DEPTH", "advanced").strip().lower() or "advanced"
)
if TAVILY_SEARCH_DEPTH not in ("basic", "advanced"):
    TAVILY_SEARCH_DEPTH = "advanced"
BUSQUEDA_WEB_AUTO = os.getenv("BUSQUEDA_WEB_AUTO", "false").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)

# ── Núcleo perceptivo (config/voice_parameters + vision_integration) ────────
try:
    from config.voice_parameters import MIC_ALWAYS_READY, STT_LANG, voice_parameters
    from config.vision_integration import VISION_ENABLED, VISION_IN_INPUT_FLOW, vision_parameters

    VOICE_PARAMS = voice_parameters()
    VISION_PARAMS = vision_parameters()
except Exception:
    MIC_ALWAYS_READY = True
    STT_LANG = "es-ES"
    VISION_ENABLED = True
    VISION_IN_INPUT_FLOW = True
    VOICE_PARAMS = {"sincronizado": True}
    VISION_PARAMS = {"activa": True}

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
MAX_SESIONES_RAM = int(os.getenv("MAX_SESIONES_RAM", "4" if RENDER_FREE_TIER else "8"))
MEDIA_HTTP_TIMEOUT = float(os.getenv("MEDIA_HTTP_TIMEOUT", "45"))
MEDIA_HTTP_TIMEOUT_POLL = float(os.getenv("MEDIA_HTTP_TIMEOUT_POLL", "30"))
# Hotfix imagen: con Fal/Replicate/OpenAI, generar en sync (UI no hace poll de jobs).
_media_keys = bool(
    (os.getenv("FAL_KEY") or "").strip()
    or (os.getenv("REPLICATE_API_TOKEN") or "").strip()
    or (os.getenv("REPLICATE_API_KEY") or "").strip()
    or (os.getenv("OPENAI_API_KEY") or "").strip()
)
MEDIA_ASYNC_DEFAULT = os.getenv(
    "MEDIA_ASYNC_DEFAULT",
    "false" if _media_keys else "true",
).strip().lower() in ("1", "true", "yes", "on")
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
