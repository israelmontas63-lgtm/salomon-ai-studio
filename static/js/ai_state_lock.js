/**
 * Salomón AI — Capas de control (core_control)
 * trigger_ai_core()     → botón central → /api/ai/central-button
 * request_ui_action()   → cámara/menús; BLOCKED si AI_PROCESSING
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  var API_BRAIN = "/api/ai/central-button";
  var API_UI = "/api/ai/secondary";
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
    try {
      if (window.SalomonUiManager && window.SalomonUiManager.hide) {
        window.SalomonUiManager.hide();
      }
      if (window.SalomonSettings && window.SalomonSettings.close) {
        window.SalomonSettings.close();
      }
      if (window.SalomonCamera && window.SalomonCamera.isActive && window.SalomonCamera.isActive()) {
        if (window.SalomonCamera.closeCamera) {
          window.SalomonCamera.closeCamera();
        }
      }
    } catch (_) {}
    syncServer(true, reason);
    emit({ action: "activate", reason: reason, hardware: "camera_forced_off" });
    return true;
  }

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

  function canUseSecondary() {
    return !is_ai_active;
  }

  /**
   * request_ui_action(action_id) — portero de hardware/menús.
   * return false si AI_PROCESSING (la cámara no recibe encendido).
   */
  function request_ui_action(actionId) {
    if (is_ai_active) {
      try {
        console.info(
          "[SalomonAILock] request_ui_action BLOCKED:",
          actionId || "secondary",
          "AI_PRIORITY_ACTIVE"
        );
      } catch (_) {}
      emit({
        action: "blocked",
        function_name: actionId || "secondary",
        status: "BLOCKED",
        reason: "AI_PRIORITY_ACTIVE",
        is_ai_active: true,
      });
      // Espejo servidor (auditoría)
      try {
        fetch(API_UI, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ accion: actionId || "secondary" }),
          credentials: "same-origin",
          keepalive: true,
        }).catch(function () {});
      } catch (_) {}
      return false;
    }
    return true;
  }

  /** alias legacy */
  function uiLayerManager(functionName) {
    return request_ui_action(functionName);
  }

  /**
   * trigger_ai_core(data_payload) — canal obligatorio del botón central.
   * Puente visión: comandos mira/macro/micro + adjunto de frame si ojos activos.
   */
  async function trigger_ai_core(dataPayload) {
    var body = dataPayload || {};
    var mensaje = (body.mensaje || "").trim();
    if (!mensaje) {
      return { ok: false, error: "mensaje_vacio" };
    }

    activate(body.reason || "trigger_ai_core");

    try {
      // Paridad chat↔voz: comandos de visión locales (sin romper gestos del botón)
      var visionHandled = await tryHandleVisionCommand(mensaje);
      if (visionHandled) {
        emit({
          action: "brain_response",
          ok: true,
          data: visionHandled,
          via: "vision_command_local",
        });
        return { ok: true, data: visionHandled, via: "vision_command_local" };
      }

      var dataOut = {
        mensaje: mensaje,
        session_id: body.session_id || sessionId,
      };
      if (body.imagen_base64) {
        dataOut.imagen_base64 = body.imagen_base64;
        dataOut.imagen_mime = body.imagen_mime || "image/jpeg";
      } else {
        // Si los ojos están activos, adjuntar frame + autofocus contextual
        var visPack = await prepareVisionPayload(mensaje);
        if (visPack && visPack.imagen_base64) {
          dataOut.imagen_base64 = visPack.imagen_base64;
          dataOut.imagen_mime = visPack.imagen_mime || "image/jpeg";
        }
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
        via: "trigger_ai_core",
      });

      return {
        ok: res.ok && data.exito !== false && !!data.texto,
        status: res.status,
        data: data,
        pack: pack,
      };
    } catch (err) {
      emit({ action: "brain_error", error: String(err && err.message ? err.message : err) });
      return { ok: false, error: "network", detail: String(err) };
    } finally {
      if (!body.keep_lock) {
        release("trigger_ai_core_done");
      }
    }
  }

  /** Comandos explícitos de visión (mira / macro / micro / modo visión). */
  async function tryHandleVisionCommand(mensaje) {
    var looksVisual =
      /\b(mira|qu[eé]\s+ves|macro|micro|modo\s+visi[oó]n|ojos\s+activos|enfoque\s+(cerca|lejano))\b/i.test(
        mensaje || ""
      );
    if (
      looksVisual &&
      !window.SalomonVision &&
      window.SalomonMain &&
      window.SalomonMain.ensureCameraStack
    ) {
      try {
        await window.SalomonMain.ensureCameraStack();
      } catch (_) {}
    }

    var V = window.SalomonVision;
    if (!V || !V.parseCommand) return null;
    var cmd = V.parseCommand(mensaje);
    if (!cmd || !cmd.handled) return null;
    try {
      if (V.handleChatCommand) {
        await V.handleChatCommand(mensaje);
      }
      return {
        texto: "",
        exito: true,
        metadata: {
          vision_command: cmd.type || true,
          vision_local: true,
        },
      };
    } catch (_) {
      return null;
    }
  }

  /**
   * Si cámara/visión activa: autofocus por texto + último frame para el núcleo.
   */
  async function prepareVisionPayload(mensaje) {
    var cam = window.SalomonCamera;
    var V = window.SalomonVision;
    var active =
      (cam && cam.isActive && cam.isActive()) ||
      (V && V.isActive && V.isActive()) ||
      document.body.classList.contains("vision-mode-active");
    if (!active) return null;

    try {
      if (cam && cam.autoFocusFromText) {
        await cam.autoFocusFromText(mensaje);
      }
    } catch (_) {}

    var dataUrl = null;
    if (V && V.captureCurrentFrame) {
      try {
        dataUrl = V.captureCurrentFrame(0.85);
      } catch (_) {}
    }
    if (!dataUrl && V && V.session && V.session.lastFrameDataUrl) {
      dataUrl = V.session.lastFrameDataUrl;
    }
    if (!dataUrl) return null;

    var raw = String(dataUrl).replace(/^data:image\/\w+;base64,/, "");
    if (V && V.session) V.session.lastFrameDataUrl = dataUrl;
    return { imagen_base64: raw, imagen_mime: "image/jpeg" };
  }

  /** alias legacy → mismo canal */
  var callBrainDirect = trigger_ai_core;

  window.SalomonAILock = {
    get is_ai_active() {
      return is_ai_active;
    },
    activate: activate,
    release: release,
    isActive: isActive,
    canUseSecondary: canUseSecondary,
    request_ui_action: request_ui_action,
    requestUiAction: request_ui_action,
    uiLayerManager: uiLayerManager,
    trigger_ai_core: trigger_ai_core,
    triggerAiCore: trigger_ai_core,
    callBrainDirect: callBrainDirect,
    isAiActive: isActive,
    handleCentralButtonClick: trigger_ai_core,
    executeSalomonBrainProcess: trigger_ai_core,
  };

  // API global explícita (especificación de capas)
  window.trigger_ai_core = trigger_ai_core;
  window.request_ui_action = request_ui_action;
})();
