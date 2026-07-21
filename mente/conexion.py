# -*- coding: utf-8 -*-
"""
Conexión cerebral total — unifica voz, visión, memoria y razonamiento
en un solo flujo hacia SalomonAI (cerebro).
"""

from __future__ import annotations

from typing import Any

from mente.arquitectura import mapa_mente
from mente.hilos import clasificar_area, contexto_hilo, registrar_turno
from mente.herramientas_perifericas import busqueda_web_si_autorizada, log_mente
from mente.protocolo_inicio import protocolo_inicio


def conexion_cerebral_estado() -> dict[str, Any]:
    from config import estado_nucleo_perceptivo

    perceptivo = estado_nucleo_perceptivo()
    mapa = mapa_mente()
    ok = bool(perceptivo.get("ok")) and bool(mapa.get("areas"))
    return {
        "ok": ok,
        "conexion": "COMPLETADA" if ok else "PARCIAL",
        "mensaje": (
            "Conexión cerebral completada — Salomón es una sola entidad unificada."
            if ok
            else "Conexión cerebral parcial — revisar config/ y mente/"
        ),
        "mapa": mapa,
        "perceptivo": perceptivo,
        "principio": "razonamiento_sobre_busqueda",
        "audio_al_cerebro": True,
        "hilos_con_contexto": True,
    }


def procesar_unificado(
    mensaje: str,
    *,
    session_id: str,
    salomon: Any,
    lat: float | None = None,
    lon: float | None = None,
    imagen_base64: str | None = None,
    imagen_mime: str = "image/png",
    error_consola: str | None = None,
    autonomo: bool = False,
) -> Any:
    """
    Entrada única: clasifica área semántica → contexto de hilo → cerebro.
    Búsqueda web solo vía periféricos autorizados (no interviene sola).
    """
    area = clasificar_area(mensaje, tiene_imagen=bool(imagen_base64))
    registrar_turno(session_id, rol="usuario", texto=mensaje, area=area)
    log_mente("turno area=%s session=%s", area, session_id)

    # Periférico: búsqueda encapsulada (casi siempre inactiva)
    busq = busqueda_web_si_autorizada(mensaje)
    ctx_hilo = contexto_hilo(session_id)

    contexto_extra = ctx_hilo
    if busq.get("activo") and busq.get("texto"):
        contexto_extra = (
            (contexto_extra + "\n\n" if contexto_extra else "")
            + "[Búsqueda autorizada por Israel]\n"
            + busq["texto"]
        )

    # Flujo directo audio/texto/visión → cerebro (misma entidad)
    try:
        respuesta = salomon.procesar_entrada(
            mensaje,
            lat=lat,
            lon=lon,
            imagen_base64=imagen_base64,
            imagen_mime=imagen_mime,
            error_consola=error_consola,
            autonomo=autonomo,
            contexto_mente=contexto_extra or None,
        )
    except Exception as exc:
        from cognicion.errores import auditar_excepcion

        err = auditar_excepcion(exc, origen="mente.procesar_unificado", pista="api")
        # Objeto mínimo compatible con ChatResponse / cerebro
        class _RespErr:
            texto = err.mensaje_usuario()
            exito = False
            metadata = err.to_meta()
            audio_base64 = None
            audio_mime = "audio/mpeg"
            tts_disponible = False
            imagen_url = None

        respuesta = _RespErr()
        texto = respuesta.texto
        registrar_turno(session_id, rol="asistente", texto=texto, area=area)
        return respuesta

    # Si hay contexto de hilo/periférico y el motor lo permite vía metadata
    if hasattr(respuesta, "metadata") and isinstance(respuesta.metadata, dict):
        respuesta.metadata.setdefault("mente", {})
        respuesta.metadata["mente"]["area"] = area
        respuesta.metadata["mente"]["hilo"] = session_id
        respuesta.metadata["mente"]["busqueda_periferica"] = bool(busq.get("activo"))
        respuesta.metadata["mente"]["conexion"] = "unificada"

    texto = getattr(respuesta, "texto", "") or ""
    registrar_turno(session_id, rol="asistente", texto=texto, area=area)
    return respuesta


# Re-export para API
inicio = protocolo_inicio
