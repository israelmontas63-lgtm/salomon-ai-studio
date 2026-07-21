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
  var keepCameraAllowed = false;
  var sessionId = localStorage.getItem("salomon_session_id") || null;

  /** Siempre leer session_id fresco (evita desync tras cambiar chat en el drawer). */
  function currentSessionId() {
    try {
      var live = localStorage.getItem("salomon_session_id");
      if (live) sessionId = live;
    } catch (_) {}
    return sessionId || null;
  }

  function setSessionId(id) {
    if (!id) return;
    sessionId = String(id);
    try {
      localStorage.setItem("salomon_session_id", sessionId);
    } catch (_) {}
    try {
      if (window.SalomonVision && window.SalomonVision.session) {
        window.SalomonVision.session.sessionId = sessionId;
      }
    } catch (_) {}
  }

  function looksVisualMessage(mensaje) {
    return /\b(mira|qu[eé]\s+ves|macro|micro|modo\s+visi[oó]n|ojos\s+activos|enfoque\s+(cerca|lejano)|foto|imagen|c[aá]mara|puedes\s+ver|modo\s+visual|desactiva(r)?\s+(el\s+)?modo\s+visual|qu[eé]\s+(hay|es\s+eso|color|planta|objeto)|eso\s+de\s+ah[ií]|frente\s+a\s+m[ií]|est[aá]s?\s+viendo)\b/i.test(
      mensaje || ""
    );
  }

  function visionChannelActive() {
    try {
      var cam = window.SalomonCamera;
      var V = window.SalomonVision;
      if (cam && cam.isActive && cam.isActive()) return true;
      if (V && V.isActive && V.isActive()) return true;
      if (V && V.session && (V.session.analyticalStreaming || V.session.visionChannel)) {
        return true;
      }
      if (document.body.classList.contains("vision-mode-active")) return true;
      if (document.body.classList.contains("vision-analytical")) return true;
    } catch (_) {}
    return false;
  }

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
          session_id: currentSessionId(),
        }),
        credentials: "same-origin",
        keepalive: true,
      }).catch(function () {});
    } catch (_) {}
  }

  function activate(why, opts) {
    if (is_ai_active) {
      // Refuerzo: si un turno posterior pide ojos, no apagarlos
      var optionsAlready = opts && typeof opts === "object" ? opts : {};
      if (optionsAlready.keepCamera || optionsAlready.keep_camera) {
        keepCameraAllowed = true;
      }
      return true;
    }
    var options = opts && typeof opts === "object" ? opts : {};
    var keepCamera = !!options.keepCamera || !!options.keep_camera;
    is_ai_active = true;
    keepCameraAllowed = keepCamera;
    reason = why || "smart_button";
    setBodyLock(true);
    try {
      if (window.SalomonUiManager && window.SalomonUiManager.hide) {
        window.SalomonUiManager.hide();
      }
      if (window.SalomonSettings && window.SalomonSettings.close) {
        window.SalomonSettings.close();
      }
      // Emergencia visión: no apagar ojos si este turno necesita frame / mira
      if (
        !keepCamera &&
        window.SalomonCamera &&
        window.SalomonCamera.isActive &&
        window.SalomonCamera.isActive()
      ) {
        if (window.SalomonCamera.closeCamera) {
          window.SalomonCamera.closeCamera();
        }
      }
    } catch (_) {}
    syncServer(true, reason);
    emit({
      action: "activate",
      reason: reason,
      keepCamera: keepCamera,
      keep_camera: keepCamera,
      hardware: keepCamera ? "camera_kept_for_vision" : "camera_forced_off",
    });
    return true;
  }

  function release(why) {
    if (!is_ai_active) return false;
    is_ai_active = false;
    keepCameraAllowed = false;
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

  function allowsCameraDuringAi() {
    return !!keepCameraAllowed;
  }

  function canUseSecondary() {
    return !is_ai_active;
  }

  /**
   * request_ui_action(action_id) — portero de hardware/menús.
   * return false si AI_PROCESSING (la cámara no recibe encendido).
   * Excepción: cámara/flip permitidos si el lock de voz pidió keepCamera (visión+dictado).
   */
  function request_ui_action(actionId) {
    var id = (actionId || "secondary").toLowerCase();
    var visionHw = id === "camera" || id === "flip" || id === "vision";
    if (is_ai_active && !(visionHw && keepCameraAllowed)) {
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

    // CRÍTICO: capturar frame ANTES de activate() (antes cerraba la cámara)
    var visPack = null;
    if (!body.imagen_base64 && !body.image_frame) {
      try {
        visPack = await prepareVisionPayload(mensaje);
      } catch (_) {
        visPack = null;
      }
    }
    var keepCamera = !!(
      body.keep_camera ||
      body.keepCamera ||
      body.imagen_base64 ||
      body.image_frame ||
      (visPack && visPack.imagen_base64) ||
      looksVisualMessage(mensaje) ||
      visionChannelActive()
    );
    activate(body.reason || "trigger_ai_core", { keepCamera: keepCamera });

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
        session_id: body.session_id || currentSessionId(),
      };
      var frameB64 = body.imagen_base64 || body.image_frame || null;
      var frameMime = body.imagen_mime || "image/jpeg";
      if (!frameB64 && visPack && visPack.imagen_base64) {
        frameB64 = visPack.imagen_base64;
        frameMime = visPack.imagen_mime || "image/jpeg";
      }
      if (frameB64) {
        dataOut.imagen_base64 = frameB64;
        dataOut.image_frame = frameB64;
        dataOut.imagen_mime = frameMime;
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
        setSessionId(data.session_id);
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
    var looksVisual = looksVisualMessage(mensaje);
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
   * Canal visión activo: autofocus + frame fresco (canvas→JPEG/WebP) para el núcleo.
   * Empareja consulta de voz/texto con image_frame / imagen_base64.
   */
  async function prepareVisionPayload(mensaje) {
    if (!visionChannelActive()) return null;

    var cam = window.SalomonCamera;
    var V = window.SalomonVision;

    try {
      if (cam && cam.autoFocusFromText) {
        await cam.autoFocusFromText(mensaje);
      }
      if (cam && cam.ensureSharpFocus) {
        await cam.ensureSharpFocus();
      }
    } catch (_) {}

    var dataUrl = null;
    if (V && V.captureCurrentFrame) {
      try {
        dataUrl = V.captureCurrentFrame(0.82);
      } catch (_) {}
    }
    if (!dataUrl && V && V.session && V.session.lastFrameDataUrl) {
      dataUrl = V.session.lastFrameDataUrl;
    }
    if (!dataUrl) return null;

    var mimeMatch = String(dataUrl).match(/^data:(image\/[\w.+-]+);base64,/i);
    var mime = mimeMatch ? mimeMatch[1] : "image/jpeg";
    var raw = String(dataUrl).replace(/^data:image\/[\w.+-]+;base64,/i, "");
    if (!raw) return null;
    if (V && V.session) V.session.lastFrameDataUrl = dataUrl;
    return {
      imagen_base64: raw,
      image_frame: raw,
      imagen_mime: mime,
      vision_active: true,
    };
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
    allowsCameraDuringAi: allowsCameraDuringAi,
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
    currentSessionId: currentSessionId,
    setSessionId: setSessionId,
    prepareVisionPayload: prepareVisionPayload,
    visionChannelActive: visionChannelActive,
    looksVisualMessage: looksVisualMessage,
  };

  // API global explícita (especificación de capas)
  window.trigger_ai_core = trigger_ai_core;
  window.request_ui_action = request_ui_action;
})();
