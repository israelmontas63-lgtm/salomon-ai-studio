"""
Monitoreo continuo — estado, recursos y disponibilidad.
"""

from __future__ import annotations

import os
import shutil
import time
from typing import Any

from cognicion.seguridad.secretos import claves_activas


def uso_recursos() -> dict[str, Any]:
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        mem = proc.memory_info()
        return {
            "memoria_rss_mb": round(mem.rss / 1024 / 1024, 1),
            "memoria_pct": round(proc.memory_percent(), 1),
            "cpu_pct": round(proc.cpu_percent(interval=0.1), 1),
            "hilos": proc.num_threads(),
        }
    except ImportError:
        return {"nota": "psutil no instalado — métricas básicas"}
    except Exception as exc:
        return {"error": type(exc).__name__}


def espacio_disco() -> dict[str, Any]:
    try:
        from settings import DATA_DIR
        uso = shutil.disk_usage(DATA_DIR)
        return {
            "total_gb": round(uso.total / 1024**3, 2),
            "libre_gb": round(uso.free / 1024**3, 2),
            "usado_pct": round((uso.used / uso.total) * 100, 1),
        }
    except Exception:
        return {}


def verificar_apis() -> dict[str, bool]:
    claves = claves_activas()
    return {
        "llm_gemini": claves.get("gemini", False),
        "llm_openai": claves.get("openai", False),
        "llm_groq": claves.get("groq", False),
        "clima": claves.get("openweather", False),
        "api_protegida": claves.get("api_protegida", False),
    }


_inicio = time.monotonic()


def tiempo_activo_seg() -> float:
    return round(time.monotonic() - _inicio, 1)


def snapshot() -> dict[str, Any]:
    return {
        "uptime_seg": tiempo_activo_seg(),
        "recursos": uso_recursos(),
        "disco": espacio_disco(),
        "apis": verificar_apis(),
        "timestamp": time.time(),
    }
