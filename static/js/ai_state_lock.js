/**
 * Salomón AI — State Lock del Botón Central (IA)
 * is_ai_active: exclusividad sobre cámara/menús; llamada directa a /api/ai-process.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  // Jerarquía Python: handle_central_button_click → call_salomon_brain
  var API_BRAIN = "/api/ai/central-button";
  var is_ai_active = false;
  var reason = "";
  var sessionId = localStorage.getItem("salomon_session_id") || null;

  function emit(detail) {
    window.dispatchEvent(
      new CustomEvent("salomon:ai-lock", {
        detail: Object.assign({ is_ai_active: is_ai_active }, detail || {}),
      })
    );
  }

  function setBodyLock(on) {
    document.body.classList.toggle("ai-active", !!on);
    document.body.setAttribute("data-ai-active", on ? "true" : "false");
  }

  /**
   * Prioridad del botón central: activa el bloqueo de estado.
   */
  function syncServer(activo, why) {
    try {
      fetch("/api/ai/lock", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          activo: !!activo,
          reason: why || reason || "smart_button",
          session_id: sessionId,
        }),
        credentials: "same-origin",
        keepalive: true,
      }).catch(function () {});
    } catch (_) {}
  }

  function activate(why) {
    if (is_ai_active) return true;
    is_ai_active = true;
    reason = why || "smart_button";
    setBodyLock(true);
    // Cerrar capas secundarias si estaban abiertas
    try {
      if (window.SalomonUiManager && window.SalomonUiManager.hide) {
        window.SalomonUiManager.hide();
      }
      if (window.SalomonSettings && window.SalomonSettings.close) {
        window.SalomonSettings.close();
      }
    } catch (_) {}
    syncServer(true, reason);
    emit({ action: "activate", reason: reason });
    return true;
  }

  /**
   * Restaura cámara/menús cuando termina la IA o se cierra.
   */
  function release(why) {
    if (!is_ai_active) return false;
    is_ai_active = false;
    var prev = reason;
    reason = "";
    setBodyLock(false);
    syncServer(false, why || "done");
    emit({ action: "release", reason: why || "done", previous: prev });
    return true;
  }

  function isActive() {
    return !!is_ai_active;
  }

  /** true = se puede usar cámara/menús secundarios */
  function canUseSecondary() {
    return !is_ai_active;
  }

  /**
   * Conexión directa al cerebro — sin middleware de cámara/settings/Aa.
   */
  async function callBrainDirect(payload) {
    var body = payload || {};
    var mensaje = (body.mensaje || "").trim();
    if (!mensaje) {
      return { ok: false, error: "mensaje_vacio" };
    }

    activate(body.reason || "call_brain_direct");

    try {
      var dataOut = {
        mensaje: mensaje,
        session_id: body.session_id || sessionId,
      };
      if (body.imagen_base64) {
        dataOut.imagen_base64 = body.imagen_base64;
        dataOut.imagen_mime = body.imagen_mime || "image/jpeg";
      }

      var res = await fetch(API_BRAIN, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dataOut),
        credentials: "same-origin",
      });
      var pack = await res.json().catch(function () {
        return {};
      });
      // Respuesta jerárquica: { brain: { texto, session_id, ... } }
      var data = pack.brain || pack;
      if (!data.texto && pack.mensaje && !pack.brain) {
        data = pack;
      }

      if (data.session_id) {
        sessionId = data.session_id;
        localStorage.setItem("salomon_session_id", sessionId);
      }

      emit({
        action: "brain_response",
        ok: res.ok,
        status: res.status,
        data: data,
        pack: pack,
      });

      return {
        ok: res.ok && (data.exito !== false) && !!data.texto,
        status: res.status,
        data: data,
        pack: pack,
      };
    } catch (err) {
      emit({ action: "brain_error", error: String(err && err.message ? err.message : err) });
      return { ok: false, error: "network", detail: String(err) };
    } finally {
      // Solo liberar si no pedimos mantener el lock (p.ej. mic aún escuchando)
      if (!body.keep_lock) {
        release("brain_done");
      }
    }
  }

  window.SalomonAILock = {
    get is_ai_active() {
      return is_ai_active;
    },
    activate: activate,
    release: release,
    isActive: isActive,
    canUseSecondary: canUseSecondary,
    callBrainDirect: callBrainDirect,
    /** alias pedido en especificación */
    isAiActive: isActive,
  };
})();
