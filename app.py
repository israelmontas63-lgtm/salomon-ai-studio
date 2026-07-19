"""
Servidor web de Salomón AI — FastAPI.

Flujo:
  studio/ (UI) → app.py (API) → cerebro.py (núcleo)
                              → persistencia/ (SQLite)
                              → cognicion/ (5 pilares)
                              → clima.py | herramientas.py
"""

from __future__ import annotations

import hmac
import os
import uuid

from settings import ROOT_DIR
from dotenv import load_dotenv

# Root .env + vault SBI (firma/plantilla/tokens en security/credentials/)
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / "security" / "credentials" / "sbi.env", override=True)

from cognicion.registro import configurar_registro, evento, obtener_logger

configurar_registro()

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from cerebro import SalomonAI
import herramientas
from persistencia import (
    asegurar_sesion,
    cargar_mensajes,
    guardar_mensaje,
    inicializar as init_persistencia,
    limpiar_sesion,
    sesion_existe,
)

from settings import ROOT_DIR as BASE_DIR, AGENTE_AUTONOMO_HABILITADO, APRENDIZAJE_ASYNC, LLM_FALLBACK, LOG_LEVEL, MODEL_PROVIDER, SALOMON_API_KEY, TTS_ASYNC
STUDIO_DIR = BASE_DIR / "studio" / "dist"
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

_UI_NO_CACHE = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}

app = FastAPI(title="Salomón AI", version="1.0.0")
_log = obtener_logger("api")
RUTAS_API_PUBLICAS = frozenset(
    {
        "/api/salud",
        "/api/salud/detalle",
        "/api/version",
        "/api/bca/estado",
        "/api/tunel/estado",
        "/api/cognicion/vdcp/estado",
        "/api/cognicion/cognitive-core",
        "/api/cognicion/multimodal",
        "/api/cognicion/vision",
        "/api/agentes/estado",
        "/api/esencia",
        "/api/sbi/estado",
        "/api/sbi/challenge",
        "/api/ejecutivo/estado",
        "/api/cognitivo/estado",
        "/api/eficiencia",
        "/api/identidad",
        "/api/inmune",
        "/api/conectividad",
        "/api/auditoria/cruzada",
        "/api/web/arquitecto",
        "/api/pwa/estado",
        "/api/auditoria/preflight",
        "/api/sellado",
        "/api/sce",
        "/api/evolucion/30x",
        "/api/comic/estado",
        "/api/media/estado",
        "/api/autonoma/fase1/estado",
        "/api/nucleo/perceptivo",
        "/api/mente/conexion",
        "/api/core/kernel",
        "/api/core/kernel/init",
        "/api/chat",
        "/api/ai-process",
        "/api/chat/nuevo",
        "/api/proveedores",
        "/api/stt",
        "/api/tts",
        "/api/carcasa-check",
    }
)


@app.on_event("startup")
def _iniciar_nucleo_os() -> None:
    """Boot Ultra-Light (Render Free): deferir orquesta/snapshots pesados."""
    try:
        from settings import BOOT_LIGHT, RENDER_FREE_TIER

        light = BOOT_LIGHT or RENDER_FREE_TIER
    except Exception:
        light = True

    # SystemGuard — verify only en Free Tier (sin heal/copia agresiva al boot)
    try:
        import SystemGuard as _sg

        _guard = _sg.boot_guard(auto_heal=not light)
        evento(
            _log,
            "system_guard_boot",
            ok=_guard.get("integrity", {}).get("ok"),
            viviente=True,
            protocol=_guard.get("protocol"),
            boot_light=light,
        )
    except Exception as exc:
        _log.warning("system_guard_boot_omitido: %s", exc)

    try:
        from cognicion.nucleo import obtener_nucleo
        from cognicion.capas.loader import inicializar_capas

        obtener_nucleo()
        # Motor de seguridad: lazy en primer request API (ahorra RAM al wake)
        if not light:
            from cognicion.seguridad import obtener_motor
            from cognicion.seguridad.recuperacion import crear_snapshot

            obtener_motor()
            try:
                crear_snapshot(motivo="inicio_sistema")
            except Exception as exc:
                _log.warning("snapshot_inicio_omitido: %s", exc)

        inicializar_capas(app)

        # Orquestador de carga: NO arrancar hilo en Free Tier hasta primer uso
        if not light:
            from cognicion.orquesta.colas import obtener_orquestador_carga

            orq = obtener_orquestador_carga()
            evento(
                _log,
                "colsub_orquestador_activo",
                activo=orq.activo,
                arquitectura="colas",
            )
        else:
            evento(_log, "boot_light_activo", free_tier=True, orquesta="diferida")

        # Provider Pattern — carga claves Render (no tumba Free Tier si faltan opcionales)
        try:
            from cognicion.servicios.registry import boot_proveedores
            from config.providers import ProviderConfigError
            from settings import PROVIDERS_STRICT

            boot_proveedores(strict=PROVIDERS_STRICT)
        except ProviderConfigError:
            raise
        except Exception as exc:
            _log.warning("boot_proveedores_omitido: %s", exc)

        try:
            from cognicion.eficiencia import hibernar_agentes

            hibernar_agentes()
        except Exception:
            pass
        evento(_log, "nucleo_iniciado", boot_light=light)
    except Exception as exc:
        _log.exception("startup_parcial_fallo: %s", exc)
        evento(_log, "nucleo_inicio_degradado", error=str(exc))

app.add_middleware(
    CORSMiddleware,
    # PWA / Render / local — mismo origen no necesita CORS, pero el móvil
    # a veces abre variantes de host; permitimos amplio para no bloquear.
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_sesiones: dict[str, SalomonAI] = {}

try:
    init_persistencia()
    _log.info("Persistencia inicializada")
except Exception as exc:
    # Fail-soft: el proceso no muere en Render si SQLite/volumen falla al import
    _log.exception("persistencia_inicio_degradado: %s", exc)


@app.middleware("http")
async def bloquear_rutas_sensibles_middleware(request: Request, call_next):
    from cognicion.seguridad import ruta_sensible

    if ruta_sensible(request.url.path):
        return JSONResponse(status_code=404, content={"detail": "No encontrado"})
    response = await call_next(request)
    # v105: permitir cam/mic en PWA (same-origin)
    try:
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(self), autoplay=(self)"
    except Exception:
        pass
    return response


@app.middleware("http")
async def motor_ciberseguridad_middleware(request: Request, call_next):
    """Defensa en profundidad — intrusión, identidad, auditoría, anomalías."""
    import time

    from settings import SEGURIDAD_HABILITADA
    from cognicion.capas.contexto import establecer_contexto, limpiar_contexto

    path = request.url.path
    inicio = time.perf_counter()
    api_key_hdr = request.headers.get("x-api-key")
    establecer_contexto(api_key=api_key_hdr)

    try:
        if SEGURIDAD_HABILITADA and path.startswith("/api/"):
            from cognicion.seguridad import obtener_motor
            from cognicion.seguridad.secretos import obtener_secreto
            from cognicion.seguridad.tipos import AccionSeguridad

            motor = obtener_motor()
            ip = request.client.host if request.client else "desconocida"
            api_key = api_key_hdr
            user_agent = request.headers.get("user-agent", "")
            query = str(request.url.query or "")

            user_key = obtener_secreto("SALOMON_API_KEY") or SALOMON_API_KEY
            admin_key = obtener_secreto("SALOMON_ADMIN_KEY") or ""

            def _clave_valida(enviada: str | None, esperada: str) -> bool:
                if not enviada or not esperada:
                    return False
                return hmac.compare_digest(enviada, esperada)

            if path not in RUTAS_API_PUBLICAS and user_key:
                ok_user = _clave_valida(api_key, user_key)
                ok_admin = _clave_valida(api_key, admin_key) if admin_key else False
                if not (ok_user or ok_admin):
                    ev = motor.evaluar_auth_fallida(ip, path)
                    return JSONResponse(
                        status_code=401,
                        content={
                            "detail": "API key requerida o inválida",
                            "seguridad": ev.tipo.value,
                        },
                    )

            # Rutas públicas (salud/boot PWA): no aplicar bloqueos de intrusión
            if path not in RUTAS_API_PUBLICAS:
                permitir, amenaza, motivo = motor.evaluar_peticion_entrante(
                    path,
                    request.method,
                    ip,
                    api_key=api_key,
                    query=query,
                    user_agent=user_agent,
                )
                if not permitir:
                    status = 403
                    if motivo == "requiere_autenticacion":
                        status = 401
                    elif amenaza and amenaza.accion == AccionSeguridad.BLOQUEAR:
                        status = 403
                    return JSONResponse(
                        status_code=status,
                        content={
                            "detail": motivo,
                            "seguridad": amenaza.tipo.value if amenaza else None,
                        },
                    )

        response = await call_next(request)
        duracion_ms = round((time.perf_counter() - inicio) * 1000, 1)

        if path.startswith("/api/"):
            evento(
                _log,
                "peticion",
                metodo=request.method,
                ruta=path,
                status=response.status_code,
                ms=duracion_ms,
            )
            if SEGURIDAD_HABILITADA:
                from cognicion.seguridad import obtener_motor

                obtener_motor().registrar_peticion_completada(
                    path=path,
                    metodo=request.method,
                    status=response.status_code,
                    duracion_ms=duracion_ms,
                    ip=request.client.host if request.client else "",
                    user_agent=request.headers.get("user-agent", ""),
                    api_key=api_key_hdr,
                )

        return response
    finally:
        limpiar_contexto()


def _requiere_admin(request: Request) -> None:
    from cognicion.seguridad.identidad import resolver_actor
    from cognicion.seguridad.secretos import obtener_secreto
    from cognicion.seguridad.tipos import RolAcceso

    ip = request.client.host if request.client else ""
    actor = resolver_actor(request.headers.get("x-api-key"), ip=ip)
    if actor.rol == RolAcceso.ADMIN:
        return
    if obtener_secreto("SALOMON_ADMIN_KEY"):
        raise HTTPException(status_code=403, detail="Requiere rol administrador")
    if actor.rol == RolAcceso.ANON:
        raise HTTPException(status_code=401, detail="Autenticación requerida")


def _restaurar_sesion(session_id: str) -> SalomonAI:
    mensajes = cargar_mensajes(session_id)
    salomon = SalomonAI(session_id=session_id)
    if mensajes:
        salomon.cargar_historial(mensajes)
    return salomon


def _persistir_turno(session_id: str, usuario: str, asistente: str) -> None:
    guardar_mensaje(session_id, "usuario", usuario)
    guardar_mensaje(session_id, "asistente", asistente)


def _obtener_o_crear_sesion(session_id: str | None) -> tuple[str, SalomonAI]:
    try:
        from settings import MAX_SESIONES_RAM
        from cognicion.eficiencia import podar_sesiones

        podar_sesiones(_sesiones, max_sesiones=MAX_SESIONES_RAM)
    except Exception:
        # Fallback Free Tier: máximo 2 sesiones en RAM
        while len(_sesiones) > 2:
            _sesiones.pop(next(iter(_sesiones)), None)

    if session_id and session_id in _sesiones:
        return session_id, _sesiones[session_id]

    if session_id and sesion_existe(session_id):
        salomon = _restaurar_sesion(session_id)
        _sesiones[session_id] = salomon
        return session_id, salomon

    nuevo_id = session_id or str(uuid.uuid4())
    _sesiones[nuevo_id] = SalomonAI(session_id=nuevo_id)
    asegurar_sesion(nuevo_id)
    return nuevo_id, _sesiones[nuevo_id]


class ChatRequest(BaseModel):
    mensaje: str = Field(..., min_length=0, max_length=4000)
    session_id: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    imagen_base64: str | None = Field(default=None, max_length=8_000_000)
    imagen_mime: str = "image/png"
    error_consola: str | None = Field(default=None, max_length=8000)
    autonomo: bool = False
    # Fase 1 — pipeline autónomo (visión + búsqueda/síntesis + estados)
    fase1: bool = False


class ChatResponse(BaseModel):
    texto: str
    exito: bool
    session_id: str
    metadata: dict
    audio_base64: str | None = None
    audio_mime: str = "audio/mpeg"
    tts_disponible: bool = False


class SessionResponse(BaseModel):
    session_id: str
    mensaje: str
    audio_base64: str | None = None
    audio_mime: str = "audio/mpeg"
    tts_disponible: bool = False


class HistorialItem(BaseModel):
    rol: str
    contenido: str


class HistorialResponse(BaseModel):
    session_id: str
    mensajes: list[HistorialItem]


class TextoRequest(BaseModel):
    texto: str = Field(..., max_length=8000)


class TraducirRequest(BaseModel):
    texto: str = Field(..., max_length=8000)
    origen: str = "es"
    destino: str = "en"


class CliRequest(BaseModel):
    comando: str = Field(..., max_length=500)


class BackupExportRequest(BaseModel):
    historial: list[dict] = Field(default_factory=list)
    config: dict = Field(default_factory=dict)


class BackupImportRequest(BaseModel):
    contenido: str


class VisionRequest(BaseModel):
    imagen_base64: str = Field(..., max_length=8_000_000)
    imagen_mime: str = "image/png"
    contexto: str = Field(default="", max_length=4000)
    session_id: str | None = None


class VdcpRequest(BaseModel):
    imagen_base64: str | None = Field(default=None, max_length=8_000_000)
    ruta: str | None = None
    max_foveas: int | None = Field(default=None, ge=1, le=40)
    session_id: str | None = None


class ErrorConsolaRequest(BaseModel):
    error: str = Field(..., min_length=1, max_length=8000)
    session_id: str | None = None
    mensaje: str = Field(default="Ayúdame a corregir este error.", max_length=4000)
    autonomo: bool = True


class AgenteRequest(BaseModel):
    tarea: str = Field(..., min_length=1, max_length=4000)
    error: str | None = Field(default=None, max_length=8000)
    session_id: str | None = None


def _build_id() -> str:
    """Identificador de despliegue (Render git commit o override local)."""
    raw = (
        os.getenv("RENDER_GIT_COMMIT")
        or os.getenv("SALOMON_BUILD_ID")
        or os.getenv("GIT_COMMIT")
        or ""
    ).strip()
    if not raw:
        # Fallback estable por mtime de overlays (dev local)
        try:
            marker = STUDIO_DIR / "salomon-update.js"
            if marker.is_file():
                raw = f"local-{int(marker.stat().st_mtime)}"
        except Exception:
            raw = "dev"
    return raw or "dev"


# ── Salud / versión (CI/CD) ────────────────────────────────────────────────
def _leer_version_json() -> dict:
    """Lee version.json de la raíz del repo (despliegue continuo)."""
    import json
    import time as _time

    ruta = BASE_DIR / "version.json"
    data: dict = {
        "version": "1.0.0",
        "timestamp": 0,
        "channel": "main",
    }
    try:
        if ruta.is_file():
            texto = ruta.read_text(encoding="utf-8-sig")
            raw = json.loads(texto)
            if isinstance(raw, dict):
                data.update(raw)
    except Exception:
        pass
    build = _build_id()
    data["build"] = build[:12] if len(build) > 12 else build
    data["build_full"] = build
    data["served_at"] = int(_time.time())
    return data


@app.get("/version.json")
def version_json_file():
    """Manifiesto de versión para actualización proactiva del cliente."""
    return JSONResponse(
        content=_leer_version_json(),
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


@app.get("/api/version")
def api_version() -> dict:
    """Build actual en Render — el cliente lo usa para auto-actualizar la PWA."""
    from settings import CARTESIA_API_KEY, CARTESIA_MODEL_ID, CARTESIA_VOICE_ID

    data = _leer_version_json()
    key_ok = bool((CARTESIA_API_KEY or "").strip())
    voice_ok = bool((CARTESIA_VOICE_ID or "").strip())
    return {
        "estado": "ok",
        "servicio": "Salomón AI",
        "version": data.get("version") or "1.0.0",
        "timestamp": data.get("timestamp") or 0,
        "timestamp_iso": data.get("timestamp_iso"),
        "build": data.get("build"),
        "build_full": data.get("build_full"),
        "channel": data.get("channel") or "main",
        "tts_env": "CARTESIA_API_KEY",
        "tts_modelo": CARTESIA_MODEL_ID or "sonic-3.5",
        "tts_formato": "audio/wav",
        "tts_key": key_ok,
        "tts_voice": voice_ok,
        "tts_configurado": bool(key_ok and voice_ok),
        "live": True,
    }


def _salud_payload() -> dict:
    """Estado técnico de salud (JSON / Render / SystemGuard)."""
    ver = _leer_version_json()
    guard: dict = {"active": False}
    try:
        import SystemGuard as _sg

        rep = _sg.verificar_contra_ledger(raise_on_drift=False)
        guard = {
            "active": True,
            "viviente": True,
            "integrity_ok": rep.get("ok"),
            "checked": rep.get("checked"),
            "protocol": "SALOMON_VIVIENTE",
        }
    except Exception:
        guard = {"active": False}
    multimodal: dict = {"active": False}
    try:
        from cognicion.multimodal import estado_multimodal

        multimodal = {
            "active": True,
            "version": "70.0.0",
            "budget_ms": estado_multimodal().get("modules", {}).get("system_guard_budget_ms"),
        }
    except Exception:
        multimodal = {"active": False}
    multiagente: dict = {"active": False}
    try:
        from cognicion.agente.coordinador import estado_multiagente

        ma = estado_multiagente()
        multiagente = {
            "active": True,
            "version": ma.get("version"),
            "protocol": ma.get("protocol"),
            "render_caps": ma.get("render"),
        }
    except Exception:
        multiagente = {"active": False}
    eficiencia: dict = {"active": False}
    try:
        from cognicion.eficiencia import estado_eficiencia

        eficiencia = estado_eficiencia()
    except Exception:
        eficiencia = {"active": False}
    identidad: dict = {"active": False}
    try:
        from cognicion.identidad import estado_identidad
        from cognicion.web import estado_web_architect

        identidad = {
            **estado_identidad(),
            "web_architect_active": estado_web_architect().get("active"),
        }
    except Exception:
        identidad = {"active": False}
    pwa = {
        "active": True,
        "version": "106.0.0",
        "service_worker": "/service-worker.js",
        "display": "standalone",
        "theme_color": "#000000",
        "installable": True,
        "cache": "salomon-pwa-v105",
        "seal": True,
        "permissions": ["camera", "microphone"],
        "espera_autorizacion_fisica": True,
    }
    sce: dict = {"active": False}
    try:
        from cognicion.evolucion import estado_sce

        sce = estado_sce()
    except Exception:
        sce = {"active": False}
    evolucion_30x: dict = {"active": False}
    try:
        from cognicion.evolucion.habilidades_30x import estado_30x

        evolucion_30x = estado_30x()
    except Exception:
        evolucion_30x = {"active": False}
    comic: dict = {"active": False}
    try:
        from cognicion.comic import estado_comic_engine

        comic = estado_comic_engine()
    except Exception:
        comic = {"active": False}
    return {
        "estado": "ok",
        "servicio": "Salomón AI",
        "version": ver.get("version") or "1.0.0",
        "build": ver.get("build"),
        "timestamp": ver.get("timestamp") or 0,
        "live": True,
        "neural_integrity_lock": True,
        "system_guard": guard,
        "multimodal": multimodal,
        "multiagente": multiagente,
        "eficiencia": eficiencia,
        "identidad": identidad,
        "pwa": pwa,
        "sce": sce,
        "evolucion_30x": {
            "active": bool(evolucion_30x.get("active")),
            "version": evolucion_30x.get("version"),
            "aprobadas": evolucion_30x.get("aprobadas_sce"),
            "prioridad_hoy": evolucion_30x.get("prioridad_hoy"),
            "nucleo": evolucion_30x.get("nucleo"),
        },
        "comic_engine": comic,
        "sistema_inmune": {
            "active": bool(sce.get("active")),
            "protocol": "IDENTIDAD_PROPIEDAD_SEGURIDAD_INMUNE",
            "version": "102.0.0",
            "identidad_grabada": bool((identidad or {}).get("active")),
            "creador": (identidad or {}).get("creador") or "Israel Monta",
        },
        "conectividad": {
            "active": True,
            "version": "104.0.0",
            "protocol": "RECONEXION_EMERGENCIA_PUERTOS_PERIFERICOS",
        },
        "nucleo_perceptivo": _nucleo_perceptivo_payload(),
        "mente": _mente_conexion_payload(),
        "protocol": ver.get("protocol") or "SALOMON_VIVIENTE",
    }


def _mente_conexion_payload() -> dict:
    try:
        from mente.conexion import conexion_cerebral_estado

        return conexion_cerebral_estado()
    except Exception as exc:
        return {"ok": False, "conexion": "ERROR", "error": type(exc).__name__}


def _nucleo_perceptivo_payload() -> dict:
    try:
        from config import estado_nucleo_perceptivo

        return estado_nucleo_perceptivo()
    except Exception as exc:
        return {
            "ok": False,
            "confirmacion": "Núcleo perceptivo incompleto — revisar config/",
            "error": type(exc).__name__,
        }


def _salud_dashboard_html(payload: dict) -> str:
    """Salomón Health Dashboard (v41) — vista viviente para navegador / PWA."""
    ok = bool((payload.get("system_guard") or {}).get("integrity_ok", True))
    integridad = "100% OK" if ok else "DRIFT DETECTADO"
    version = payload.get("version") or "41.0.0"
    protocol = payload.get("protocol") or "SALOMON_VIVIENTE"
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <meta name="theme-color" content="#0a0a0b" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-title" content="Salomón VIVO" />
  <title>Salomón VIVO — Salud</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap" rel="stylesheet" />
  <style>
    :root {{
      --bg0: #070708;
      --bg1: #121316;
      --neon: #39ff14;
      --neon-dim: #1a8f0a;
      --text: #e8eae6;
      --muted: #8a9088;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{
      min-height: 100%;
      background:
        radial-gradient(ellipse 80% 50% at 50% 0%, #1a2214 0%, transparent 55%),
        linear-gradient(165deg, var(--bg0) 0%, var(--bg1) 100%);
      color: var(--text);
      font-family: "Outfit", sans-serif;
    }}
    main {{
      min-height: 100dvh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 2rem 1.25rem 3rem;
      gap: 1.25rem;
    }}
    .brand {{
      font-size: 0.75rem;
      letter-spacing: 0.28em;
      text-transform: uppercase;
      color: var(--muted);
      font-weight: 600;
    }}
    h1 {{
      font-size: clamp(1.55rem, 5.5vw, 2.35rem);
      font-weight: 700;
      color: var(--neon);
      text-shadow: 0 0 18px rgba(57, 255, 20, 0.35);
      line-height: 1.25;
      max-width: 18ch;
    }}
    .sub {{
      font-size: clamp(1rem, 3.2vw, 1.2rem);
      color: var(--text);
      opacity: 0.92;
    }}
    .meta {{
      font-size: 0.8rem;
      color: var(--muted);
      letter-spacing: 0.04em;
    }}
    .cta {{
      margin-top: 1.5rem;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 3rem;
      padding: 0.85rem 1.75rem;
      border-radius: 999px;
      border: 1px solid rgba(57, 255, 20, 0.45);
      background: linear-gradient(180deg, rgba(57, 255, 20, 0.16), rgba(57, 255, 20, 0.05));
      color: var(--neon);
      font: inherit;
      font-weight: 600;
      font-size: 1rem;
      text-decoration: none;
      letter-spacing: 0.02em;
      transition: background 0.2s ease, border-color 0.2s ease, transform 0.15s ease;
    }}
    .cta:hover {{
      background: linear-gradient(180deg, rgba(57, 255, 20, 0.28), rgba(57, 255, 20, 0.1));
      border-color: var(--neon);
    }}
    .cta:active {{ transform: scale(0.98); }}
    @media (prefers-reduced-motion: reduce) {{
      .cta {{ transition: none; }}
    }}
  </style>
</head>
<body>
  <main>
    <p class="brand">Salomón AI · {protocol}</p>
    <h1>Estado: SALOMÓN VIVIENTE</h1>
    <p class="sub">Integridad del Sistema: {integridad}</p>
    <p class="meta">v{version}</p>
    <a class="cta" href="/">Volver al Asistente</a>
  </main>
</body>
</html>"""


@app.get("/api/salud")
def salud(request: Request):
    """
    Health Dashboard (HTML en navegador) + JSON para Render/monitores.
    HTML: navegación documento / Accept text/html / ?view=dashboard
    JSON: probes, Accept json, ?format=json
    """
    payload = _salud_payload()
    fmt = (request.query_params.get("format") or "").lower()
    view = (request.query_params.get("view") or "").lower()
    if fmt == "json" or view == "json":
        return payload
    if view in {"dashboard", "html", "ui"}:
        return HTMLResponse(content=_salud_dashboard_html(payload), status_code=200)
    if request.headers.get("sec-fetch-dest") == "document":
        return HTMLResponse(content=_salud_dashboard_html(payload), status_code=200)
    accept = (request.headers.get("accept") or "").lower()
    if "text/html" in accept:
        html_i = accept.find("text/html")
        json_i = accept.find("application/json")
        if json_i < 0 or html_i < json_i:
            return HTMLResponse(content=_salud_dashboard_html(payload), status_code=200)
    return payload


@app.get("/api/nucleo/perceptivo")
def nucleo_perceptivo() -> dict:
    """Visión + Voz + Memory Cortex — confirmación de núcleo."""
    return _nucleo_perceptivo_payload()


@app.get("/api/mente/conexion")
def mente_conexion() -> dict:
    """Estado de conexión cerebral unificada (arquitectura semántica)."""
    from mente.conexion import conexion_cerebral_estado

    return conexion_cerebral_estado()


@app.get("/api/proveedores")
def api_proveedores() -> dict:
    """
    Inventario Provider Pattern + infraestructura neuronal.
    No expone secretos — solo presencia, cadena activa y SBI.
    """
    from cognicion.servicios import obtener_manager

    mgr = obtener_manager()
    return {**mgr.estado(), "infraestructura": mgr.infraestructura_lista()}


@app.get("/api/core/kernel")
def api_core_kernel() -> dict:
    """Kernel /core — MainController.init estado."""
    from core.cortex.main_controller import MainController

    return MainController.estado()


@app.post("/api/core/kernel/init")
def api_core_kernel_init() -> dict:
    """Fuerza init() del kernel Python (saludo + locks)."""
    from core.cortex.main_controller import MainController

    return MainController.init()


@app.get("/boot/{path:path}")
def boot_static(path: str):
    """Sirve studio/dist/boot/** (permisos, PWA, heal)."""
    safe = path.replace("\\", "/").lstrip("/")
    if ".." in safe.split("/"):
        raise HTTPException(status_code=400, detail="ruta_invalida")
    ruta = STUDIO_DIR / "boot" / safe
    if not ruta.is_file():
        raise HTTPException(status_code=404, detail="boot_asset_missing")
    media = "application/javascript" if safe.endswith(".js") else "text/plain"
    return FileResponse(ruta, media_type=media, headers={"Cache-Control": "no-cache"})


@app.get("/ui/{path:path}")
def ui_static(path: str):
    """Sirve studio/dist/ui/** (drawers, overlays, indicadores)."""
    safe = path.replace("\\", "/").lstrip("/")
    if ".." in safe.split("/"):
        raise HTTPException(status_code=400, detail="ruta_invalida")
    ruta = STUDIO_DIR / "ui" / safe
    if not ruta.is_file():
        raise HTTPException(status_code=404, detail="ui_asset_missing")
    media = "application/javascript" if safe.endswith(".js") else "text/plain"
    return FileResponse(ruta, media_type=media, headers={"Cache-Control": "no-cache"})


@app.get("/core/{path:path}")
def core_static(path: str):
    """Sirve studio/dist/core/** (kernel JS)."""
    safe = path.replace("\\", "/").lstrip("/")
    if ".." in safe.split("/"):
        raise HTTPException(status_code=400, detail="ruta_invalida")
    ruta = STUDIO_DIR / "core" / safe
    if not ruta.is_file():
        raise HTTPException(status_code=404, detail="core_asset_missing")
    media = "application/javascript" if safe.endswith(".js") else "text/plain"
    return FileResponse(ruta, media_type=media, headers={"Cache-Control": "no-cache"})


@app.get("/api/salud/detalle")
def salud_detalle() -> dict:
    memoria_ok = False
    try:
        from cognicion.memoria.vectorial import obtener_memoria

        memoria_ok = obtener_memoria().activa
    except Exception:
        memoria_ok = False

    from cognicion.llm import gemini_disponible, llm_disponible, proveedor_respaldo_disponible
    from settings import GROQ_API_KEY, LLM_LOCAL_FALLBACK, OPENAI_API_KEY

    return {
        "estado": "ok",
        "servicio": "Salomón AI",
        "version": "1.0.0",
        "cognicion": {
            "memoria_vectorial": memoria_ok,
            "pilares": ["memoria", "razonamiento", "vision", "autocorreccion", "agente"],
            "agente_autonomo": AGENTE_AUTONOMO_HABILITADO,
            "tts_async": TTS_ASYNC,
            "aprendizaje_async": APRENDIZAJE_ASYNC,
            "log_level": LOG_LEVEL,
            "proveedor_llm": MODEL_PROVIDER,
            "llm_disponible": llm_disponible(),
            "gemini_disponible": gemini_disponible(),
            "openai_configurado": bool(OPENAI_API_KEY),
            "groq_configurado": bool(GROQ_API_KEY),
            "llm_local_fallback": LLM_LOCAL_FALLBACK,
            "proveedor_respaldo": proveedor_respaldo_disponible(),
        },
        "bca": os.getenv("BCA_SUPERVISOR") == "1",
    }


@app.get("/api/bca/estado")
def api_bca_estado() -> dict:
    """Estado del Branch de Control Autónomo (indicador UI verde/rojo)."""
    from cognicion.orquesta.bca import leer_estado, puerto_ocupado, salud_http

    st = leer_estado()
    servidor = salud_http() or puerto_ocupado()
    bca_activo = bool(st.get("bca_activo"))
    # Verde: BCA vivo y servidor OK · Rojo: necesita intervención
    if bca_activo and servidor:
        color = "verde"
        etiqueta = "BCA activo"
        necesita = False
    elif bca_activo and not servidor:
        color = "ambar"
        etiqueta = "BCA reiniciando"
        necesita = False
    elif servidor and not bca_activo:
        color = "ambar"
        etiqueta = "Servidor sin BCA"
        necesita = True
    else:
        color = "rojo"
        etiqueta = "Intervención requerida"
        necesita = True
    return {
        "exito": True,
        "bca_activo": bca_activo,
        "servidor_ok": servidor,
        "necesita_intervencion": necesita,
        "color": color,
        "etiqueta": etiqueta,
        "detalle": st,
    }


@app.get("/api/tunel/estado")
def api_tunel_estado() -> dict:
    """Public URL del túnel localtunnel (acceso móvil)."""
    from cognicion.red.tunel import leer_estado_tunel

    st = leer_estado_tunel()
    return {
        "exito": True,
        "activo": bool(st.get("activo")),
        "public_url": st.get("public_url"),
        "puerto": st.get("puerto") or 8000,
        "error": st.get("error"),
    }


class TtsResponse(BaseModel):
    audio_base64: str | None = None
    audio_mime: str = "audio/wav"
    tts_disponible: bool = False
    error: str | None = None


@app.post("/api/tts", response_model=TtsResponse)
def api_tts(body: TextoRequest) -> TtsResponse:
    """TTS ServiceManager — ElevenLabs → Cartesia (única ruta neuronal)."""
    from cognicion.servicios import obtener_manager

    resultado = obtener_manager().hablar(body.texto)
    return TtsResponse(
        audio_base64=resultado.audio_base64,
        audio_mime=resultado.audio_mime or "audio/wav",
        tts_disponible=resultado.tts_disponible,
        error=resultado.error,
    )


@app.post("/api/stt")
async def api_stt(
    audio: UploadFile = File(...),
) -> dict:
    """STT Deepgram — ciclo de escucha servidor (ServiceManager)."""
    from cognicion.servicios import obtener_manager

    raw = await audio.read()
    mime = audio.content_type or "audio/wav"
    return obtener_manager().escuchar(raw, mime=mime)


class HablarRequest(BaseModel):
    texto: str = Field(..., min_length=1, max_length=4000)


@app.post("/api/acciones/hablar")
def api_hablar(body: HablarRequest) -> dict:
    from acciones.hablar import hablar

    return hablar(body.texto)


@app.post("/api/ai-process", response_model=ChatResponse)
@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    session_id, salomon = _obtener_o_crear_sesion(body.session_id)

    if body.fase1:
        from cognicion.autonoma.fase1 import ejecutar_fase1

        pack = ejecutar_fase1(
            body.mensaje,
            imagen_base64=body.imagen_base64,
            imagen_mime=body.imagen_mime,
        )
        texto = pack.get("texto") or ""
        meta = dict(pack.get("metadata") or {})
        meta["fase1"] = True
        if body.mensaje.strip() or body.imagen_base64:
            _persistir_turno(
                session_id,
                (body.mensaje or "").strip() or "[foto]",
                texto,
            )
        return ChatResponse(
            texto=texto,
            exito=bool(pack.get("exito")),
            session_id=session_id,
            metadata=meta,
            audio_base64=None,
            audio_mime="audio/mpeg",
            tts_disponible=False,
        )

    # Conexión cerebral unificada (mente/ → cerebro)
    from mente.conexion import procesar_unificado

    respuesta = procesar_unificado(
        body.mensaje,
        session_id=session_id,
        salomon=salomon,
        lat=body.lat,
        lon=body.lon,
        imagen_base64=body.imagen_base64,
        imagen_mime=body.imagen_mime,
        error_consola=body.error_consola,
        autonomo=body.autonomo,
    )

    if body.mensaje.strip():
        _persistir_turno(session_id, body.mensaje.strip(), respuesta.texto)

    return ChatResponse(
        texto=respuesta.texto,
        exito=respuesta.exito,
        session_id=session_id,
        metadata=respuesta.metadata,
        audio_base64=respuesta.audio_base64,
        audio_mime=respuesta.audio_mime,
        tts_disponible=respuesta.tts_disponible,
    )


class Fase1Request(BaseModel):
    mensaje: str = Field(default="", max_length=4000)
    session_id: str | None = None
    imagen_base64: str | None = Field(default=None, max_length=8_000_000)
    imagen_mime: str = "image/png"


@app.get("/api/autonoma/fase1/estado")
def autonoma_fase1_estado() -> dict:
    return {
        "ok": True,
        "fase": "1",
        "protocolo": "SALOMON_AUTONOMO_FASE1",
        "capacidades": {
            "vision_escena": True,
            "agentes_paralelos": ["busqueda", "sintesis"],
            "streaming_estados": True,
            "audio_interim": True,
        },
        "siguiente": "Fase 2 — analítico + verificador + HF/Wikipedia profunda",
        "firma": "Created by Israel Monta - Salomón AI Studio",
    }


@app.post("/api/autonoma/fase1")
def autonoma_fase1(body: Fase1Request) -> dict:
    """JSON síncrono — misma lógica que el stream, sin SSE."""
    from cognicion.autonoma.fase1 import ejecutar_fase1

    session_id, _salomon = _obtener_o_crear_sesion(body.session_id)
    pack = ejecutar_fase1(
        body.mensaje,
        imagen_base64=body.imagen_base64,
        imagen_mime=body.imagen_mime,
    )
    texto = pack.get("texto") or ""
    if body.mensaje.strip() or body.imagen_base64:
        _persistir_turno(
            session_id,
            (body.mensaje or "").strip() or "[foto]",
            texto,
        )
    return {
        "texto": texto,
        "exito": bool(pack.get("exito")),
        "session_id": session_id,
        "metadata": pack.get("metadata") or {},
    }


@app.post("/api/autonoma/fase1/stream")
def autonoma_fase1_stream(body: Fase1Request) -> StreamingResponse:
    """
    SSE: emite status (Estoy pensando / buscando / sintetizando…)
    y cierra con evento done { texto, metadata }.
    """
    from cognicion.autonoma.fase1 import evento_sse, iter_eventos_fase1

    session_id, _salomon = _obtener_o_crear_sesion(body.session_id)

    def gen():
        final_texto = ""
        for ev in iter_eventos_fase1(
            body.mensaje,
            imagen_base64=body.imagen_base64,
            imagen_mime=body.imagen_mime,
        ):
            if ev.get("type") == "done":
                final_texto = ev.get("texto") or ""
                ev = {**ev, "session_id": session_id}
            yield evento_sse(ev)
        if final_texto and (body.mensaje.strip() or body.imagen_base64):
            try:
                _persistir_turno(
                    session_id,
                    (body.mensaje or "").strip() or "[foto]",
                    final_texto,
                )
            except Exception:
                pass

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.options("/api/chat/nuevo")
def nuevo_chat_options() -> JSONResponse:
    """Preflight CORS — elimina 403/bloqueo en boot del kernel."""
    return JSONResponse(
        content={"ok": True},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "86400",
        },
    )


@app.post("/api/chat/nuevo", response_model=SessionResponse)
def nuevo_chat(session_id: str | None = None, reiniciar: bool = False) -> JSONResponse:
    if reiniciar:
        if session_id and session_id in _sesiones:
            _sesiones[session_id].reiniciar_conversacion()
            limpiar_sesion(session_id)
            salomon = _sesiones[session_id]
        elif session_id and sesion_existe(session_id):
            salomon = _restaurar_sesion(session_id)
            salomon.reiniciar_conversacion()
            limpiar_sesion(session_id)
            _sesiones[session_id] = salomon
        else:
            session_id, salomon = _obtener_o_crear_sesion(None)
    else:
        session_id, salomon = _obtener_o_crear_sesion(session_id)

    # Protocolo de inicio cerebral (siempre al abrir / nuevo chat)
    from mente.protocolo_inicio import protocolo_inicio

    ciclo = protocolo_inicio(session_id)
    frase = ciclo["frase"]
    _persistir_turno(session_id, "[inicio]", frase)
    payload = SessionResponse(
        session_id=session_id,
        mensaje=frase,
        audio_base64=ciclo.get("audio_base64"),
        audio_mime=ciclo.get("audio_mime") or "audio/wav",
        tts_disponible=bool(ciclo.get("tts_disponible")),
    )
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    return JSONResponse(
        content=data,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@app.get("/api/historial", response_model=HistorialResponse)
def historial(session_id: str) -> HistorialResponse:
    if session_id in _sesiones:
        salomon = _sesiones[session_id]
        mensajes = [
            HistorialItem(rol=m.rol, contenido=m.contenido)
            for m in salomon.historial
            if m.rol in ("usuario", "asistente")
        ]
        return HistorialResponse(session_id=session_id, mensajes=mensajes)

    if sesion_existe(session_id):
        mensajes_db = cargar_mensajes(session_id)
        return HistorialResponse(
            session_id=session_id,
            mensajes=[
                HistorialItem(rol=m["rol"], contenido=m["contenido"])
                for m in mensajes_db
            ],
        )

    raise HTTPException(status_code=404, detail="Sesión no encontrada")


@app.get("/api/cognicion/estado")
def cognicion_estado(session_id: str | None = None) -> dict:
    from cognicion.cache import estadisticas as estadisticas_cache
    from cognicion.conectores import listar_conectores
    from cognicion.llm import obtener_proveedor
    from cognicion.memoria.tipos import TipoMemoria
    from cognicion.skills import listar_skills

    sid, salomon = _obtener_o_crear_sesion(session_id)
    motor = salomon._motor
    intencion = getattr(motor, "_ultima_intencion", None)
    return {
        "session_id": sid,
        "memoria_activa": motor.memoria.activa,
        "pilares": {
            "memoria": motor.memoria.activa,
            "razonamiento": True,
            "cognitive_core": True,
            "universal_code_engine": True,
            "empatia": True,
            "code_guardrails": True,
            "vision": True,
            "autocorreccion": True,
            "agente": True,
            "aprendizaje": True,
            "skills": True,
        },
        "cognitive_core": {
            "version": "60.0.0",
            "ciclo": ["analisis", "planificacion", "ejecucion", "verificacion"],
            "protocol": "COGNITIVE_CORE_CODING_ENGINE",
        },
        "intencion_ultima": intencion.value if intencion else None,
        "skills": [s.id for s in listar_skills()],
        "conectores": listar_conectores(),
        "proveedor_llm": obtener_proveedor().nombre,
        "memoria_capas": [c.value for c in TipoMemoria],
        "cache": estadisticas_cache(),
    }


@app.get("/api/cognicion/cognitive-core")
def cognicion_cognitive_core() -> dict:
    """Estado del motor Cognitive Core & Coding Engine (v60)."""
    return {
        "protocol": "COGNITIVE_CORE_CODING_ENGINE",
        "version": "60.0.0",
        "parent_protocol": "SALOMON_VIVIENTE",
        "modules": {
            "chain_of_thought": {
                "ciclo": ["analisis", "planificacion", "ejecucion", "verificacion"],
                "pensamiento_critico": True,
            },
            "universal_code_engine": {
                "lenguajes": ["python", "javascript", "html", "c++"],
                "matematica_sandbox": True,
            },
            "empatia_cognitiva": True,
            "code_guardrails": {"sandbox": "interno"},
        },
        "active": True,
    }


@app.get("/api/cognicion/multimodal")
def cognicion_multimodal() -> dict:
    """Estado Multimodal Core & Visual Agents (v70)."""
    from cognicion.multimodal import estado_multimodal

    return estado_multimodal()


@app.get("/api/agentes/estado")
def agentes_estado() -> dict:
    """Estado Multi-Agent + Máxima Eficiencia (v95)."""
    from cognicion.agente.coordinador import estado_multiagente

    return estado_multiagente()


@app.get("/api/esencia")
def api_esencia() -> dict:
    """Protocolo de Esencia 2026+ — auditoría leyes + regeneración + malla."""
    from cognicion.esencia import auditoria_esencia

    return auditoria_esencia(auto_heal=True)


class EsenciaArquitectoRequest(BaseModel):
    tarea: str = ""
    mensaje: str = ""
    con_busqueda: bool = True


@app.post("/api/esencia/arquitecto")
def api_esencia_arquitecto(body: EsenciaArquitectoRequest) -> dict:
    """Despliega Arquitecto → micro-agentes (Estado Vivo)."""
    from cognicion.esencia import arquitecto_desplegar

    tarea = (body.tarea or body.mensaje or "").strip()
    if not tarea:
        return {"ok": False, "error": "tarea_requerida"}
    return arquitecto_desplegar(tarea, con_busqueda=body.con_busqueda)


class SbiEnrollRequest(BaseModel):
    audio_base64: str = Field(..., min_length=8)
    audio_mime: str = "audio/wav"
    enroll_token: str | None = None


class SbiVerifyRequest(BaseModel):
    audio_base64: str | None = None
    audio_mime: str = "audio/wav"
    recovery_key: str | None = None


@app.get("/api/sbi/estado")
def api_sbi_estado() -> dict:
    """SBI-PRO — estado (sin secretos ni huella)."""
    from cognicion.seguridad.sbi_pro import estado_sbi

    return estado_sbi()


@app.get("/api/sbi/challenge")
def api_sbi_challenge() -> dict:
    """Frase de desafío para enrollment / verificación en voz."""
    from cognicion.seguridad.sbi_pro import estado_sbi

    st = estado_sbi()
    return {
        "protocolo": st["protocolo"],
        "challenge": st["challenge"],
        "owner": st["owner"],
        "enrolled": st["enrolled"],
    }


@app.post("/api/sbi/enroll")
def api_sbi_enroll(body: SbiEnrollRequest, request: Request) -> dict:
    """
    Enrollment de huella de Israel.
    Auth: header X-SBI-Enroll-Token == SBI_ENROLL_TOKEN, o rol admin.
    """
    from cognicion.seguridad.sbi_pro import enrollar

    token_hdr = request.headers.get("x-sbi-enroll-token") or body.enroll_token
    admin_ok = False
    try:
        _requiere_admin(request)
        admin_ok = True
    except HTTPException:
        admin_ok = False

    return enrollar(
        body.audio_base64,
        mime=body.audio_mime,
        enroll_token=token_hdr,
        admin_ok=admin_ok,
    )


@app.post("/api/sbi/verify")
def api_sbi_verify(body: SbiVerifyRequest) -> dict:
    """Verifica audio contra plantilla enrollada (o recovery key)."""
    from cognicion.seguridad.sbi_pro import verificar

    return verificar(
        body.audio_base64,
        mime=body.audio_mime,
        recovery_key=body.recovery_key,
    ).a_dict()


class EjecutivoRequest(BaseModel):
    modulo: str = Field(
        default="completo",
        description="mercados|contenido|oportunidades|contactos|completo",
    )
    consulta: str = ""
    tema: str = ""
    numero: str = ""
    plataforma: str = "shorts"
    actor: str = "Israel Montas"


@app.get("/api/ejecutivo/estado")
def api_ejecutivo_estado() -> dict:
    """Cerebro Ejecutivo — estado (exclusivo Israel Montas)."""
    from cognicion.ejecutivo import estado_ejecutivo

    return estado_ejecutivo()


@app.post("/api/ejecutivo/informe")
def api_ejecutivo_informe(body: EjecutivoRequest) -> dict:
    """Informe ejecutivo: mercados / contenido / oportunidades / contactos."""
    from cognicion.ejecutivo import informe_ejecutivo
    from settings import EJECUTIVO_ENABLED

    if not EJECUTIVO_ENABLED:
        return {"ok": False, "error": "ejecutivo_desactivado"}
    return informe_ejecutivo(
        modulo=body.modulo,  # type: ignore[arg-type]
        consulta=body.consulta,
        tema=body.tema,
        numero=body.numero,
        plataforma=body.plataforma,
        actor=body.actor,
    )


class CognitivoCorreccionRequest(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None
    causa_raiz: str = ""


class CognitivoConsolidarRequest(BaseModel):
    session_id: str | None = None
    notas: str = ""


@app.get("/api/cognitivo/estado")
def api_cognitivo_estado() -> dict:
    """Cerebro Cognitivo Dual — Despertar."""
    from cognicion.cognitivo import estado_cognitivo_dual

    return estado_cognitivo_dual()


@app.post("/api/cognitivo/pre")
def api_cognitivo_pre(body: CognitivoCorreccionRequest) -> dict:
    """Ciclo pre-tarea: claridad + crítico + lecciones episódicas."""
    from cognicion.cognitivo import ciclo_pre_tarea

    return ciclo_pre_tarea(body.mensaje, session_id=body.session_id)


@app.post("/api/cognitivo/correccion")
def api_cognitivo_correccion(body: CognitivoCorreccionRequest) -> dict:
    """Registra corrección de Israel → memoria episódica + frase de aprendizaje."""
    from cognicion.cognitivo import registrar_correccion

    return registrar_correccion(
        body.mensaje,
        session_id=body.session_id,
        causa_raiz=body.causa_raiz,
    )


@app.post("/api/cognitivo/consolidar")
def api_cognitivo_consolidar(body: CognitivoConsolidarRequest) -> dict:
    """Limpieza y consolidación de sesión → esencia permanente."""
    from cognicion.cognitivo import consolidar_sesion

    return consolidar_sesion(body.session_id, notas=body.notas)


@app.get("/api/eficiencia")
def api_eficiencia() -> dict:
    from cognicion.eficiencia import estado_eficiencia

    return estado_eficiencia()


@app.get("/api/identidad")
def api_identidad() -> dict:
    from cognicion.evolucion import estado_sistema_inmune
    from cognicion.identidad import estado_identidad
    from cognicion.web import estado_web_architect

    inmune = estado_sistema_inmune()
    return {
        **estado_identidad(),
        "web_architect": estado_web_architect(),
        "sistema_inmune": {
            "active": inmune.get("sistema_inmune_activo"),
            "nucleo": inmune.get("nucleo"),
            "confirmacion": inmune.get("confirmacion"),
            "modulos_centrales": inmune.get("modulos_centrales"),
        },
    }


@app.get("/api/inmune")
def api_sistema_inmune() -> dict:
    """Sistema Inmune + identidad blindada (v102)."""
    from cognicion.evolucion import estado_sistema_inmune

    return estado_sistema_inmune()


@app.get("/api/conectividad")
def api_conectividad_estado() -> dict:
    """Estado de reconexión (puertos, memoria, gateway) v104."""
    from cognicion.reconexion import estado_conectividad

    return estado_conectividad()


@app.post("/api/conectividad/reconectar")
def api_conectividad_reconectar() -> dict:
    """Ejecuta protocolo de reconexión de emergencia + eco."""
    from cognicion.reconexion import ejecutar_reconexion_emergencia

    return ejecutar_reconexion_emergencia()


@app.get("/api/auditoria/cruzada")
def api_auditoria_cruzada() -> dict:
    """Auditoría cruzada Cursor↔Salomón + reparación forzosa (v105)."""
    from cognicion.auditoria_cruzada import ejecutar_auditoria_cruzada

    return ejecutar_auditoria_cruzada()


class WebArchitectRequest(BaseModel):
    peticion: str = Field(..., min_length=1, max_length=4000)


@app.post("/api/web/arquitecto")
def api_web_arquitecto(body: WebArchitectRequest) -> dict:
    from cognicion.web import ejecutar_arquitecto_web

    return ejecutar_arquitecto_web(body.peticion)


@app.get("/api/web/arquitecto")
def api_web_arquitecto_estado() -> dict:
    from cognicion.web import estado_web_architect

    return estado_web_architect()


class CoordinarRequest(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None


@app.post("/api/agentes/coordinar")
def agentes_coordinar(body: CoordinarRequest) -> dict:
    """Despacho zero-overlap al agente especializado (lazy)."""
    from cognicion.agente.coordinador import coordinar

    return coordinar(body.mensaje)


class VisionBuscarRequest(BaseModel):
    consulta: str = Field(..., min_length=1, max_length=2000)
    generar_si_falta: bool = True
    session_id: str | None = None


@app.post("/api/cognicion/vision/buscar")
def cognicion_vision_buscar(body: VisionBuscarRequest) -> dict:
    """Agente de recuperación visual (scraper) + fallback HD."""
    from cognicion.multimodal import ejecutar_con_presupuesto
    from cognicion.vision.busqueda_visual import buscar_visual, recuperar_o_generar

    if body.generar_si_falta:
        return ejecutar_con_presupuesto(recuperar_o_generar, body.consulta)
    return ejecutar_con_presupuesto(buscar_visual, body.consulta)


@app.get("/api/nucleo/estado")
def nucleo_estado() -> dict:
    """Mapa del Sistema Operativo de IA — componentes, motores y eventos."""
    from cognicion.agente.registro import listar_agentes
    from cognicion.modelos.gestor import listar_tareas
    from cognicion.mcp.cliente import estado_mcp
    from cognicion.nucleo import obtener_nucleo
    from cognicion.plugins.cargador import descubrir_plugins

    nucleo = obtener_nucleo()
    return {
        "os": "Salomón AI",
        "arquitectura": "ARQUITECTURA.md",
        **nucleo.mapa(),
        "tareas_modelo": listar_tareas(),
        "agentes": [
            {"id": a.id, "nombre": a.nombre, "rol": a.rol, "activo": a.activo}
            for a in listar_agentes(activos_only=False)
        ],
        "mcp": estado_mcp(),
        "plugins_descubiertos": descubrir_plugins(),
    }


@app.get("/api/seguridad/estado")
def seguridad_estado(request: Request) -> dict:
    """Panel de ciberseguridad — requiere admin si SALOMON_ADMIN_KEY está configurada."""
    _requiere_admin(request)
    from cognicion.seguridad import obtener_motor

    return obtener_motor().estado()


@app.get("/api/seguridad/auditoria")
def seguridad_auditoria(request: Request, limite: int = 50) -> dict:
    """Registro de auditoría — quién, qué, cuándo, desde dónde."""
    _requiere_admin(request)
    from cognicion.seguridad.auditoria import listar as listar_auditoria

    return {"registros": listar_auditoria(limite=min(limite, 200))}


@app.get("/api/seguridad/alertas")
def seguridad_alertas(request: Request) -> dict:
    """Alertas activas de intrusión y anomalías."""
    _requiere_admin(request)
    from cognicion.seguridad.anomalias import obtener_detector_anomalias
    from cognicion.seguridad.intrusion import obtener_detector
    from cognicion.seguridad import obtener_motor

    motor = obtener_motor()
    return {
        "intrusion": obtener_detector().ultimos_eventos(20),
        "anomalias": obtener_detector_anomalias().alertas_activas(20),
        "motor": motor.estado().get("alertas_motor", []),
    }


@app.post("/api/seguridad/snapshot")
def seguridad_snapshot(request: Request) -> dict:
    """Crea copia de seguridad manual."""
    _requiere_admin(request)
    from cognicion.seguridad.recuperacion import crear_snapshot

    return crear_snapshot(motivo="manual_admin")


@app.get("/api/seguridad/snapshots")
def seguridad_snapshots(request: Request) -> dict:
    """Lista copias de seguridad disponibles."""
    _requiere_admin(request)
    from cognicion.seguridad.recuperacion import listar_snapshots

    return {"snapshots": listar_snapshots()}


@app.post("/api/seguridad/recuperar/{servicio}")
def seguridad_recuperar(servicio: str, request: Request) -> dict:
    """Auto-reparación de un servicio degradado."""
    _requiere_admin(request)
    from cognicion.seguridad.recuperacion import intentar_recuperar

    if servicio not in ("llm", "memoria"):
        raise HTTPException(status_code=400, detail="Servicio no reconocido")
    return intentar_recuperar(servicio)


@app.post("/api/cognicion/vision", response_model=ChatResponse)
def cognicion_vision(body: VisionRequest) -> ChatResponse:
    session_id, salomon = _obtener_o_crear_sesion(body.session_id)
    respuesta = salomon.procesar_entrada(
        body.contexto or "Analiza esta captura y dime qué ves.",
        imagen_base64=body.imagen_base64,
        imagen_mime=body.imagen_mime,
    )
    entrada = (body.contexto or "Analiza esta captura y dime qué ves.").strip()
    _persistir_turno(session_id, entrada, respuesta.texto)
    return ChatResponse(
        texto=respuesta.texto,
        exito=respuesta.exito,
        session_id=session_id,
        metadata=respuesta.metadata,
        audio_base64=respuesta.audio_base64,
        audio_mime=respuesta.audio_mime,
        tts_disponible=respuesta.tts_disponible,
    )


@app.post("/api/cognicion/vdcp")
def cognicion_vdcp(body: VdcpRequest) -> dict:
    """
    Visión Dinámica de Campo Profundo (Colsub):
    gran angular → foveación → OCR de alta resolución.
    """
    from cognicion.orquesta.colsub import colsub_vdcp_bridge

    if not body.imagen_base64 and not body.ruta:
        raise HTTPException(status_code=400, detail="imagen_base64_o_ruta_requerida")
    pack = colsub_vdcp_bridge(
        imagen_base64=body.imagen_base64,
        ruta=body.ruta,
        max_foveas=body.max_foveas,
    )
    return {
        "exito": bool(pack.get("exito")),
        "session_id": body.session_id,
        "pipeline": pack.get("pipeline"),
        "escena": pack.get("escena"),
        "hallazgos": pack.get("hallazgos"),
        "textos": pack.get("textos"),
        "narrativa_consolidada": pack.get("narrativa_consolidada"),
        "ms": pack.get("ms"),
        "error": pack.get("error"),
    }


@app.get("/api/cognicion/vdcp/estado")
def cognicion_vdcp_estado() -> dict:
    from cognicion.vision.vdcp import estado_vdcp

    return estado_vdcp()


@app.post("/api/cognicion/error", response_model=ChatResponse)
def cognicion_error(body: ErrorConsolaRequest) -> ChatResponse:
    session_id, salomon = _obtener_o_crear_sesion(body.session_id)
    respuesta = salomon.procesar_entrada(
        body.mensaje,
        error_consola=body.error,
        autonomo=body.autonomo,
    )
    _persistir_turno(session_id, body.mensaje.strip(), respuesta.texto)
    return ChatResponse(
        texto=respuesta.texto,
        exito=respuesta.exito,
        session_id=session_id,
        metadata=respuesta.metadata,
        audio_base64=respuesta.audio_base64,
        audio_mime=respuesta.audio_mime,
        tts_disponible=respuesta.tts_disponible,
    )


@app.post("/api/cognicion/agente", response_model=ChatResponse)
def cognicion_agente(body: AgenteRequest) -> ChatResponse:
    session_id, salomon = _obtener_o_crear_sesion(body.session_id)
    respuesta = salomon.procesar_entrada(
        body.tarea,
        error_consola=body.error,
        autonomo=True,
    )
    _persistir_turno(session_id, body.tarea.strip(), respuesta.texto)
    return ChatResponse(
        texto=respuesta.texto,
        exito=respuesta.exito,
        session_id=session_id,
        metadata=respuesta.metadata,
        audio_base64=respuesta.audio_base64,
        audio_mime=respuesta.audio_mime,
        tts_disponible=respuesta.tts_disponible,
    )


class GrafoRequest(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None
    profundizar: bool = False
    forzar_busqueda: bool = False
    forzar_orquesta: bool = False
    ruta_forzada: str | None = None
    media_path: str | None = None
    media_ops: dict | None = None
    agentes: list[str] | None = None


@app.post("/api/grafo/ejecutar")
def api_grafo_ejecutar(body: GrafoRequest) -> dict:
    from cognicion.grafo import ejecutar_grafo

    meta: dict = {}
    if body.ruta_forzada:
        meta["ruta_forzada"] = body.ruta_forzada
    if body.forzar_busqueda:
        meta["forzar_busqueda"] = True
    if body.forzar_orquesta:
        meta["forzar_orquesta"] = True
    if body.agentes:
        meta["agentes"] = body.agentes
    estado = ejecutar_grafo(
        body.mensaje,
        session_id=body.session_id,
        profundizar=body.profundizar,
        metadata=meta,
        media_path=body.media_path,
        media_ops=body.media_ops,
        forzar_busqueda=body.forzar_busqueda,
        forzar_orquesta=body.forzar_orquesta,
    )
    return {
        "respuesta": estado.get("respuesta"),
        "ruta": estado.get("intencion") or estado.get("ruta"),
        "modo_razonamiento": estado.get("modo_razonamiento"),
        "razonamiento": estado.get("razonamiento"),
        "necesita_busqueda": estado.get("necesita_busqueda"),
        "necesita_orquesta": estado.get("necesita_orquesta"),
        "resultado_busqueda": estado.get("resultado_busqueda"),
        "hallazgos_agentes": estado.get("hallazgos_agentes"),
        "sintesis_lista": estado.get("sintesis_lista"),
        "session_id": estado.get("session_id"),
        "borrador_guion": estado.get("borrador_guion"),
        "resultado_tecnico": estado.get("resultado_tecnico"),
        "resultado_imagen": estado.get("resultado_imagen"),
        "resultado_video": estado.get("resultado_video"),
        "metadata": estado.get("metadata") or {},
        "error": estado.get("error"),
    }


@app.post("/api/orquesta/ejecutar")
def api_orquesta_ejecutar(body: GrafoRequest) -> dict:
    """Colsub: despliega 1–40 agentes on-demand y sintetiza."""
    from cognicion.grafo import ejecutar_grafo

    meta: dict = {"forzar_orquesta": True, "ruta_forzada": "orquestador"}
    if body.agentes:
        meta["agentes"] = body.agentes
        meta["colsub_n"] = len(body.agentes)
    estado = ejecutar_grafo(
        body.mensaje,
        session_id=body.session_id,
        profundizar=True,
        metadata=meta,
        forzar_orquesta=True,
    )
    return {
        "exito": bool(estado.get("sintesis_lista") or estado.get("respuesta")),
        "respuesta": estado.get("respuesta"),
        "hallazgos_agentes": estado.get("hallazgos_agentes"),
        "razonamiento": estado.get("razonamiento"),
        "colsub": ((estado.get("metadata") or {}).get("orquestador") or {}).get("colsub"),
        "metadata": estado.get("metadata") or {},
        "session_id": estado.get("session_id") or body.session_id,
        "error": estado.get("error"),
    }


@app.get("/api/orquesta/colsub/estado")
def api_colsub_estado() -> dict:
    """Estado de escalado, recursos y Orquestador de Carga."""
    from cognicion.orquesta import puntuacion_complejidad, recursos_criticos
    from cognicion.orquesta.colas import obtener_orquestador_carga
    from settings import (
        COLSUB_CPU_CRITICO,
        COLSUB_MAX_AGENTES,
        COLSUB_MAX_WORKERS,
        COLSUB_RAM_CRITICO,
    )

    critico, rec = recursos_criticos()
    orq = obtener_orquestador_carga()
    return {
        "nombre": "Colsub",
        "max_agentes": COLSUB_MAX_AGENTES,
        "max_workers": COLSUB_MAX_WORKERS,
        "cpu_critico": COLSUB_CPU_CRITICO,
        "ram_critico": COLSUB_RAM_CRITICO,
        "recursos_criticos": critico,
        "recursos": rec,
        "orquestador_carga": orq.snapshot(),
        "ejemplo_simple": puntuacion_complejidad("¿Qué es el sol?"),
        "ejemplo_complejo": puntuacion_complejidad(
            "Investiga a fondo el impacto económico, científico y estratégico "
            "del núcleo de la Tierra comparando fuentes académicas y de mercado."
        ),
    }


@app.post("/api/orquesta/diagnostico")
def api_orquesta_diagnostico() -> dict:
    """Protocolo de auto-diagnóstico de enjambres + confirmación de colas."""
    from cognicion.orquesta.colas import (
        autodiagnostico_enjambres,
        obtener_orquestador_carga,
    )

    # Activar / despertar orquestador de carga
    orq = obtener_orquestador_carga()
    reporte = autodiagnostico_enjambres()
    reporte["autoridad"] = {
        "protocolo": "colas",
        "director": "Israel",
        "orquestador_activo": orq.activo,
        "mensaje": (
            "Protocolo de trabajo cambiado: arquitectura de colas Colsub. "
            "Listo para consultas de alto rendimiento."
        ),
    }
    return reporte


class ColaRequest(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None
    prioridad: int = Field(5, ge=1, le=10)
    agentes_n: int | None = Field(None, ge=1, le=40)


@app.post("/api/orquesta/cola")
def api_orquesta_encolar(body: ColaRequest) -> dict:
    """Encola una consulta de alto rendimiento (FIFO + prioridad)."""
    from cognicion.orquesta.colas import obtener_orquestador_carga

    orq = obtener_orquestador_carga()
    job_id = orq.encolar(
        body.mensaje,
        session_id=body.session_id,
        prioridad=body.prioridad,
        forzar_n=body.agentes_n,
    )
    return {
        "exito": True,
        "job_id": job_id,
        "estado": "en_cola",
        "orquestador": orq.snapshot(),
    }


@app.get("/api/orquesta/cola/{job_id}")
def api_orquesta_cola_estado(job_id: str) -> dict:
    from cognicion.orquesta.colas import obtener_orquestador_carga

    orq = obtener_orquestador_carga()
    st = orq.estado_trabajo(job_id)
    if not st:
        raise HTTPException(status_code=404, detail="trabajo_no_encontrado")
    return st


class BusquedaRequest(BaseModel):
    consulta: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None
    via_grafo: bool = True


@app.post("/api/busqueda")
def api_busqueda(body: BusquedaRequest) -> dict:
    """Búsqueda web en vivo (Tavily / DuckDuckGo) — respaldo autónomo de Salomón."""
    if body.via_grafo:
        from cognicion.grafo import ejecutar_grafo

        estado = ejecutar_grafo(
            body.consulta,
            session_id=body.session_id,
            forzar_busqueda=True,
        )
        return {
            "exito": bool((estado.get("resultado_busqueda") or {}).get("exito", True)),
            "respuesta": estado.get("respuesta"),
            "resultado": estado.get("resultado_busqueda"),
            "ruta": "busqueda",
            "session_id": estado.get("session_id") or body.session_id,
            "metadata": estado.get("metadata") or {},
        }

    from cognicion.busqueda import responder_con_busqueda

    pack = responder_con_busqueda(body.consulta)
    return {
        "exito": bool(pack.get("exito")),
        "respuesta": pack.get("texto"),
        "resultado": pack.get("busqueda"),
        "ruta": None,
        "session_id": body.session_id,
        "metadata": {"motor": pack.get("motor")},
    }


class GenerarImagenRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None
    size: str = "1024x1024"
    quality: str = "hd"
    via_grafo: bool = True
    usar_routing: bool = True


class MediaRouteRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    hint: str | None = None  # imagen_hd | video_gen | postproceso
    motor: str | None = None
    imagen_entrada: str | None = None
    session_id: str | None = None
    async_mode: bool | None = None


@app.post("/api/media/route")
def api_media_route(body: MediaRouteRequest) -> dict:
    """
    Colsub Multi-Model Routing. En Free Tier / async_mode: encola y responde al instante.
    """
    from settings import MEDIA_ASYNC_DEFAULT, RENDER_FREE_TIER

    usar_async = body.async_mode if body.async_mode is not None else (MEDIA_ASYNC_DEFAULT or RENDER_FREE_TIER)
    if usar_async:
        from cognicion.media.jobs_async import encolar_media

        job = encolar_media(body.prompt, hint=body.hint or "imagen_hd", motor=body.motor)
        return {**job, "session_id": body.session_id}

    from cognicion.media.media_engine import bridge_colsub_media

    pack = bridge_colsub_media(
        body.prompt,
        hint=body.hint,
        imagen_entrada=body.imagen_entrada,
        forzar_motor=body.motor,
    )
    res = pack.get("resultado") or {}
    return {
        "exito": bool(pack.get("exito")),
        "tarea": pack.get("tarea"),
        "routing": pack.get("routing"),
        "resultado": res,
        "activo_url": res.get("url_relativa"),
        "protocolo": pack.get("protocolo") or "MAX_EFFICIENCY",
        "version": pack.get("version") or "95.0.0",
        "prompt_enhancer": pack.get("prompt_enhancer"),
        "motor_enhancer": pack.get("motor_enhancer"),
        "prompt_original": pack.get("prompt_original"),
        "latencia_ms": pack.get("latencia_ms"),
        "progreso_requerido": pack.get("progreso_requerido"),
        "budget_ms": pack.get("budget_ms"),
        "session_id": body.session_id,
        "error": res.get("error"),
        "async": False,
    }


@app.get("/api/media/jobs/{job_id}")
def api_media_job(job_id: str) -> dict:
    from cognicion.media.jobs_async import estado_job

    st = estado_job(job_id)
    if not st:
        raise HTTPException(status_code=404, detail="job_no_encontrado")
    return st


@app.post("/api/media/generar_imagen")
def api_media_generar_imagen(body: GenerarImagenRequest) -> dict:
    """Genera imagen HD — routing Colsub (Flux/MJ) o grafo."""
    if body.usar_routing:
        from cognicion.media.media_engine import bridge_colsub_media

        pack = bridge_colsub_media(body.prompt, hint="imagen_hd")
        res = pack.get("resultado") or {}
        return {
            "exito": bool(pack.get("exito")),
            "ruta_grafo": None,
            "routing": pack.get("routing"),
            "respuesta": (
                f"Motor {res.get('motor')} · calidad {res.get('calidad')}. "
                f"{res.get('url_relativa') or ''}"
            ),
            "resultado": res,
            "session_id": body.session_id,
            "error": res.get("error"),
        }

    from cognicion.grafo import ejecutar_grafo

    if body.via_grafo:
        estado = ejecutar_grafo(
            f"Genera una imagen: {body.prompt}",
            session_id=body.session_id,
            metadata={"ruta_forzada": "imagen"},
            media_ops={
                "prompt": body.prompt,
                "size": body.size,
                "quality": body.quality,
            },
        )
        img = estado.get("resultado_imagen") or {}
        return {
            "exito": bool(img.get("exito")),
            "ruta_grafo": "imagen",
            "respuesta": estado.get("respuesta"),
            "resultado": img,
            "session_id": estado.get("session_id") or body.session_id,
            "error": estado.get("error") or img.get("error"),
        }

    from cognicion.media import generar_imagen

    resultado = generar_imagen(
        body.prompt, size=body.size, quality=body.quality
    )
    return {
        "exito": bool(resultado.get("exito")),
        "ruta_grafo": None,
        "resultado": resultado,
        "session_id": body.session_id,
        "error": resultado.get("error"),
    }


@app.post("/api/media/editar_video")
async def api_media_editar_video(
    archivo: UploadFile = File(...),
    operacion: str = Form("cortar"),
    inicio: float = Form(0.0),
    fin: float | None = Form(None),
    texto_overlay: str = Form(""),
    brillo: float = Form(1.2),
    session_id: str | None = Form(None),
    via_grafo: bool = Form(True),
) -> dict:
    """Recibe video, lo edita (corte / overlay / filtro) y enruta al nodo video."""
    from cognicion.media import editar_video, guardar_upload

    raw = await archivo.read()
    if not raw:
        raise HTTPException(status_code=400, detail="archivo_vacio")
    if len(raw) > 120 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="video_demasiado_grande")

    path = guardar_upload(archivo.filename or "video.mp4", raw)
    ops = {
        "operacion": operacion,
        "inicio": inicio,
        "fin": fin,
        "texto_overlay": texto_overlay,
        "brillo": brillo,
        "ruta": str(path),
    }

    if via_grafo:
        from cognicion.grafo import ejecutar_grafo

        estado = ejecutar_grafo(
            f"Editar video: {operacion}",
            session_id=session_id,
            metadata={"ruta_forzada": "video"},
            media_path=str(path),
            media_ops=ops,
        )
        vid = estado.get("resultado_video") or {}
        return {
            "exito": bool(vid.get("exito")),
            "ruta_grafo": "video",
            "respuesta": estado.get("respuesta"),
            "upload": str(path),
            "resultado": vid,
            "session_id": estado.get("session_id") or session_id,
            "error": estado.get("error") or vid.get("error"),
        }

    resultado = editar_video(
        path,
        operacion=operacion,
        inicio=inicio,
        fin=fin,
        texto_overlay=texto_overlay,
        brillo=brillo,
    )
    return {
        "exito": bool(resultado.get("exito")),
        "ruta_grafo": None,
        "upload": str(path),
        "resultado": resultado,
        "session_id": session_id,
        "error": resultado.get("error"),
    }


@app.get("/api/media/estado")
def api_media_estado() -> dict:
    from cognicion.media.media_engine import estado_media_routing
    from cognicion.media.video import OPERACIONES, _moviepy_disponible
    from cognicion.multimodal import MEDIA_PROGRESS_BUDGET_MS, estado_multimodal
    from settings import MEDIA_PROMPT_ENHANCER, OPENAI_API_KEY

    routing = estado_media_routing()
    ej = routing.get("routing_ejemplo") or {}
    mm = estado_multimodal()
    return {
        "protocolo": "MULTIMODAL_CORE",
        "version": "70.0.0",
        "hub": routing.get("hub"),
        "calidad_forzada": routing.get("calidad_forzada"),
        "forzar_pro": routing.get("forzar_pro"),
        "prompt_enhancer": MEDIA_PROMPT_ENHANCER,
        "progress_budget_ms": MEDIA_PROGRESS_BUDGET_MS,
        "motores": routing.get("motores"),
        "imagen": {
            "motor_legacy": "dall-e-3" if OPENAI_API_KEY else "local_placeholder",
            "openai_configurada": bool(OPENAI_API_KEY),
            "routing": ej.get("imagen"),
        },
        "video": {
            "moviepy": _moviepy_disponible(),
            "operaciones": sorted(OPERACIONES),
            "routing": ej.get("video"),
        },
        "postproceso": ej.get("post"),
        "keys_configuradas": {
            k: bool((v or {}).get("configurado"))
            for k, v in (routing.get("motores") or {}).items()
        },
        "multimodal": mm,
    }


@app.get("/api/herramientas")
def api_herramientas_catalogo() -> dict:
    return herramientas.catalogo_herramientas()


@app.get("/api/herramientas/planes")
def api_planes() -> dict:
    return herramientas.planes_suscripcion()


@app.get("/api/herramientas/analiticas")
def api_analiticas(session_id: str | None = None) -> dict:
    turnos = 0
    if session_id and session_id in _sesiones:
        turnos = _sesiones[session_id]._contar_turnos()
    return herramientas.analiticas(turnos)


@app.get("/api/herramientas/solar")
def api_solar() -> dict:
    return herramientas.monitor_solar()


@app.get("/api/herramientas/optimizar")
def api_optimizar() -> dict:
    return herramientas.optimizar_rendimiento()


@app.get("/api/herramientas/seguridad")
def api_seguridad() -> dict:
    return herramientas.seguridad_yiiot()


@app.get("/api/herramientas/ayuda")
def api_ayuda() -> dict:
    return herramientas.ayuda_sistema()


@app.post("/api/herramientas/corregir")
def api_corregir(body: TextoRequest) -> dict:
    return herramientas.corregir_texto(body.texto)


@app.post("/api/herramientas/traducir")
def api_traducir(body: TraducirRequest) -> dict:
    return herramientas.traducir_texto(body.texto, body.origen, body.destino)


@app.post("/api/herramientas/cli")
def api_cli(body: CliRequest) -> dict:
    return herramientas.ejecutar_cli(body.comando)


@app.post("/api/herramientas/resumir")
async def api_resumir(archivo: UploadFile = File(...)) -> dict:
    contenido_bytes = await archivo.read()
    try:
        contenido = contenido_bytes.decode("utf-8")
    except UnicodeDecodeError:
        contenido = contenido_bytes.decode("latin-1", errors="replace")

    nombre = archivo.filename or "archivo.txt"
    return herramientas.resumir_archivo(nombre, contenido)


@app.post("/api/herramientas/backup/export")
def api_backup_export(body: BackupExportRequest) -> dict:
    return herramientas.exportar_backup(body.historial, body.config)


@app.post("/api/herramientas/backup/import")
def api_backup_import(body: BackupImportRequest) -> dict:
    return herramientas.importar_backup(body.contenido)


# UI Premium por capas: templates/ + static/css + static/js + static/assets
INDEX_TEMPLATE = "index.html"


def _respuesta_ui_premium(request: Request):
    """Sirve templates/index.html (estilos y JS solo vía /static/…)."""
    index_path = TEMPLATES_DIR / INDEX_TEMPLATE
    if not index_path.is_file():
        return JSONResponse(
            status_code=404,
            content={
                "error": "templates/index.html no encontrado",
                "ruta_esperada": str(index_path),
            },
        )
    return templates.TemplateResponse(
        request,
        INDEX_TEMPLATE,
        headers=_UI_NO_CACHE,
    )


@app.get("/")
def index(request: Request):
    """Raíz pública — UI Premium (templates/index.html)."""
    return _respuesta_ui_premium(request)


@app.get("/carcasa")
@app.get("/carcasa/")
@app.get("/carcasa_base.html")
@app.get("/vista-carcasa")
def carcasa_premium(request: Request):
    """Alias de la UI Premium (misma plantilla que /)."""
    return _respuesta_ui_premium(request)


@app.get("/api/carcasa-check")
def carcasa_check():
    """Diagnóstico: capas UI Premium presentes en el deploy."""
    css = BASE_DIR / "static" / "css" / "styles.css"
    js = BASE_DIR / "static" / "js" / "app.js"
    assets = BASE_DIR / "static" / "assets"
    index_path = TEMPLATES_DIR / INDEX_TEMPLATE
    return {
        "ok": index_path.is_file() and css.is_file() and js.is_file(),
        "capas": {
            "templates": str(index_path),
            "css": str(css),
            "js": str(js),
            "assets": str(assets),
        },
        "endpoints": ["/", "/carcasa", "/static/css/styles.css", "/static/js/app.js"],
    }


@app.get("/asistente")
def asistente_pwa():
    """PWA anterior (studio/dist/index.html)."""
    if STUDIO_DIR.exists() and (STUDIO_DIR / "index.html").exists():
        return FileResponse(
            STUDIO_DIR / "index.html",
            media_type="text/html; charset=utf-8",
            headers={"Cache-Control": "no-cache"},
        )
    return JSONResponse(status_code=404, content={"error": "UI asistente no encontrada"})


def _archivo_studio(
    nombre: str,
    media_type: str | None = None,
    *,
    cache: str = "public, max-age=86400",
) -> FileResponse:
    """Resuelve studio/dist, luego boot/, ui/, tools/ (anti-huérfanos)."""
    from pathlib import Path as _Path

    rel = _Path(nombre)
    leaf = rel.name
    candidatos = [
        STUDIO_DIR / rel,
        STUDIO_DIR / "boot" / leaf,
        STUDIO_DIR / "ui" / leaf,
        STUDIO_DIR / "tools" / leaf,
        BASE_DIR / rel,
    ]
    for ruta in candidatos:
        if ruta.is_file():
            return FileResponse(
                ruta,
                media_type=media_type,
                headers={"Cache-Control": cache},
            )
    raise HTTPException(status_code=404, detail="No encontrado")


@app.get("/media-panel.js")
def media_panel_js() -> FileResponse:
    return _archivo_studio("media-panel.js", "application/javascript")


@app.get("/visual-progress.js")
def visual_progress_js() -> FileResponse:
    return _archivo_studio("visual-progress.js", "application/javascript")


@app.get("/bca-indicator.js")
def bca_indicator_js() -> FileResponse:
    return _archivo_studio("bca-indicator.js", "application/javascript")


@app.get("/manifest.json")
@app.get("/manifest.webmanifest")
def manifest_json() -> FileResponse:
    """PWA manifest Premium (static/) con fallback studio."""
    premium = BASE_DIR / "static" / "manifest.json"
    if premium.is_file():
        return FileResponse(
            premium,
            media_type="application/manifest+json",
            headers={"Cache-Control": "no-cache"},
        )
    try:
        return _archivo_studio("manifest.json", "application/manifest+json")
    except HTTPException:
        return _archivo_studio("manifest.webmanifest", "application/manifest+json")


@app.get("/favicon-v2.ico")
def favicon_v2_ico() -> FileResponse:
    return _archivo_studio("favicon-v2.ico", "image/x-icon")


@app.get("/favicon-v2.svg")
def favicon_v2_svg() -> FileResponse:
    return _archivo_studio("favicon-v2.svg", "image/svg+xml")


@app.get("/favicon.svg")
def favicon() -> FileResponse:
    # Preferir identidad Salomón (v2)
    ruta = STUDIO_DIR / "icon-v2.svg"
    if ruta.is_file():
        return FileResponse(ruta, media_type="image/svg+xml")
    return _archivo_studio("favicon-v2.svg", "image/svg+xml")


@app.get("/icon-v2.svg")
def icon_v2_svg() -> FileResponse:
    return _archivo_studio("icon-v2.svg", "image/svg+xml")


@app.get("/icon.svg")
def icon_svg() -> FileResponse:
    # Compat: redirige al asset con cache-bust
    return _archivo_studio("icon-v2.svg", "image/svg+xml")


@app.get("/icon-192-v2.png")
def icon_192_v2() -> FileResponse:
    return _archivo_studio("icon-192-v2.png", "image/png")


@app.get("/icon-512-v2.png")
def icon_512_v2() -> FileResponse:
    return _archivo_studio("icon-512-v2.png", "image/png")


@app.get("/icon-192-maskable-v2.png")
def icon_192_maskable_v2() -> FileResponse:
    return _archivo_studio("icon-192-maskable-v2.png", "image/png")


@app.get("/icon-512-maskable-v2.png")
def icon_512_maskable_v2() -> FileResponse:
    return _archivo_studio("icon-512-maskable-v2.png", "image/png")


@app.get("/icon-192.png")
def icon_192() -> FileResponse:
    return _archivo_studio("icon-192-v2.png", "image/png")


@app.get("/icon-512.png")
def icon_512() -> FileResponse:
    return _archivo_studio("icon-512-v2.png", "image/png")


@app.get("/apple-touch-icon-v2.png")
def apple_touch_icon_v2() -> FileResponse:
    return _archivo_studio("apple-touch-icon-v2.png", "image/png")


@app.get("/apple-touch-icon.png")
def apple_touch_icon() -> FileResponse:
    return _archivo_studio("apple-touch-icon-v2.png", "image/png")


@app.get("/salomon-theme.css")
def salomon_theme_css() -> FileResponse:
    return _archivo_studio("salomon-theme.css", "text/css")


@app.get("/splash.css")
def splash_css() -> FileResponse:
    return _archivo_studio("splash.css", "text/css")


@app.get("/voice-orchestrator.css")
def voice_orchestrator_css() -> FileResponse:
    """Capa 1 Bridge: solo animaciones del botón (no toca layout)."""
    return _archivo_studio("voice-orchestrator.css", "text/css")


@app.get("/header-logo-spec.css")
def header_logo_spec_css() -> FileResponse:
    """Header/Logo PIXEL_PERFECT (aditivo)."""
    return _archivo_studio("header-logo-spec.css", "text/css")


@app.get("/salomon-estructura.css")
def salomon_estructura_css() -> FileResponse:
    """Estructura Salomón: logo/menús/campo/barra/burbujas (maqueta)."""
    return _archivo_studio("salomon-estructura.css", "text/css")


@app.get("/thinking-animation-spec.css")
def thinking_animation_spec_css() -> FileResponse:
    """Thinking motion protocol (aditivo)."""
    return _archivo_studio("thinking-animation-spec.css", "text/css")


@app.get("/salomon-ui-shield.css")
def salomon_ui_shield_css() -> FileResponse:
    """UI Shield: rediseño visual aditivo."""
    return _archivo_studio("salomon-ui-shield.css", "text/css")


@app.get("/camera-v13.css")
def camera_v13_css() -> FileResponse:
    """Cámara Salomón — UI aislada (engine v20)."""
    return _archivo_studio("camera-v13.css", "text/css")


@app.get("/camera-engine.js")
def camera_engine_js() -> FileResponse:
    """MediaStreamManager / CameraEngine v20 — pipeline nativo."""
    return _archivo_studio("camera-engine.js", "application/javascript")


@app.get("/salomon-security-kernel.js")
def salomon_security_kernel_js() -> FileResponse:
    """Salomón Inmortal v23 — sandbox proxy, limiter y telemetría (sobre el Core)."""
    return _archivo_studio("salomon-security-kernel.js", "application/javascript")


@app.get("/camera-v13.js")
def camera_v13_js() -> FileResponse:
    """Cámara Salomón — UI shell sobre CameraEngine (sin Bridge/agente)."""
    return _archivo_studio("camera-v13.js", "application/javascript")


@app.get("/tools/camera_actions.js")
def tools_camera_actions_js() -> FileResponse:
    """Captura UI legacy encapsulada (desconectada; shutter-only activo)."""
    return _archivo_studio("tools/camera_actions.js", "application/javascript")


@app.get("/salomon-ui-shield.js")
def salomon_ui_shield_js() -> FileResponse:
    """UI Shield: interacciones (cámara/voz/burbujas)."""
    return _archivo_studio("salomon-ui-shield.js", "application/javascript")


@app.get("/salomon-fase1.js")
def salomon_fase1_js() -> FileResponse:
    """Fase1 fetch bridge — Memory Cortex (búsqueda solo explícita)."""
    return _archivo_studio("salomon-fase1.js", "application/javascript")


@app.get("/salomon-self-heal.js")
def salomon_self_heal_js() -> FileResponse:
    """Autosaneamiento: evaluateHealth + forceReset + Default Layout."""
    return _archivo_studio("salomon-self-heal.js", "application/javascript")


@app.get("/salomon-orchestrator-bridge.js")
def salomon_orchestrator_bridge_js() -> FileResponse:
    """Capa 1 Bridge: estados + cancelación sobre UI estable."""
    return _archivo_studio("salomon-orchestrator-bridge.js", "application/javascript")


@app.get("/salomon-update.js")
def salomon_update_js() -> FileResponse:
    """CI/CD: auto-actualización PWA desde Render."""
    return _archivo_studio("salomon-update.js", "application/javascript")


@app.get("/standalone-boot.js")
def standalone_boot_js() -> FileResponse:
    return _archivo_studio("standalone-boot.js", "application/javascript")


@app.get("/vision-overlay.js")
def vision_overlay_js() -> FileResponse:
    return _archivo_studio("vision-overlay.js", "application/javascript")


@app.get("/drawers.css")
def drawers_css() -> FileResponse:
    return _archivo_studio("drawers.css", "text/css")


@app.get("/drawers.js")
def drawers_js() -> FileResponse:
    return _archivo_studio("drawers.js", "application/javascript")


@app.get("/sw.js")
@app.get("/service-worker.js")
def service_worker_nativo() -> FileResponse:
    """Service Worker Premium (static/js) — scope '/'."""
    premium = BASE_DIR / "static" / "js" / "service-worker.js"
    if premium.is_file():
        return FileResponse(
            premium,
            media_type="application/javascript",
            headers={
                "Service-Worker-Allowed": "/",
                "Cache-Control": "no-cache",
            },
        )
    resp = _archivo_studio("service-worker.js", "application/javascript")
    if hasattr(resp, "headers"):
        resp.headers["Service-Worker-Allowed"] = "/"
        resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.get("/pwa-nativa.js")
def pwa_nativa_js() -> FileResponse:
    return _archivo_studio("pwa-nativa.js", "application/javascript")


@app.get("/reconexion-perifericos.js")
def reconexion_perifericos_js() -> FileResponse:
    return _archivo_studio("reconexion-perifericos.js", "application/javascript")


@app.get("/api/pwa/estado")
def api_pwa_estado() -> dict:
    return {
        "protocol": "EJECUCION_DESPLIEGUE_FINAL",
        "version": "106.0.0",
        "active": True,
        "manifest": {
            "name": "Salomon AI",
            "short_name": "Salomon",
            "display": "standalone",
            "theme_color": "#000000",
            "ascii_safe": True,
            "permissions": ["camera", "microphone"],
        },
        "service_worker": "/service-worker.js",
        "service_worker_legacy": "/sw.js",
        "cache": "salomon-pwa-v105",
        "core_endpoints": [
            "/api/identidad",
            "/api/inmune",
            "/api/conectividad",
            "/api/auditoria/cruzada",
            "/api/web/arquitecto",
            "/api/eficiencia",
        ],
        "perifericos": "/reconexion-perifericos.js?v=105",
        "permissions_policy": "camera=(self), microphone=(self)",
        "installable": True,
        "owner": "Israel Monta - Salomon AI Studio",
        "external_fetch_passthrough": True,
        "nucleo": "DESPLIEGUE_FINAL",
        "espera_autorizacion_fisica": True,
        "mensaje": "DESPLIEGUE EN CURSO. ESPERANDO ACTIVACIÓN FÍSICA",
        "instruccion_israel": (
            "Abre la PWA, toca la pantalla y otorga permisos de micrófono y cámara."
        ),
    }


@app.get("/api/sce")
def api_sce_estado() -> dict:
    """Sistema de Criterio de Evolución (v100)."""
    from cognicion.evolucion import estado_sce

    return estado_sce()


class SceEvaluarRequest(BaseModel):
    propuesta: str = Field(..., min_length=1, max_length=4000)
    paquete: str | None = None
    autorizado: bool = False


@app.post("/api/sce/evaluar")
def api_sce_evaluar(body: SceEvaluarRequest) -> dict:
    from cognicion.evolucion import analizar_valor

    return analizar_valor(
        body.propuesta,
        contexto={"paquete": body.paquete or "", "autorizado": body.autorizado},
    )


@app.get("/api/evolucion/30x")
def api_evolucion_30x() -> dict:
    """Evolución 30-X — habilidades de vanguardia filtradas por SCE (v101)."""
    from cognicion.evolucion.habilidades_30x import estado_30x

    return estado_30x()


@app.get("/api/comic/estado")
def api_comic_estado() -> dict:
    from cognicion.comic import estado_comic_engine

    return estado_comic_engine()


class ComicProducirRequest(BaseModel):
    titulo: str | None = Field(default=None, max_length=200)
    tema: str | None = Field(default=None, max_length=500)
    persistir: bool = True


@app.post("/api/comic/producir")
def api_comic_producir(body: ComicProducirRequest | None = None) -> dict:
    """Comic_Engine: Guion → Storyboard → Ilustración → Lettering."""
    from cognicion.comic import producir_comic

    body = body or ComicProducirRequest()
    return producir_comic(
        titulo=body.titulo,
        tema=body.tema,
        persistir=body.persistir,
    )


@app.get("/api/sellado")
def api_sellado_final() -> dict:
    """Informe de sellado final pre-despliegue (v103)."""
    import subprocess
    import sys
    from pathlib import Path

    script = Path(__file__).resolve().parent / "scripts" / "sellado_final_v103.py"
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=str(Path(__file__).resolve().parent),
            encoding="utf-8",
            errors="replace",
        )
        import json as _json

        out = proc.stdout or ""
        i = out.find("{")
        payload = _json.loads(out[i:]) if i >= 0 else {"ok": False, "raw": out[-500:]}
        payload["exit_code"] = proc.returncode
        return payload
    except Exception as exc:
        return {
            "ok": False,
            "protocol": "SELLADO_FINAL_DESPLIEGUE_SEGURO",
            "version": "103.0.0",
            "estado": "ERROR_SELLADO",
            "error": f"{type(exc).__name__}: {exc}",
        }


@app.get("/api/auditoria/preflight")
def api_auditoria_preflight() -> dict:
    """Auditoría de integridad y pre-flight (v98)."""
    import subprocess
    import sys
    from pathlib import Path

    script = Path(__file__).resolve().parent / "scripts" / "preflight_audit_v98.py"
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(Path(__file__).resolve().parent),
        )
        import json as _json

        payload = _json.loads(proc.stdout or "{}")
        payload["exit_code"] = proc.returncode
        payload["protocol"] = "AUDITORIA_INTEGRIDAD_PREFLIGHT"
        payload["version"] = "98.0.0"
        payload["estado"] = (
            "OPERATIVO, SIN ERRORES" if payload.get("ok") and proc.returncode == 0 else "CON_HALLAZGOS"
        )
        return payload
    except Exception as exc:
        return {
            "ok": False,
            "protocol": "AUDITORIA_INTEGRIDAD_PREFLIGHT",
            "version": "98.0.0",
            "estado": "ERROR_AUDITORIA",
            "error": f"{type(exc).__name__}: {exc}",
        }


@app.get("/icons.svg")
def icons() -> FileResponse:
    return _archivo_studio("icons.svg", "image/svg+xml")


if STUDIO_DIR.exists():
    assets_dir = STUDIO_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="studio_assets")

# Estáticos públicos (carcasa_base.html y diseño)
_static_public = BASE_DIR / "static"
_static_public.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_public)), name="static_public")

# Archivos multimedia generados / editados
_media_root = ROOT_DIR / "data" / "media"
_media_root.mkdir(parents=True, exist_ok=True)
(_media_root / "generadas").mkdir(exist_ok=True)
(_media_root / "editados").mkdir(exist_ok=True)
(_media_root / "uploads").mkdir(exist_ok=True)
app.mount("/media", StaticFiles(directory=_media_root), name="media_files")

# Montar capas/plugins de forma tolerante (lazy / no tumba el worker).
# Cámara es 100% cliente (JS); no hay init de hardware aquí.
try:
    from cognicion.capas.loader import inicializar_capas as _inicializar_capas

    _inicializar_capas(app)
except Exception as exc:
    _log.exception("capas_import_degradado: %s", exc)


if __name__ == "__main__":
    import uvicorn

    from cognicion.red.tunel import iniciar_tunel_si_habilitado
    from settings import COLSUB_HOST, COLSUB_PORT

    # Render inyecta PORT; local usa COLSUB_PORT o 10000
    port = int(os.environ.get("PORT", COLSUB_PORT or 10000))
    host = os.environ.get("HOST", COLSUB_HOST or "0.0.0.0")
    iniciar_tunel_si_habilitado(port)
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=os.environ.get("RELOAD", "").lower() in ("1", "true", "yes"),
    )
