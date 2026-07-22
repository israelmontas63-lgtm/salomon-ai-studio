"""
Cliente LLM centralizado — proveedores intercambiables (google.genai + OpenAI).
"""

from __future__ import annotations

import os
import traceback
from typing import Any, Callable, Protocol

from settings import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_MODELOS_RESPALDO,
    GEMINI_VISION_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
    LLM_FALLBACK,
    LLM_LOCAL_FALLBACK,
    LLM_TEMPERATURE,
    LLM_TOP_P,
    MODEL_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)

from cognicion.registro import evento, obtener_logger
from cognicion.respuesta_local import respuesta_local_chat

_log = obtener_logger("llm")
_ultimo_uso: dict[str, object] = {}
# Circuit breaker: si Gemini responde 429/limit:0, saltar a Groq unos minutos
_gemini_skip_until: float = 0.0


def _gemini_circuit_abierto() -> bool:
    import time

    return time.monotonic() < float(_gemini_skip_until)


def _gemini_circuit_abrir(segundos: float = 180.0) -> None:
    global _gemini_skip_until
    import time

    _gemini_skip_until = time.monotonic() + max(30.0, float(segundos))
    print(f"[LLM] Gemini circuit OPEN {segundos:.0f}s -> cascada Groq/local", flush=True)


def _gemini_circuit_cerrar() -> None:
    global _gemini_skip_until
    _gemini_skip_until = 0.0

# Tope duro por llamada (ms). Free Tier Render: corto para no matar el proxy (~30s).
_render_free = os.getenv("RENDER_FREE_TIER", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
# Gemini exige deadline >= 10s (API 400 si es menor). Free Tier: 12s + hard cut.
_LLM_HTTP_TIMEOUT_MS = int(
    os.getenv(
        "LLM_HTTP_TIMEOUT_MS",
        "12000" if _render_free else "20000",
    )
    or ("12000" if _render_free else "20000")
)
if _LLM_HTTP_TIMEOUT_MS < 10000:
    _LLM_HTTP_TIMEOUT_MS = 10000  # mínimo impuesto por Google GenAI
# Cuántos modelos Gemini probar (1 en Free = evita N×timeout)
_LLM_MAX_MODELS = int(
    os.getenv("LLM_MAX_MODELS", "1" if _render_free else "3") or "1"
)
# Presupuesto total de la cascada cloud (s) antes de forzar local
_LLM_TOTAL_BUDGET_S = float(
    os.getenv("LLM_TOTAL_BUDGET_S", "18" if _render_free else "45") or "18"
)
# Temperatura estable (0.3–0.5): menos alucinación / basura creativa
try:
    _LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", str(LLM_TEMPERATURE)) or LLM_TEMPERATURE)
except Exception:
    _LLM_TEMPERATURE = float(LLM_TEMPERATURE)
_LLM_TEMPERATURE = max(0.0, min(1.0, _LLM_TEMPERATURE))
try:
    _LLM_TOP_P = float(os.getenv("LLM_TOP_P", str(LLM_TOP_P)) or LLM_TOP_P)
except Exception:
    _LLM_TOP_P = float(LLM_TOP_P)
_LLM_TOP_P = max(0.1, min(1.0, _LLM_TOP_P))
# Historial corto en Free Tier = menos latencia y menos contexto contaminado
_HIST_MAX_TURNS = int(os.getenv("LLM_HIST_MAX_TURNS", "6" if _render_free else "12") or "6")
_HIST_MAX_MSG_CHARS = int(
    os.getenv("LLM_HIST_MAX_MSG_CHARS", "2000" if _render_free else "3500") or "2000"
)
_HIST_MAX_TOTAL_CHARS = int(
    os.getenv("LLM_HIST_MAX_TOTAL_CHARS", "10000" if _render_free else "24000") or "10000"
)
_SYS_PROMPT_MAX = int(os.getenv("LLM_SYS_PROMPT_MAX", "4200" if _render_free else "12000") or "4200")


def _config_generacion() -> dict[str, Any]:
    """Parámetros de muestreo estables para todos los proveedores."""
    return {
        "temperature": float(_LLM_TEMPERATURE),
        "top_p": float(_LLM_TOP_P),
    }


def _preparar_system_instruction(system_instruction: str) -> str:
    """
    Free Tier: recorta el prompt preservando el bloque inicial de Coherencia Estricta.
    """
    sys_inst = (system_instruction or "").strip()
    if not sys_inst:
        return ""
    if len(sys_inst) <= _SYS_PROMPT_MAX:
        return sys_inst
    # Mantener el encabezado (coherencia) + cola de estabilidad si cabe
    head = sys_inst[: max(1800, _SYS_PROMPT_MAX - 900)]
    tail_marker = "[Prompt de Estabilidad"
    idx = sys_inst.find(tail_marker)
    if idx >= 0:
        tail = sys_inst[idx : idx + 800]
        merged = (head.rstrip() + "\n\n…\n\n" + tail).strip()
        if len(merged) > _SYS_PROMPT_MAX:
            merged = merged[: _SYS_PROMPT_MAX - 1] + "…"
        print(
            f"[LLM] system_instruction recortado a {len(merged)} chars (coherencia+estabilidad)",
            flush=True,
        )
        return merged
    out = sys_inst[: _SYS_PROMPT_MAX - 1] + "…"
    print(f"[LLM] system_instruction truncado a {len(out)} chars", flush=True)
    return out


def _env_key(*names: str) -> str:
    """Lee la API key en caliente desde el entorno (no solo al importar settings)."""
    for name in names:
        val = (os.getenv(name) or "").strip()
        if val:
            return val
    # Fallback a settings capturados al boot
    mapping = {
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "GROQ_API_KEY": GROQ_API_KEY,
    }
    for name in names:
        val = (mapping.get(name) or "").strip()
        if val:
            return val
    return ""


def _falta_clave(provider: str) -> Exception:
    from core.error_codes import format_error_response

    msg = (
        f"Falta API key del proveedor '{provider}'. "
        "Configura GEMINI_API_KEY / OPENAI_API_KEY / GROQ_API_KEY en Render Environment."
    )
    exc = RuntimeError(msg)
    pack = format_error_response(
        exc,
        code=42,
        cause=msg,
        hint="api",
        origin=f"cognicion.llm.{provider}",
        audit=True,
        extra_meta={"provider": provider},
    )
    setattr(exc, "salomon_error_pack", pack)
    setattr(exc, "salomon_error_code", 42)
    print(
        f"[LLM] ERROR 42 — sin clave para {provider}. "
        f"GEMINI={bool(_env_key('GEMINI_API_KEY'))} "
        f"OPENAI={bool(_env_key('OPENAI_API_KEY'))} "
        f"GROQ={bool(_env_key('GROQ_API_KEY'))}",
        flush=True,
    )
    return exc


def estado_llm() -> dict[str, Any]:
    """Diagnóstico seguro (sin filtrar secretos) para /api/version o /api/llm/status."""
    try:
        disponible = llm_disponible()
    except Exception:
        disponible = False
    return {
        "provider": MODEL_PROVIDER,
        "fallback": bool(LLM_FALLBACK),
        "local_fallback": bool(LLM_LOCAL_FALLBACK),
        "timeout_ms": _LLM_HTTP_TIMEOUT_MS,
        "max_models": _LLM_MAX_MODELS,
        "budget_s": _LLM_TOTAL_BUDGET_S,
        "temperature": _LLM_TEMPERATURE,
        "top_p": _LLM_TOP_P,
        "hist_max_turns": _HIST_MAX_TURNS,
        "keys": {
            "gemini": bool(_env_key("GEMINI_API_KEY")),
            "openai": bool(_env_key("OPENAI_API_KEY")),
            "groq": bool(_env_key("GROQ_API_KEY")),
        },
        "models": {
            "gemini": GEMINI_MODEL,
            "openai": OPENAI_MODEL,
            "groq": GROQ_MODEL,
        },
        "disponible": disponible,
    }


def recargar_entorno_llm() -> dict[str, Any]:
    """
    Recarga .env (override) + reinicia clientes LLM cacheados.
    No imprime secretos. Útil tras actualizar GEMINI_API_KEY en local/Render.
    """
    from pathlib import Path

    from dotenv import load_dotenv

    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env", override=True)
    load_dotenv(root / "security" / "credentials" / "sbi.env", override=True)

    # Invalidar clientes cacheados para forzar nueva key
    _gemini_circuit_cerrar()
    for nombre, prov in list(_PROVEEDORES.items()):
        if hasattr(prov, "_client"):
            try:
                prov._client = None
            except Exception:
                pass
        if hasattr(prov, "_client_key"):
            try:
                prov._client_key = ""
            except Exception:
                pass

    global _LLM_HTTP_TIMEOUT_MS
    try:
        raw = int(os.getenv("LLM_HTTP_TIMEOUT_MS", str(_LLM_HTTP_TIMEOUT_MS)) or _LLM_HTTP_TIMEOUT_MS)
        _LLM_HTTP_TIMEOUT_MS = max(10000, raw)
    except Exception:
        _LLM_HTTP_TIMEOUT_MS = max(10000, int(_LLM_HTTP_TIMEOUT_MS))

    st = estado_llm()
    st["reloaded"] = True
    st["gemini_key_len"] = len(_env_key("GEMINI_API_KEY"))
    st["gemini_circuit_open"] = _gemini_circuit_abierto()
    print(
        f"[LLM] entorno recargado gemini_key={bool(_env_key('GEMINI_API_KEY'))} "
        f"timeout_ms={_LLM_HTTP_TIMEOUT_MS}",
        flush=True,
    )
    return st



def _anclar_error_proveedor(exc: Exception, *, provider: str) -> Exception:
    """
    Clasifica el fallo con el diccionario oficial (core.error_codes)
    y ancla la estructura estandarizada en la excepción para el cerebro/chat.
    """
    try:
        from core.error_codes import format_error_response, get_error_info

        pack = format_error_response(
            exc,
            hint="api",
            origin=f"cognicion.llm.{provider}",
            audit=True,
            extra_meta={"provider": provider},
        )
        info = get_error_info(pack.get("error_codigo", 49))
        setattr(exc, "salomon_error_pack", pack)
        setattr(exc, "salomon_error_code", int(info["code"]))
        evento(
            _log,
            "llm_provider_error_coded",
            provider=provider,
            error_codigo=info["code"],
            error_rango=info["range"],
            error=type(exc).__name__,
            detail=str(exc)[:240],
        )
        print(
            f"[LLM] {provider} -> Error {info['code']}: {type(exc).__name__}: {str(exc)[:200]}",
            flush=True,
        )
        print(traceback.format_exc()[-1200:], flush=True)
    except Exception as bridge_exc:
        evento(
            _log,
            "llm_error_codes_bridge_fail",
            provider=provider,
            error=type(bridge_exc).__name__,
        )
        print(
            f"[LLM] bridge_fail {provider}: {type(exc).__name__}: {exc}\n"
            f"{traceback.format_exc()[-800:]}",
            flush=True,
        )
    return exc


class ModelProvider(Protocol):
    """Contrato para proveedores de modelos."""

    nombre: str

    def disponible(self) -> bool: ...

    def chat_con_historial(
        self,
        mensaje: str,
        historial: list[dict],
        system_instruction: str,
        model_name: str | None = None,
    ) -> str: ...

    def generar_texto(self, prompt: str, model_name: str | None = None) -> str: ...

    def analizar_imagen(
        self,
        prompt: str,
        imagen_bytes: bytes,
        mime_type: str = "image/png",
        model_name: str | None = None,
    ) -> str: ...


def _finite_chars(text: Any, limit: int) -> str:
    if text is None:
        return ""
    if isinstance(text, bytes):
        raw = text.decode("utf-8", errors="replace")
    else:
        raw = str(text)
    raw = raw.strip()
    if not raw:
        return ""
    if len(raw) > limit:
        return raw[: limit - 1] + "…"
    return raw


def _sanitizar_historial_chat(
    historial: list[dict],
    mensaje: str,
    *,
    role_assistant: str = "model",
    max_turns: int = 16,
    max_msg_chars: int = 3_500,
    max_total_chars: int = 28_000,
) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    """
    Cemento de historial para proveedores LLM:
    - roles solo user / model|assistant
    - sin vacíos / nulos
    - roles estrictamente alternados
    - tope de caracteres (anti overflow de contexto)
    """
    meta: dict[str, Any] = {
        "turns_in": len(historial or []),
        "dropped_empty": 0,
        "merged_same_role": 0,
        "truncated": False,
        "capped_total": False,
    }
    msg = _finite_chars(mensaje, max_msg_chars * 3)  # turno actual puede ir enriquecido
    if not msg:
        msg = "…"

    cleaned: list[dict[str, Any]] = []
    for item in historial or []:
        if not isinstance(item, dict):
            meta["dropped_empty"] += 1
            continue
        raw_role = str(item.get("role") or "").strip().lower()
        if raw_role in ("user", "usuario"):
            role = "user"
        elif raw_role in ("model", "assistant", "asistente"):
            role = role_assistant
        else:
            meta["dropped_empty"] += 1
            continue
        parts = item.get("parts")
        if isinstance(parts, list) and parts:
            texto = _finite_chars(parts[0], max_msg_chars)
        else:
            texto = _finite_chars(item.get("content") or item.get("contenido"), max_msg_chars)
        if not texto:
            meta["dropped_empty"] += 1
            continue
        if cleaned and cleaned[-1]["role"] == role:
            cleaned[-1]["parts"][0] = _finite_chars(
                cleaned[-1]["parts"][0] + "\n" + texto, max_msg_chars
            )
            meta["merged_same_role"] += 1
        else:
            cleaned.append({"role": role, "parts": [texto]})

    # Debe empezar en user (Gemini)
    while cleaned and cleaned[0]["role"] != "user":
        cleaned.pop(0)
        meta["truncated"] = True

    # Máximo N pares (user+assistant)
    max_msgs = max(2, int(max_turns) * 2)
    if len(cleaned) > max_msgs:
        cleaned = cleaned[-max_msgs:]
        meta["truncated"] = True
        while cleaned and cleaned[0]["role"] != "user":
            cleaned.pop(0)

    # No terminar en user: el mensaje actual se añade aparte
    if cleaned and cleaned[-1]["role"] == "user":
        cleaned.pop()
        meta["truncated"] = True

    # Presupuesto total
    total = sum(len(x["parts"][0]) for x in cleaned) + len(msg)
    while cleaned and total > max_total_chars:
        dropped = cleaned.pop(0)
        total -= len(dropped["parts"][0])
        meta["capped_total"] = True
        meta["truncated"] = True
        while cleaned and cleaned[0]["role"] != "user":
            cleaned.pop(0)

    meta["turns_out"] = len(cleaned)
    meta["chars_out"] = total
    return cleaned, msg, meta


def _historial_a_gemini_contents(historial: list[dict], mensaje: str) -> list:
    from google.genai import types

    cleaned, msg, meta = _sanitizar_historial_chat(
        historial,
        mensaje,
        role_assistant="model",
        max_turns=_HIST_MAX_TURNS,
        max_msg_chars=_HIST_MAX_MSG_CHARS,
        max_total_chars=_HIST_MAX_TOTAL_CHARS,
    )
    evento(
        _log,
        "llm_payload_gemini",
        turns=meta.get("turns_out"),
        chars=meta.get("chars_out"),
        dropped_empty=meta.get("dropped_empty"),
        merged=meta.get("merged_same_role"),
        truncated=meta.get("truncated"),
        capped=meta.get("capped_total"),
    )
    contents: list = []
    for item in cleaned:
        contents.append(
            types.Content(
                role=item["role"],
                parts=[types.Part.from_text(text=item["parts"][0])],
            )
        )
    contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=msg)])
    )
    if not contents:
        contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=msg or "Hola")])
        )
    return contents


class GeminiProvider:
    nombre = "gemini"

    def __init__(self) -> None:
        self._client = None
        self._client_key: str = ""

    def _cliente(self):
        key = _env_key("GEMINI_API_KEY")
        if not key:
            raise _falta_clave("gemini")
        if self._client is None or self._client_key != key:
            from google import genai
            from google.genai import types

            opts = None
            try:
                retry = None
                try:
                    # 1 intento: fallar rápido en 429 y cascada a Groq (evita Error 49 por latencia)
                    retry = types.HttpRetryOptions(attempts=1)
                except Exception:
                    retry = None
                kwargs_opts: dict[str, Any] = {"timeout": int(_LLM_HTTP_TIMEOUT_MS)}
                if retry is not None:
                    kwargs_opts["retry_options"] = retry
                opts = types.HttpOptions(**kwargs_opts)
            except Exception:
                opts = None
            kwargs: dict[str, Any] = {"api_key": key}
            if opts is not None:
                kwargs["http_options"] = opts
            self._client = genai.Client(**kwargs)
            self._client_key = key
            print(
                f"[LLM] Gemini client listo (key_len={len(key)} timeout_ms={_LLM_HTTP_TIMEOUT_MS})",
                flush=True,
            )
        return self._client

    def disponible(self) -> bool:
        if _gemini_circuit_abierto():
            return False
        return bool(_env_key("GEMINI_API_KEY"))

    def _modelos_a_probar(self, model_name: str | None) -> list[str]:
        principal = model_name or GEMINI_MODEL
        # Free Tier: preferir lite si no hay override (más rápido, menos Error 49)
        if _render_free and not model_name:
            lite = "gemini-2.0-flash-lite"
            if lite not in (principal or ""):
                principal = lite
        vistos: set[str] = set()
        orden: list[str] = []
        for modelo in [principal, *GEMINI_MODELOS_RESPALDO]:
            if modelo and modelo not in vistos:
                vistos.add(modelo)
                orden.append(modelo)
        return orden[: max(1, _LLM_MAX_MODELS)]

    def chat_con_historial(
        self,
        mensaje: str,
        historial: list[dict],
        system_instruction: str,
        model_name: str | None = None,
    ) -> str:
        from google.genai import types

        if not self.disponible():
            raise _falta_clave("gemini")
        client = self._cliente()
        # Free Tier: system prompt corto = menos latencia; preserva Coherencia Estricta
        sys_inst = _preparar_system_instruction(system_instruction)
        contents = _historial_a_gemini_contents(historial, mensaje)
        ultimo_error: Exception | None = None
        gen = _config_generacion()

        for modelo in self._modelos_a_probar(model_name):
            try:
                print(
                    f"[LLM] Gemini generate_content model={modelo} turns={len(contents)} "
                    f"temp={gen['temperature']}",
                    flush=True,
                )
                cfg_kwargs: dict[str, Any] = {
                    "system_instruction": sys_inst or None,
                    "temperature": gen["temperature"],
                    "top_p": gen["top_p"],
                }
                try:
                    cfg_kwargs["http_options"] = types.HttpOptions(
                        timeout=int(_LLM_HTTP_TIMEOUT_MS)
                    )
                except Exception:
                    pass

                def _call():
                    return client.models.generate_content(
                        model=modelo,
                        contents=contents,
                        config=types.GenerateContentConfig(**cfg_kwargs),
                    )

                # Timeout duro en hilo (HttpOptions a veces no corta a tiempo en Render)
                import concurrent.futures

                # Google GenAI exige deadline >= 10s; nunca cortar antes.
                hard_s = max(10.0, float(_LLM_HTTP_TIMEOUT_MS) / 1000.0)
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    fut = pool.submit(_call)
                    try:
                        respuesta = fut.result(timeout=hard_s)
                    except concurrent.futures.TimeoutError as te:
                        raise TimeoutError(
                            f"gemini_hard_timeout_{hard_s:.0f}s model={modelo}"
                        ) from te

                texto = (respuesta.text or "").strip()
                if texto:
                    return texto
                print(f"[LLM] Gemini respuesta vacía model={modelo}", flush=True)
            except Exception as exc:
                ultimo_error = _anclar_error_proveedor(exc, provider="gemini")
                _marcar_cuota_gemini(exc)
                evento(
                    _log,
                    "llm_gemini_exception",
                    modelo=modelo,
                    error=type(exc).__name__,
                    detail=str(exc)[:400],
                    contents_n=len(contents),
                    error_codigo=getattr(exc, "salomon_error_code", None),
                )
                if _es_error_recuperable(exc):
                    evento(
                        _log,
                        "gemini_modelo_fallido",
                        modelo=modelo,
                        error=type(exc).__name__,
                    )
                    continue
                # En Free Tier no abortar: dejar que la cascada pruebe Groq/local
                if _render_free:
                    continue
                raise

        if ultimo_error:
            raise ultimo_error
        return ""

    def generar_texto(self, prompt: str, model_name: str | None = None) -> str:
        if not self.disponible():
            raise _falta_clave("gemini")
        client = self._cliente()
        ultimo_error: Exception | None = None

        for modelo in self._modelos_a_probar(model_name):
            try:
                respuesta = client.models.generate_content(
                    model=modelo,
                    contents=prompt,
                )
                texto = (respuesta.text or "").strip()
                if texto:
                    return texto
            except Exception as exc:
                ultimo_error = _anclar_error_proveedor(exc, provider="gemini")
                _marcar_cuota_gemini(exc)
                if _es_error_recuperable(exc):
                    continue
                raise

        if ultimo_error:
            raise ultimo_error
        return ""

    def analizar_imagen(
        self,
        prompt: str,
        imagen_bytes: bytes,
        mime_type: str = "image/png",
        model_name: str | None = None,
    ) -> str:
        from google.genai import types

        client = self._cliente()
        respuesta = client.models.generate_content(
            model=model_name or GEMINI_VISION_MODEL,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(data=imagen_bytes, mime_type=mime_type),
                    ],
                )
            ],
        )
        return (respuesta.text or "").strip()


def _mensajes_openai_style(
    mensaje: str,
    historial: list[dict],
    system_instruction: str,
    *,
    label: str = "openai",
) -> list[dict[str, str]]:
    cleaned, msg, meta = _sanitizar_historial_chat(
        historial,
        mensaje,
        role_assistant="assistant",
        max_turns=_HIST_MAX_TURNS,
        max_msg_chars=_HIST_MAX_MSG_CHARS,
        max_total_chars=_HIST_MAX_TOTAL_CHARS,
    )
    evento(
        _log,
        f"llm_payload_{label}",
        turns=meta.get("turns_out"),
        chars=meta.get("chars_out"),
        truncated=meta.get("truncated"),
        capped=meta.get("capped_total"),
        dropped_empty=meta.get("dropped_empty"),
        merged=meta.get("merged_same_role"),
    )
    sys_inst = _preparar_system_instruction(system_instruction)
    mensajes: list[dict[str, str]] = [
        {"role": "system", "content": sys_inst},
    ]
    for item in cleaned:
        mensajes.append({"role": item["role"], "content": item["parts"][0]})
    mensajes.append({"role": "user", "content": msg})
    return mensajes


class OpenAIProvider:
    nombre = "openai"

    def disponible(self) -> bool:
        return bool(_env_key("OPENAI_API_KEY"))

    def _cliente(self):
        from openai import OpenAI

        key = _env_key("OPENAI_API_KEY")
        if not key:
            raise _falta_clave("openai")
        kwargs: dict[str, Any] = {
            "api_key": key,
            "timeout": max(5.0, float(_LLM_HTTP_TIMEOUT_MS) / 1000.0),
        }
        base = (os.getenv("OPENAI_BASE_URL") or OPENAI_BASE_URL or "").strip()
        if base:
            kwargs["base_url"] = base
        return OpenAI(**kwargs)

    def _mensajes_openai(
        self,
        mensaje: str,
        historial: list[dict],
        system_instruction: str,
    ) -> list[dict[str, str]]:
        return _mensajes_openai_style(
            mensaje, historial, system_instruction, label="openai"
        )

    def chat_con_historial(
        self,
        mensaje: str,
        historial: list[dict],
        system_instruction: str,
        model_name: str | None = None,
    ) -> str:
        if not self.disponible():
            raise _falta_clave("openai")
        try:
            client = self._cliente()
            gen = _config_generacion()
            print(
                f"[LLM] OpenAI chat.completions.create temp={gen['temperature']}",
                flush=True,
            )
            respuesta = client.chat.completions.create(
                model=model_name or OPENAI_MODEL,
                messages=self._mensajes_openai(mensaje, historial, system_instruction),
                temperature=gen["temperature"],
                top_p=gen["top_p"],
            )
            return (respuesta.choices[0].message.content or "").strip()
        except Exception as exc:
            raise _anclar_error_proveedor(exc, provider="openai") from exc

    def generar_texto(self, prompt: str, model_name: str | None = None) -> str:
        if not self.disponible():
            raise _falta_clave("openai")
        try:
            client = self._cliente()
            gen = _config_generacion()
            respuesta = client.chat.completions.create(
                model=model_name or OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=gen["temperature"],
                top_p=gen["top_p"],
            )
            return (respuesta.choices[0].message.content or "").strip()
        except Exception as exc:
            raise _anclar_error_proveedor(exc, provider="openai") from exc

    def analizar_imagen(
        self,
        prompt: str,
        imagen_bytes: bytes,
        mime_type: str = "image/png",
        model_name: str | None = None,
    ) -> str:
        import base64

        client = self._cliente()
        imagen_b64 = base64.b64encode(imagen_bytes).decode("ascii")
        respuesta = client.chat.completions.create(
            model=model_name or OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{imagen_b64}",
                            },
                        },
                    ],
                }
            ],
        )
        return (respuesta.choices[0].message.content or "").strip()


class GroqProvider:
    """Groq — API compatible con OpenAI, gratis sin tarjeta (console.groq.com)."""

    nombre = "groq"

    def disponible(self) -> bool:
        return bool(_env_key("GROQ_API_KEY"))

    def _cliente(self):
        from openai import OpenAI

        key = _env_key("GROQ_API_KEY")
        if not key:
            raise _falta_clave("groq")
        return OpenAI(
            api_key=key,
            base_url="https://api.groq.com/openai/v1",
            timeout=max(5.0, float(_LLM_HTTP_TIMEOUT_MS) / 1000.0),
        )

    def _mensajes_openai(
        self,
        mensaje: str,
        historial: list[dict],
        system_instruction: str,
    ) -> list[dict[str, str]]:
        return _mensajes_openai_style(
            mensaje, historial, system_instruction, label="groq"
        )

    def chat_con_historial(
        self,
        mensaje: str,
        historial: list[dict],
        system_instruction: str,
        model_name: str | None = None,
    ) -> str:
        if not self.disponible():
            raise _falta_clave("groq")
        try:
            client = self._cliente()
            gen = _config_generacion()
            print(
                f"[LLM] Groq chat.completions.create temp={gen['temperature']}",
                flush=True,
            )
            respuesta = client.chat.completions.create(
                model=model_name or GROQ_MODEL,
                messages=self._mensajes_openai(mensaje, historial, system_instruction),
                temperature=gen["temperature"],
                top_p=gen["top_p"],
            )
            return (respuesta.choices[0].message.content or "").strip()
        except Exception as exc:
            raise _anclar_error_proveedor(exc, provider="groq") from exc

    def generar_texto(self, prompt: str, model_name: str | None = None) -> str:
        if not self.disponible():
            raise _falta_clave("groq")
        try:
            client = self._cliente()
            gen = _config_generacion()
            respuesta = client.chat.completions.create(
                model=model_name or GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=gen["temperature"],
                top_p=gen["top_p"],
            )
            return (respuesta.choices[0].message.content or "").strip()
        except Exception as exc:
            raise _anclar_error_proveedor(exc, provider="groq") from exc

    def analizar_imagen(
        self,
        prompt: str,
        imagen_bytes: bytes,
        mime_type: str = "image/png",
        model_name: str | None = None,
    ) -> str:
        raise NotImplementedError("Groq no soporta visión en este proveedor")


class LocalProvider:
    """Respaldo sin nube — usa conectores y memoria ya enriquecidas."""

    nombre = "local"

    def disponible(self) -> bool:
        return LLM_LOCAL_FALLBACK

    def chat_con_historial(
        self,
        mensaje: str,
        historial: list[dict],
        system_instruction: str,
        model_name: str | None = None,
    ) -> str:
        return respuesta_local_chat(mensaje, historial, system_instruction)

    def generar_texto(self, prompt: str, model_name: str | None = None) -> str:
        return respuesta_local_chat(prompt, [], "")

    def analizar_imagen(
        self,
        prompt: str,
        imagen_bytes: bytes,
        mime_type: str = "image/png",
        model_name: str | None = None,
    ) -> str:
        return "Análisis visual no disponible sin motor en la nube. Describe la imagen en texto."


_PROVEEDORES: dict[str, ModelProvider] = {
    "gemini": GeminiProvider(),
    "groq": GroqProvider(),
    "openai": OpenAIProvider(),
    "local": LocalProvider(),
}


def registrar_proveedor(proveedor: ModelProvider) -> None:
    _PROVEEDORES[proveedor.nombre] = proveedor


def listar_proveedores() -> list[str]:
    return list(_PROVEEDORES.keys())


def obtener_proveedor(nombre: str | None = None) -> ModelProvider:
    clave = (nombre or MODEL_PROVIDER or "gemini").strip().lower()
    if clave not in _PROVEEDORES:
        clave = "gemini"
    proveedor = _PROVEEDORES[clave]
    if proveedor.disponible():
        return proveedor
    for alterno in listar_proveedores():
        if alterno == clave:
            continue
        candidato = _PROVEEDORES.get(alterno)
        if candidato and candidato.disponible():
            evento(
                _log,
                "proveedor_alterno",
                preferido=clave,
                activo=alterno,
            )
            return candidato
    return proveedor


def _es_error_recuperable(exc: Exception) -> bool:
    texto = str(exc).lower()
    codigo = getattr(exc, "code", None)
    status = getattr(exc, "status_code", None)
    if codigo in (429, "429", 404, "404", 401, "401", 503, "503"):
        return True
    if status in (429, 404, 401, 503, 500):
        return True
    nombre = type(exc).__name__.lower()
    if any(x in nombre for x in ("notfound", "ratelimit", "authentication", "apiconnection")):
        return True
    return any(
        x in texto
        for x in (
            "quota",
            "429",
            "404",
            "not found",
            "resource_exhausted",
            "resourceexhausted",
            "rate limit",
            "too many requests",
            "invalid_api_key",
            "incorrect api key",
            "does not exist",
            "model_not_found",
            "deadline",
            "invalid_argument",
            "too short",
            "timeout",
        )
    )


def _marcar_cuota_gemini(exc: Exception) -> None:
    texto = str(exc).lower()
    if any(
        x in texto
        for x in ("429", "quota", "resource_exhausted", "resourceexhausted", "rate limit")
    ):
        _gemini_circuit_abrir(180.0)


def _proveedor_respaldo(actual: str) -> ModelProvider | None:
    for nombre in listar_proveedores():
        if nombre == actual:
            continue
        proveedor = _PROVEEDORES.get(nombre)
        if proveedor and proveedor.disponible():
            return proveedor
    return None


def _registrar_uso(
    proveedor: str,
    *,
    fallback: bool = False,
    error_previo: str | None = None,
) -> None:
    _ultimo_uso.clear()
    _ultimo_uso.update(
        {
            "proveedor": proveedor,
            "fallback": fallback,
            "error_previo": error_previo,
        }
    )


def ultimo_uso_llm() -> dict[str, object]:
    return dict(_ultimo_uso)


def proveedor_respaldo_disponible() -> str | None:
    principal = obtener_proveedor().nombre
    respaldo = _proveedor_respaldo(principal)
    return respaldo.nombre if respaldo else None


def _orden_fallback(desde: str) -> list[str]:
    # Cadena oficial Render: Gemini → Groq → OpenAI → local
    preferidos = [desde, "gemini", "groq", "openai", "local"]
    orden: list[str] = []
    for nombre in preferidos:
        if nombre not in orden:
            orden.append(nombre)
    for nombre in listar_proveedores():
        if nombre not in orden:
            orden.append(nombre)
    return orden



def _ejecutar_con_respaldo(ejecutar: Callable[[ModelProvider], str]) -> str:
    import time

    t0 = time.monotonic()
    principal = obtener_proveedor()

    def _agotado() -> bool:
        return (time.monotonic() - t0) >= float(_LLM_TOTAL_BUDGET_S)

    if not LLM_FALLBACK:
        try:
            resultado = ejecutar(principal)
            _registrar_uso(principal.nombre)
            return resultado
        except Exception as exc:
            ultimo = _anclar_error_proveedor(exc, provider=principal.nombre)
            local = _PROVEEDORES.get("local")
            if local is not None:
                try:
                    print("[LLM] fallback-off -> local de emergencia", flush=True)
                    texto = ejecutar(local)
                    if texto:
                        _registrar_uso("local", fallback=True, error_previo=type(exc).__name__)
                        return texto
                except Exception:
                    pass
            raise ultimo

    ultimo_error: Exception | None = None
    # Free Tier: Gemini → Groq (rápido) → local. OpenAI al final (más lento).
    orden = _orden_fallback(principal.nombre)
    if _render_free:
        prefer = [principal.nombre, "gemini", "groq", "local", "openai"]
        orden = []
        for n in prefer:
            if n not in orden:
                orden.append(n)

    for indice, nombre in enumerate(orden):
        if nombre != "local" and _agotado():
            print(
                f"[LLM] presupuesto {_LLM_TOTAL_BUDGET_S}s agotado — salto a local",
                flush=True,
            )
            break
        proveedor = _PROVEEDORES.get(nombre)
        if proveedor is None:
            continue
        if nombre != "local" and not proveedor.disponible():
            print(f"[LLM] skip {nombre}: sin API key", flush=True)
            continue
        if nombre == "local" and not LLM_LOCAL_FALLBACK:
            continue
        try:
            print(
                f"[LLM] intento provider={nombre} t+{time.monotonic()-t0:.1f}s",
                flush=True,
            )
            resultado = ejecutar(proveedor)
            if not resultado and nombre != "local":
                continue
            _registrar_uso(
                proveedor.nombre,
                fallback=indice > 0,
                error_previo=type(ultimo_error).__name__ if ultimo_error else None,
            )
            if indice > 0:
                evento(
                    _log,
                    "fallback_proveedor",
                    de=principal.nombre,
                    a=proveedor.nombre,
                    error=type(ultimo_error).__name__ if ultimo_error else None,
                )
            return resultado
        except NotImplementedError as exc:
            ultimo_error = _anclar_error_proveedor(exc, provider=nombre)
            continue
        except Exception as exc:
            ultimo_error = _anclar_error_proveedor(exc, provider=nombre)
            evento(
                _log,
                "proveedor_fallido",
                proveedor=nombre,
                error=type(exc).__name__,
                error_codigo=getattr(exc, "salomon_error_code", None),
            )
            continue

    local = _PROVEEDORES.get("local")
    if local is not None:
        try:
            print("[LLM] ultimo recurso local tras fallos/timeout cloud", flush=True)
            texto = ejecutar(local)
            if texto:
                _registrar_uso(
                    "local",
                    fallback=True,
                    error_previo=type(ultimo_error).__name__ if ultimo_error else None,
                )
                return texto
        except Exception as exc:
            ultimo_error = _anclar_error_proveedor(exc, provider="local")

    if ultimo_error:
        raise ultimo_error
    return respuesta_local_chat("", [], "")


def llm_disponible() -> bool:
    if LLM_LOCAL_FALLBACK:
        return True
    return any(p.disponible() for nombre, p in _PROVEEDORES.items() if nombre != "local")


def gemini_disponible() -> bool:
    """Indica si Gemini tiene clave configurada."""
    return _PROVEEDORES["gemini"].disponible()


def _modelo_para_proveedor(proveedor: ModelProvider, model_name: str | None) -> str | None:
    """
    Enruta el model_name correcto por proveedor:
    - Gemini: siempre un id gemini-* (p.ej. gemini-2.0-flash)
    - Groq/OpenAI: NUNCA reenviar nombres Gemini (evita NotFoundError en fallback)
    """
    nombre = proveedor.nombre
    raw = (model_name or "").strip()
    m = raw.lower()

    if nombre == "gemini":
        # UI → motor: garantizar nombre Gemini válido hacia la API
        if raw and ("gemini" in m or m.startswith("models/")):
            return raw
        return GEMINI_MODEL

    if not raw:
        return None

    if nombre == "openai":
        if m.startswith(("gpt-", "o1", "o3", "o4", "chatgpt")):
            return raw
        return None
    if nombre == "groq":
        if any(x in m for x in ("llama", "mixtral", "gemma", "qwen", "deepseek")):
            return raw
        return None
    return None


def chat_con_historial(
    mensaje: str,
    historial: list[dict],
    system_instruction: str,
    model_name: str | None = None,
) -> str:
    return _ejecutar_con_respaldo(
        lambda proveedor: proveedor.chat_con_historial(
            mensaje,
            historial,
            system_instruction,
            _modelo_para_proveedor(proveedor, model_name),
        )
    )


def generar_texto(prompt: str, model_name: str | None = None) -> str:
    return _ejecutar_con_respaldo(
        lambda proveedor: proveedor.generar_texto(
            prompt, _modelo_para_proveedor(proveedor, model_name)
        )
    )


def analizar_imagen_gemini(
    prompt: str,
    imagen_bytes: bytes,
    mime_type: str = "image/png",
    model_name: str | None = None,
) -> str:
    return _ejecutar_con_respaldo(
        lambda proveedor: proveedor.analizar_imagen(
            prompt,
            imagen_bytes,
            mime_type,
            _modelo_para_proveedor(proveedor, model_name),
        )
    )
