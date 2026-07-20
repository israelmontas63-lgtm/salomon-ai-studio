"""
Cliente LLM centralizado — proveedores intercambiables (google.genai + OpenAI).
"""

from __future__ import annotations

from typing import Callable, Protocol

from settings import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_MODELOS_RESPALDO,
    GEMINI_VISION_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
    LLM_FALLBACK,
    LLM_LOCAL_FALLBACK,
    MODEL_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)

from cognicion.registro import evento, obtener_logger
from cognicion.respuesta_local import respuesta_local_chat

_log = obtener_logger("llm")
_ultimo_uso: dict[str, object] = {}


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


def _historial_a_gemini_contents(historial: list[dict], mensaje: str) -> list:
    from google.genai import types

    contents: list = []
    for item in historial:
        rol = "user" if item.get("role") == "user" else "model"
        parts = item.get("parts") or []
        texto = str(parts[0]) if parts else ""
        if not texto:
            continue
        contents.append(
            types.Content(role=rol, parts=[types.Part.from_text(text=texto)])
        )
    contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=mensaje)])
    )
    return contents


class GeminiProvider:
    nombre = "gemini"

    def __init__(self) -> None:
        self._client = None

    def _cliente(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=GEMINI_API_KEY)
        return self._client

    def disponible(self) -> bool:
        return bool(GEMINI_API_KEY)

    def _modelos_a_probar(self, model_name: str | None) -> list[str]:
        principal = model_name or GEMINI_MODEL
        vistos: set[str] = set()
        orden: list[str] = []
        for modelo in [principal, *GEMINI_MODELOS_RESPALDO]:
            if modelo and modelo not in vistos:
                vistos.add(modelo)
                orden.append(modelo)
        return orden

    def chat_con_historial(
        self,
        mensaje: str,
        historial: list[dict],
        system_instruction: str,
        model_name: str | None = None,
    ) -> str:
        from google.genai import types

        client = self._cliente()
        contents = _historial_a_gemini_contents(historial, mensaje)
        ultimo_error: Exception | None = None

        for modelo in self._modelos_a_probar(model_name):
            try:
                respuesta = client.models.generate_content(
                    model=modelo,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                    ),
                )
                texto = (respuesta.text or "").strip()
                if texto:
                    return texto
            except Exception as exc:
                ultimo_error = exc
                if _es_error_recuperable(exc):
                    evento(_log, "gemini_modelo_fallido", modelo=modelo, error=type(exc).__name__)
                    continue
                raise

        if ultimo_error:
            raise ultimo_error
        return ""

    def generar_texto(self, prompt: str, model_name: str | None = None) -> str:
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
                ultimo_error = exc
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


class OpenAIProvider:
    nombre = "openai"

    def disponible(self) -> bool:
        return bool(OPENAI_API_KEY)

    def _cliente(self):
        from openai import OpenAI

        kwargs: dict[str, str] = {"api_key": OPENAI_API_KEY}
        if OPENAI_BASE_URL:
            kwargs["base_url"] = OPENAI_BASE_URL
        return OpenAI(**kwargs)

    def _mensajes_openai(
        self,
        mensaje: str,
        historial: list[dict],
        system_instruction: str,
    ) -> list[dict[str, str]]:
        mensajes: list[dict[str, str]] = [
            {"role": "system", "content": system_instruction},
        ]
        for item in historial:
            rol = "user" if item.get("role") == "user" else "assistant"
            parts = item.get("parts") or []
            if parts:
                mensajes.append({"role": rol, "content": str(parts[0])})
        mensajes.append({"role": "user", "content": mensaje})
        return mensajes

    def chat_con_historial(
        self,
        mensaje: str,
        historial: list[dict],
        system_instruction: str,
        model_name: str | None = None,
    ) -> str:
        client = self._cliente()
        respuesta = client.chat.completions.create(
            model=model_name or OPENAI_MODEL,
            messages=self._mensajes_openai(mensaje, historial, system_instruction),
        )
        return (respuesta.choices[0].message.content or "").strip()

    def generar_texto(self, prompt: str, model_name: str | None = None) -> str:
        client = self._cliente()
        respuesta = client.chat.completions.create(
            model=model_name or OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return (respuesta.choices[0].message.content or "").strip()

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
        return bool(GROQ_API_KEY)

    def _cliente(self):
        from openai import OpenAI

        return OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )

    def _mensajes_openai(
        self,
        mensaje: str,
        historial: list[dict],
        system_instruction: str,
    ) -> list[dict[str, str]]:
        mensajes: list[dict[str, str]] = [
            {"role": "system", "content": system_instruction},
        ]
        for item in historial:
            rol = "user" if item.get("role") == "user" else "assistant"
            parts = item.get("parts") or []
            if parts:
                mensajes.append({"role": rol, "content": str(parts[0])})
        mensajes.append({"role": "user", "content": mensaje})
        return mensajes

    def chat_con_historial(
        self,
        mensaje: str,
        historial: list[dict],
        system_instruction: str,
        model_name: str | None = None,
    ) -> str:
        client = self._cliente()
        respuesta = client.chat.completions.create(
            model=model_name or GROQ_MODEL,
            messages=self._mensajes_openai(mensaje, historial, system_instruction),
        )
        return (respuesta.choices[0].message.content or "").strip()

    def generar_texto(self, prompt: str, model_name: str | None = None) -> str:
        client = self._cliente()
        respuesta = client.chat.completions.create(
            model=model_name or GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return (respuesta.choices[0].message.content or "").strip()

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
        )
    )


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
    principal = obtener_proveedor()
    if not LLM_FALLBACK:
        resultado = ejecutar(principal)
        _registrar_uso(principal.nombre)
        return resultado

    ultimo_error: Exception | None = None
    for indice, nombre in enumerate(_orden_fallback(principal.nombre)):
        proveedor = _PROVEEDORES.get(nombre)
        if proveedor is None:
            continue
        if nombre != "local" and not proveedor.disponible():
            continue
        if nombre == "local" and not LLM_LOCAL_FALLBACK:
            continue
        try:
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
            ultimo_error = exc
            continue
        except Exception as exc:
            ultimo_error = exc
            if not _es_error_recuperable(exc) and nombre != "local":
                raise
            evento(
                _log,
                "proveedor_fallido",
                proveedor=nombre,
                error=type(exc).__name__,
            )
            continue

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
