"""
Motor de Ciberseguridad — coordina defensa en profundidad estilo JARVIS.

Principio: identificar → limitar → aislar → registrar → notificar → recuperar.
Nunca acciones ofensivas contra terceros.
"""

from __future__ import annotations

import uuid
from typing import Any

from cognicion.nucleo import obtener_nucleo
from cognicion.seguridad.anomalias import obtener_detector_anomalias
from cognicion.seguridad.auditoria import contar_por_accion, inicializar as init_auditoria, listar as listar_auditoria, registrar as registrar_auditoria
from cognicion.seguridad.identidad import puede_acceder, requiere_admin, resolver_actor
from cognicion.seguridad.intrusion import obtener_detector
from cognicion.seguridad.monitoreo import snapshot as snapshot_monitoreo
from cognicion.seguridad.recuperacion import crear_snapshot, estado_recuperacion, intentar_recuperar, listar_snapshots, servicio_degradado
from cognicion.seguridad.secretos import claves_activas, inventario_secretos
from cognicion.seguridad.tipos import AccionSeguridad, AlertaSeguridad, EventoSeguridad, RolAcceso, Severidad, TipoAmenaza
from cognicion.registro import evento, obtener_logger

_log = obtener_logger("ciberseguridad")


class MotorCiberseguridad:
    """Kernel de seguridad — defensa en profundidad."""

    def __init__(self) -> None:
        init_auditoria()
        self._alertas: list[AlertaSeguridad] = []
        self._iniciado = False

    def iniciar(self) -> None:
        if self._iniciado:
            return
        crear_snapshot(motivo="inicio_sistema")
        intentar_recuperar("llm")
        self._iniciado = True
        obtener_nucleo().eventos.emitir("seguridad:inicio", capas=10)
        evento(_log, "motor_ciberseguridad_iniciado")

    def evaluar_peticion_entrante(
        self,
        path: str,
        metodo: str,
        ip: str,
        api_key: str | None = None,
        query: str = "",
        user_agent: str = "",
    ) -> tuple[bool, EventoSeguridad | None, str]:
        """
        Capa 1–3: intrusión + identidad.
        Returns: (permitir, evento_amenaza, motivo)
        """
        detector = obtener_detector()

        amenaza = detector.evaluar_peticion(path, metodo, ip, query=query)
        if amenaza and amenaza.accion == AccionSeguridad.BLOQUEAR:
            self._procesar_amenaza(amenaza)
            return False, amenaza, amenaza.detalle

        actor = resolver_actor(api_key, ip=ip, user_agent=user_agent)
        permitido, motivo = puede_acceder(actor, path, metodo)

        if not permitido:
            ev = EventoSeguridad(
                tipo=TipoAmenaza.ACCESO_DENEGADO,
                severidad=Severidad.MEDIA,
                accion=AccionSeguridad.BLOQUEAR,
                detalle=motivo,
                actor=actor,
                recurso=path,
            )
            self._procesar_amenaza(ev)
            return False, ev, motivo

        return True, None, motivo

    def evaluar_auth_fallida(self, ip: str, path: str) -> EventoSeguridad:
        ev = obtener_detector().registrar_auth_fallida(ip, path)
        self._procesar_amenaza(ev)
        return ev

    def registrar_peticion_completada(
        self,
        *,
        path: str,
        metodo: str,
        status: int,
        duracion_ms: float,
        ip: str = "",
        user_agent: str = "",
        api_key: str | None = None,
        session_id: str = "",
    ) -> None:
        """Capa 4–5: auditoría + detección de anomalías."""
        actor = resolver_actor(api_key, ip=ip, user_agent=user_agent)
        accion = "api_peticion" if status < 400 else "api_error"

        registrar_auditoria(
            actor_rol=actor.rol.value,
            actor_id=actor.identificador,
            accion=accion,
            recurso=path,
            ip=ip,
            user_agent=user_agent[:200],
            metodo=metodo,
            status=status,
            duracion_ms=duracion_ms,
            session_id=session_id,
        )

        if path.startswith("/api/"):
            alerta = obtener_detector_anomalias().registrar_observacion(
                path, duracion_ms, status
            )
            if alerta:
                self._alertas.append(alerta)
                self._notificar_admin(alerta)
                obtener_nucleo().eventos.emitir(
                    "seguridad:anomalia",
                    ruta=path,
                    detalle=alerta.evento.detalle,
                )

        if status >= 500:
            intentar_recuperar("llm")

    def _procesar_amenaza(self, ev: EventoSeguridad) -> None:
        alerta = AlertaSeguridad(id=str(uuid.uuid4()), evento=ev)
        self._alertas.append(alerta)
        if len(self._alertas) > 300:
            self._alertas = self._alertas[-300:]

        registrar_auditoria(
            actor_rol=ev.actor.rol.value if ev.actor else RolAcceso.ANON.value,
            actor_id=ev.actor.identificador if ev.actor else "sistema",
            accion=f"amenaza_{ev.tipo.value}",
            recurso=ev.recurso,
            ip=ev.actor.ip if ev.actor else "",
            detalle=ev.detalle,
            status=403,
        )

        obtener_nucleo().eventos.emitir(
            "seguridad:amenaza",
            tipo=ev.tipo.value,
            severidad=ev.severidad.value,
            accion=ev.accion.value,
            detalle=ev.detalle,
        )
        evento(
            _log,
            "amenaza",
            tipo=ev.tipo.value,
            severidad=ev.severidad.value,
            accion_seguridad=ev.accion.value,
            detalle=ev.detalle,
        )

        if ev.severidad in (Severidad.ALTA, Severidad.CRITICA):
            self._notificar_admin(alerta)

    def _notificar_admin(self, alerta: AlertaSeguridad) -> None:
        if alerta.notificada:
            return
        alerta.notificada = True
        evento(
            _log,
            "alerta_admin",
            id=alerta.id,
            tipo=alerta.evento.tipo.value,
            detalle=alerta.evento.detalle,
        )

    def estado(self) -> dict[str, Any]:
        detector = obtener_detector()
        anomalias = obtener_detector_anomalias()
        return {
            "motor": "ciberseguridad",
            "version": "1.0.0",
            "principio": "identificar → limitar → aislar → registrar → notificar → recuperar",
            "ofensivo": False,
            "capas": [
                "intrusion",
                "identidad",
                "secretos",
                "auditoria",
                "anomalias",
                "sandbox",
                "monitoreo",
                "recuperacion",
                "degradacion",
                "defensa_profundidad",
            ],
            "ips_bloqueadas": detector.ips_bloqueadas(),
            "eventos_intrusion": detector.ultimos_eventos(10),
            "alertas_activas": anomalias.alertas_activas(10),
            "alertas_motor": [
                {
                    "id": a.id,
                    "tipo": a.evento.tipo.value,
                    "severidad": a.evento.severidad.value,
                    "detalle": a.evento.detalle,
                    "timestamp": a.evento.timestamp,
                }
                for a in self._alertas[-10:]
                if not a.resuelta
            ],
            "linea_base": anomalias.linea_base(),
            "secretos": inventario_secretos(),
            "claves_activas": claves_activas(),
            "monitoreo": snapshot_monitoreo(),
            "recuperacion": estado_recuperacion(),
            "degradados": {
                "llm": servicio_degradado("llm"),
                "memoria": servicio_degradado("memoria"),
            },
            "auditoria_resumen": contar_por_accion(),
        }


_motor: MotorCiberseguridad | None = None


def obtener_motor() -> MotorCiberseguridad:
    global _motor
    if _motor is None:
        _motor = MotorCiberseguridad()
        _motor.iniciar()
    return _motor


def reiniciar_motor() -> None:
    global _motor
    _motor = None
