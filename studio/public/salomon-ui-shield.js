/**
 * SalomÃ³n AI Studio â€” UI Shield v1
 * Interacciones visuales sobre UI estable (sin tocar Gemini/clima/prompt).
 */
(function () {
  "use strict";

  var ICON_USER =
    '<span class="header-icon-user" aria-hidden="true"><svg viewBox="0 0 24 24">' +
    '<circle cx="12" cy="8" r="3.2"/>' +
    '<path d="M5.5 19.2c1.6-3.1 4-4.6 6.5-4.6s4.9 1.5 6.5 4.6"/>' +
    "</svg></span>";
  var ICON_H = '<span class="header-icon-h" aria-hidden="true">H</span>';

  var camera = {
    stream: null,
    facing: "environment",
    phase: "closed", // derivado de modoInterfaz
    open: false,
    capturing: false,
    flipping: false,
    mode: "photo",
    videoEl: null,
    openSeq: 0,
    flipSeq: 0,
    agentLockTimer: 0,
    zoom: 1,
    pinch: { active: false, startDist: 0, startZoom: 1, moved: false },
    stageEl: null,
    stageTapHandler: null,
    opening: false,
  };
  /** CAPA 1 — único estado de interfaz (fuente de verdad) */
  var modoInterfaz = "asistente"; // "asistente" | "camara-trasera" | "camara-frontal"
  var ZOOM_MIN = 1;
  var ZOOM_MAX = 4;
  var audio = { ctx: null, analyser: null, src: null, raf: 0, stream: null };
  var swapLock = false;
  var writeLock = false;
  var closingWrite = false;
  var lastTap = 0;
  var lastCamTap = 0;
  var lastShotAt = 0;
  var HOLD_CAPTURE_MS = 500;
  var CAPTURE_OPTS = { capture: true, passive: false };
  var SHOT_COOLDOWN_MS = 550;
  var CAM_CYCLE_MS = 550;

  function log() {
    try {
      console.info.apply(console, ["[UI Shield]"].concat([].slice.call(arguments)));
    } catch (e) {}
  }

  function canTakeShot() {
    var now = Date.now();
    if (now - lastShotAt < SHOT_COOLDOWN_MS) return false;
    if (!isCamMode() || !camera.open || camera.capturing) return false;
    if (camera.pinch.active || camera.pinch.moved) return false;
    if (camera.flipping && modoInterfaz !== "camara-frontal") return false;
    lastShotAt = now;
    return true;
  }

  function isCamMode() {
    return modoInterfaz === "camara-trasera" || modoInterfaz === "camara-frontal";
  }

  function getModoInterfaz() {
    return modoInterfaz;
  }

  /**
   * CAPA 1 — setter unico. Camara y boton central solo leen este estado.
   * Ciclo: asistente → camara-trasera → camara-frontal → asistente
   */
  function setModoInterfaz(next) {
    if (next !== "asistente" && next !== "camara-trasera" && next !== "camara-frontal") {
      return;
    }
    if (next === modoInterfaz && next === "asistente") return;
    // Mismo modo cam + stream ok → no-op; si quedó colgado sin stream, reintenta
    if (next === modoInterfaz && isCamMode() && camera.open && !camera.flipping && !camera.opening) return;

    var prev = modoInterfaz;
    modoInterfaz = next;
    document.documentElement.setAttribute("data-modo-interfaz", next);
    log("modoInterfaz", prev, "->", next);

    if (next === "asistente") {
      camera.phase = "closed";
      camera.facing = "environment";
      stopCameraCompleto(false);
      return;
    }

    if (next === "camara-trasera") {
      camera.phase = "rear";
      camera.facing = "environment";
      pauseChatForCapture();
      stopAudioReactive();
      openNeuralCamera({ mode: "photo", facing: "environment", keepFacing: true });
      return;
    }

    // camara-frontal
    camera.phase = "selfie";
    camera.facing = "user";
    pauseChatForCapture();
    stopAudioReactive();
    resetCameraZoom();
    if (prev === "camara-trasera" && camera.open && camera.videoEl) {
      var overlay = document.getElementById("ui-camera-overlay");
      if (overlay) {
        overlay.dataset.facing = "user";
        overlay.classList.add("is-selfie");
      }
      syncCameraUiState();
      swapFacingInPlace("environment");
    } else {
      openNeuralCamera({ mode: "photo", facing: "user", keepFacing: true });
    }
  }

  function canCycleCam() {
    var now = Date.now();
    if (now - lastCamTap < CAM_CYCLE_MS) return false;
    if (camera.flipping || camera.capturing || camera.opening) return false;
    // En cam: no avanzar ciclo hasta tener stream listo (evita 2 streams)
    if (isCamMode() && !camera.open) return false;
    lastCamTap = now;
    return true;
  }

  /** Solo un evento â€œÃºtilâ€ por gesto tÃ¡ctil (evita touchend+click doble) */
  function isPrimaryGesture(e) {
    if (!e) return false;
    if (e.type === "touchend") return true;
    if (e.type === "pointerup") {
      if (e.pointerType === "touch") return false; // ya hubo touchend
      return true; // mouse / pen
    }
    if (e.type === "click") {
      if (e.pointerType === "touch") return false;
      // click sintÃ©tico tras touch: detail suele ser 1; si hubo touch reciente, ignorar
      if (Date.now() - lastCamTap < 700 || Date.now() - lastShotAt < 700) return false;
      return true;
    }
    return false;
  }

  function haptic(ms) {
    try {
      if (!navigator.vibrate) return;
      if (navigator.userActivation && !navigator.userActivation.hasBeenActive) return;
      navigator.vibrate(ms || 10);
    } catch (e) {}
  }

  /* â€”â€”â€” Header: H izq (tools) / Perfil der (cuenta) + swap de clicks â€”â€”â€” */
  function styleHeader() {
    var header = document.querySelector(".studio-header");
    if (!header) return false;
    var btns = header.querySelectorAll(".header-menu-btn");
    if (btns.length < 2) return false;

    // Ocultar subtÃ­tulo
    var sub = header.querySelector(".logo-subtitle");
    if (sub) sub.style.display = "none";

    // Iconos
    injectHeaderIcon(btns[0], "h", ICON_H, "Herramientas");
    injectHeaderIcon(btns[1], "user", ICON_USER, "Cuenta y Planes");

    // Swap: React left=account, right=tools â†’ UI left=tools, right=account
    if (header.dataset.uiSwap !== "1") {
      header.dataset.uiSwap = "1";
      btns[0].addEventListener(
        "click",
        function (e) {
          if (swapLock) return;
          e.preventDefault();
          e.stopImmediatePropagation();
          swapLock = true;
          btns[1].click();
          swapLock = false;
        },
        true
      );
      btns[1].addEventListener(
        "click",
        function (e) {
          if (swapLock) return;
          e.preventDefault();
          e.stopImmediatePropagation();
          swapLock = true;
          btns[0].click();
          swapLock = false;
        },
        true
      );
    }

    // SS thinking state from status dot / bridge
    syncLogoState(header);
    return true;
  }

  function injectHeaderIcon(btn, kind, html, label) {
    if (!btn) return;
    btn.setAttribute("aria-label", label);
    btn.title = label;
    if (btn.dataset.uiIcon === kind && btn.querySelector(".header-icon-" + (kind === "h" ? "h" : "user"))) {
      return;
    }
    btn.dataset.uiIcon = kind;
    var old = btn.querySelector(".header-icon-h, .header-icon-user, .dots-icon, .lines-icon");
    if (old) old.outerHTML = html;
    else btn.insertAdjacentHTML("afterbegin", html);
    var lab = btn.querySelector(".menu-label");
    if (lab) lab.textContent = label;
  }

  function syncLogoState(header) {
    header = header || document.querySelector(".studio-header");
    if (!header) return;
    var thinking =
      header.querySelector(".status-dot--thinking, .status-dot--listening, .status-dot--speaking") ||
      (window.SalomonBridge &&
        (window.SalomonBridge.getState() === "PROCESSING" ||
          window.SalomonBridge.getState() === "DICTATING" ||
          window.SalomonBridge.getState() === "CONVERSATION"));
    header.dataset.ssState = thinking ? "thinking" : "idle";
    var logo = header.querySelector(".vinyl-card, .salomon-logo");
    if (logo) {
      logo.classList.add("salomon-logo");
      logo.classList.toggle("pensando", !!thinking);
      var ss = logo.querySelector(".vinyl-card__ss");
      if (ss && ss.textContent.replace(/\s/g, "") === "SS") ss.textContent = "S S";
    }
  }

  /** Sella clases de la maqueta ESTRUCTURA sobre el DOM React estable */
  function stampEstructuraClasses() {
    var header = document.querySelector(".studio-header");
    if (header) {
      var logo = header.querySelector(".vinyl-card");
      if (logo) logo.classList.add("salomon-logo");
      header.querySelectorAll(".header-menu-btn").forEach(function (btn) {
        btn.classList.add("menu-icono", "brillo");
      });
      syncLogoState(header);
    }

    var form =
      document.querySelector(".bottom-bar form.chat-input") ||
      document.querySelector(".bottom-bar .chat-input") ||
      document.querySelector(".bottom-bar .input-row");
    if (form) {
      form.classList.add("campo-texto-contenedor", "teclado-deslizar-enter");
      var input = form.querySelector("input");
      if (input) {
        input.classList.add("campo-texto-input");
        if (!input.dataset.uiCampoFocus) {
          input.dataset.uiCampoFocus = "1";
          input.addEventListener("focus", function () {
            form.classList.add("activo");
          });
          input.addEventListener("blur", function () {
            form.classList.remove("activo");
          });
        }
      }
      var send = form.querySelector(".send-btn");
      if (send) send.classList.add("flecha-enviar");
    }

    var row = document.querySelector(".controls-row");
    if (row) {
      row.classList.add("barra-botones");
      var btns = row.querySelectorAll(".control-btn");
      if (btns[0]) btns[0].classList.add("boton-camara");
      var main = row.querySelector(".control-btn--main") || btns[1];
      if (main) {
        main.classList.add("boton-central");
        var orbit = main.querySelector(".ui-voice-orbit");
        if (orbit) orbit.classList.add("anillo-dictado");
        var cloud = main.querySelector(".ui-voice-cloud");
        if (cloud) cloud.classList.add("destello-nube");
      }
      if (btns.length) btns[btns.length - 1].classList.add("boton-texto");
    }

    document.querySelectorAll(".bubble--ai").forEach(function (el) {
      el.classList.add("burbuja-mensaje", "salomon");
    });
    document.querySelectorAll(".bubble--user").forEach(function (el) {
      el.classList.add("burbuja-mensaje", "usuario");
    });
    var menu = document.getElementById("ui-bubble-menu");
    if (menu) menu.classList.add("menu-contextual-mensaje");
  }

  /* â€”â€”â€” Bottom controls: camera / voice fx / text â€”â€”â€” */
  function enhanceControls() {
    var row = document.querySelector(".controls-row");
    if (!row) return false;
    var btns = row.querySelectorAll(".control-btn");
    if (btns.length < 3) return false;

    var cam = btns[0];
    var main = row.querySelector(".control-btn--main") || btns[1];
    var textBtn = btns[btns.length - 1];

    // Ciclo cÃ¡mara: cerrado â†’ trasera â†’ selfie â†’ cerrado (un solo gesto)
    if (cam.dataset.uiCam !== "1") {
      cam.dataset.uiCam = "1";
      cam.classList.add("ui-smart-cam-btn", "boton-camara");
      cam.setAttribute("aria-label", " ");
      cam.removeAttribute("title");
      function onCamGesture(e) {
        if (!isPrimaryGesture(e)) return;
        if (e.cancelable) e.preventDefault();
        e.stopImmediatePropagation();
        e.stopPropagation();
        onFooterCameraTap();
      }
      cam.addEventListener("touchend", onCamGesture, CAPTURE_OPTS);
      cam.addEventListener("pointerup", onCamGesture, CAPTURE_OPTS);
      cam.addEventListener("click", onCamGesture, true);
    }

    // Escritura (Aa): bloqueada en CAPTURA
    if (textBtn.dataset.uiText !== "1") {
      textBtn.dataset.uiText = "1";
      textBtn.classList.add("ui-write-btn");
      textBtn.setAttribute("aria-label", "Texto");
      textBtn.addEventListener(
        "click",
        function (e) {
          if (isCamMode() && !writeLock) {
            e.preventDefault();
            e.stopImmediatePropagation();
            return;
          }
          if (writeLock) return;
          setTimeout(syncWritingUiState, 0);
          setTimeout(syncWritingUiState, 80);
        },
        true
      );
    }

    if (main) {
      ensureVoiceFx(main);
      ensureShutterCamIcon(main);
      wireMainShutterGate(main);
      if (main.dataset.uiVoice !== "1") {
        main.dataset.uiVoice = "1";
        wireVoiceGestures(main);
      }
    }

    polishInput();
    syncCameraUiState();
    syncWritingUiState();
    return true;
  }

  function ensureShutterCamIcon(btn) {
    if (!btn) return;
    if (!btn.querySelector(".ui-shutter-cam-icon")) {
      var icon = document.createElement("span");
      icon.className = "ui-shutter-cam-icon";
      icon.setAttribute("aria-hidden", "true");
      btn.appendChild(icon);
    }
    if (!btn.querySelector(".ui-cam-ring-plata")) {
      var ring = document.createElement("span");
      ring.className = "ui-cam-ring-plata";
      ring.setAttribute("aria-hidden", "true");
      btn.appendChild(ring);
    }
    if (!btn.querySelector(".ui-cam-swirl-plata")) {
      var swirl = document.createElement("span");
      swirl.className = "ui-cam-swirl-plata";
      swirl.setAttribute("aria-hidden", "true");
      btn.appendChild(swirl);
    }
  }

  function getTextBtn() {
    var row = document.querySelector(".controls-row");
    if (!row) return null;
    var btns = row.querySelectorAll(".control-btn");
    return btns.length ? btns[btns.length - 1] : null;
  }

  function isWritingOpen() {
    return !!document.querySelector(".bottom-bar form.chat-input");
  }

  function closeWritingIfOpen() {
    if (closingWrite || !isWritingOpen()) return;
    var btn = getTextBtn();
    if (!btn) return;
    closingWrite = true;
    writeLock = true;
    try {
      // Con writeLock el handler Aa deja pasar el click a React para desmontar el form
      btn.click();
    } catch (e) {}
    writeLock = false;
    closingWrite = false;
    document.documentElement.classList.remove("salomon-write-mode");
    if (btn) btn.classList.remove("is-write-active");
  }

  function syncWritingUiState() {
    var open = isWritingOpen();
    var textBtn = getTextBtn();
    var camOn = isCamMode();
    // CAPTURA manda: si el form de chat sigue en DOM, cerrar solo escritura (no apagar captura)
    if (open && camOn) {
      closeWritingIfOpen();
      open = isWritingOpen();
    }
    if (textBtn) {
      textBtn.classList.add("ui-write-btn");
      textBtn.classList.toggle("is-write-active", open && !camOn);
      textBtn.setAttribute("aria-label", " ");
      textBtn.removeAttribute("title");
    }
    document.documentElement.classList.toggle("salomon-write-mode", open && !camOn);
    if (!camOn) polishInput();
  }

  function ensureVoiceFx(btn) {
    if (!btn.querySelector(".ui-voice-orbit")) {
      var orbit = document.createElement("span");
      orbit.className = "ui-voice-orbit";
      orbit.setAttribute("aria-hidden", "true");
      btn.appendChild(orbit);
    }
    if (!btn.querySelector(".ui-voice-cloud")) {
      var cloud = document.createElement("span");
      cloud.className = "ui-voice-cloud";
      cloud.setAttribute("aria-hidden", "true");
      btn.appendChild(cloud);
    }
  }

  /** Cancela chat/voz y bloquea agente mientras CAPTURA */
  function pauseChatForCapture() {
    closeWritingIfOpen();
    stopAudioReactive();
    lockAgentOut();
    var main = document.querySelector(".controls-row .control-btn--main");
    if (main) {
      main.dataset.uiMode = "";
      main.classList.remove("voice-btn--spinning", "control-btn--recording");
      main.removeAttribute("data-button-state");
    }
    document.documentElement.classList.add("salomon-cam-mode");
    document.documentElement.setAttribute("data-salomon-camera-only", "1");
    document.documentElement.setAttribute("data-salomon-layer", "camera");
    setAgentLayerInert(true);
  }

  function setAgentLayerInert(on) {
    var root = document.getElementById("root");
    if (root) {
      try {
        if (on) root.setAttribute("inert", "");
        else root.removeAttribute("inert");
      } catch (e) {}
      root.setAttribute("aria-hidden", on ? "true" : "false");
      root.setAttribute("data-salomon-layer", on ? "agent-paused" : "agent");
    }
    var header = document.querySelector(".studio-header");
    if (header) {
      header.setAttribute("aria-hidden", on ? "true" : "false");
      header.setAttribute("data-salomon-layer", on ? "agent-paused" : "agent");
    }
  }

  function lockAgentOut() {
    try {
      if (window.SalomonBridge && typeof window.SalomonBridge.cancelAll === "function") {
        window.SalomonBridge.cancelAll("camera-only-mode");
      }
    } catch (e) {}
    try {
      window.dispatchEvent(new CustomEvent("salomon:camera-agent-lock", { detail: { lock: true } }));
    } catch (e) {}
    if (camera.agentLockTimer) return;
    camera.agentLockTimer = setInterval(function () {
      if (!camera.open) {
        clearInterval(camera.agentLockTimer);
        camera.agentLockTimer = 0;
        return;
      }
      try {
        if (window.SalomonBridge && typeof window.SalomonBridge.cancelAll === "function") {
          window.SalomonBridge.cancelAll("camera-only-pulse");
        }
      } catch (e) {}
    }, 1200);
  }

  function unlockAgent() {
    if (camera.agentLockTimer) {
      clearInterval(camera.agentLockTimer);
      camera.agentLockTimer = 0;
    }
    document.documentElement.removeAttribute("data-salomon-camera-only");
    document.documentElement.setAttribute("data-salomon-layer", "agent");
    setAgentLayerInert(false);
    try {
      window.dispatchEvent(new CustomEvent("salomon:camera-agent-lock", { detail: { lock: false } }));
    } catch (e) {}
  }

  /** Controles + preview permitidos en CAPTURA (resto del DOM = muro) */
  function isCaptureExemptTarget(t) {
    if (!t || !t.closest) return false;
    return !!(
      t.closest(".control-btn--main") ||
      t.closest(".voice-btn-wrap") ||
      t.closest(".boton-central") ||
      t.closest(".ui-smart-cam-btn") ||
      t.closest(".boton-camara") ||
      t.closest('.control-btn[aria-label="CÃ¡mara"]') ||
      t.closest(".ui-write-btn") ||
      t.closest(".boton-texto") ||
      t.closest(".ui-camera-close") ||
      t.closest("#ui-smart-button") ||
      t.closest(".ui-smart-button") ||
      t.closest("#ui-camera-overlay") ||
      t.closest(".ui-camera-stage") ||
      t.closest(".neural-camera") ||
      t.closest("#salomon-update-btn") ||
      t.closest(".salomon-update-slot") ||
      t.closest(".cam13-root") ||
      t.closest("[data-salomon-camera-v13]") ||
      t.closest("[data-salomon-camera-v14]")
    );
  }

  function isScreenShutterTarget(t) {
    if (!t || !t.closest) return false;
    if (t.closest(".bottom-bar")) return false;
    if (t.closest(".studio-header")) return false;
    if (t.closest(".salomon-update-slot")) return false;
    return !!(
      t.closest("#ui-camera-overlay") ||
      t.closest(".ui-camera-stage") ||
      t.closest("#root") ||
      t === document.body ||
      t === document.documentElement
    );
  }

  /**
   * Muro CAPTURA: chat no recibe gestos.
   * Gatillo de pantalla solo sobre preview/Ã¡rea de cÃ¡mara (no footer).
   */
  function installCaptureEventWall() {
    if (document.documentElement.dataset.uiCamWall === "1") return;
    document.documentElement.dataset.uiCamWall = "1";
    var blockTypes = [
      "touchstart",
      "touchmove",
      "pointerdown",
      "pointermove",
      "mousedown",
      "mouseup",
      "click",
    ];
    function blockChat(e) {
      // v13/v14 aislada: no interceptar gestos (ni preview ni botones)
      if (
        document.documentElement.classList.contains("camera-v13-open") ||
        document.documentElement.classList.contains("camera-v14-open") ||
        document.documentElement.classList.contains("camera-v15-open") ||
        document.documentElement.classList.contains("camera-v16-open")
      ) {
        return;
      }
      if (!isCamMode()) return;
      if (isCaptureExemptTarget(e.target)) return;
      if (e.cancelable) e.preventDefault();
      e.stopImmediatePropagation();
      e.stopPropagation();
    }
    blockTypes.forEach(function (type) {
      document.addEventListener(type, blockChat, CAPTURE_OPTS);
    });

    function onScreenShutter(e) {
      if (!isCamMode()) return;
      if (camera.pinch.active || camera.pinch.moved) return;
      if (isCaptureExemptTarget(e.target) && !isScreenShutterTarget(e.target)) return;
      if (!isPrimaryGesture(e)) return;
      if (!isScreenShutterTarget(e.target)) return;
      // 2 dedos = pellizco, no foto
      if (e.touches && e.touches.length > 0) return;
      if (e.changedTouches && e.changedTouches.length > 1) return;
      if (e.cancelable) e.preventDefault();
      e.stopImmediatePropagation();
      e.stopPropagation();
      if (!canTakeShot()) return;
      log("pantalla â†’ capturePhoto");
      capturePhoto();
    }
    document.addEventListener("touchend", onScreenShutter, CAPTURE_OPTS);
    document.addEventListener("pointerup", onScreenShutter, CAPTURE_OPTS);

    if (document.documentElement.dataset.uiCamVol !== "1") {
      document.documentElement.dataset.uiCamVol = "1";
      function onVolume(e) {
        if (!isCamMode()) return;
        var k = e.key || "";
        var c = e.code || "";
        if (
          k === "AudioVolumeUp" ||
          k === "AudioVolumeDown" ||
          c === "VolumeUp" ||
          c === "VolumeDown" ||
          c === "AudioVolumeUp" ||
          c === "AudioVolumeDown"
        ) {
          if (e.cancelable) e.preventDefault();
          e.stopImmediatePropagation();
          if (!canTakeShot()) return;
          log("volumen â†’ capturePhoto");
          capturePhoto();
        }
      }
      document.addEventListener("keydown", onVolume, true);
      document.addEventListener("keyup", onVolume, true);
    }
    log("muro CAPTURA + gatillos pantalla/volumen v2");
  }

  /** BotÃ³n central / mic = disparador con icono cÃ¡mara */
  function wireMainShutterGate(main) {
    if (!main || main.dataset.uiShutterGate === "1") return;
    main.dataset.uiShutterGate = "1";
    var wrap = main.closest(".voice-btn-wrap") || main;
    var targets = wrap === main ? [main] : [wrap, main];

    function gate(e) {
      if (!isCamMode()) return;
      if (!isPrimaryGesture(e)) return;
      if (e.cancelable) e.preventDefault();
      e.stopImmediatePropagation();
      e.stopPropagation();
      if (!canTakeShot()) return;
      log("mic/shutter â†’ capturePhoto (facing=" + camera.facing + ")");
      capturePhoto();
    }

    function blockVoiceWhileCam(e) {
      if (!isCamMode()) return;
      if (e.cancelable) e.preventDefault();
      e.stopImmediatePropagation();
      e.stopPropagation();
    }
    ["touchstart", "pointerdown", "mousedown"].forEach(function (type) {
      targets.forEach(function (el) {
        el.addEventListener(type, blockVoiceWhileCam, CAPTURE_OPTS);
      });
    });
    ["touchend", "pointerup", "click"].forEach(function (type) {
      targets.forEach(function (el) {
        el.addEventListener(type, gate, type === "click" ? true : CAPTURE_OPTS);
      });
    });
  }

  function wireVoiceGestures(btn) {
    // Solo feedback visual en modo CHAT (CAPTURA lo corta el shutter gate)
    btn.addEventListener(
      "click",
      function (e) {
        if (isCamMode()) {
          e.preventDefault();
          e.stopImmediatePropagation();
          return;
        }
        var now = Date.now();
        var dbl = now - lastTap < 320;
        lastTap = now;
        if (dbl) {
          btn.dataset.uiMode = "conversation";
          btn.dataset.uiFlash = "1";
          haptic([12, 30, 12]);
          setTimeout(function () {
            btn.dataset.uiFlash = "0";
          }, 900);
          startAudioReactive(btn);
        } else {
          setTimeout(function () {
            if (Date.now() - lastTap >= 300 && !isCamMode()) {
              btn.dataset.uiMode = "dictation";
              startAudioReactive(btn);
            }
          }, 300);
        }
      },
      true
    );
  }

  function startAudioReactive(btn) {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;
    if (audio.raf) return;
    navigator.mediaDevices
      .getUserMedia({ audio: true, video: false })
      .then(function (stream) {
        audio.stream = stream;
        audio.ctx = new (window.AudioContext || window.webkitAudioContext)();
        audio.analyser = audio.ctx.createAnalyser();
        audio.analyser.fftSize = 256;
        audio.src = audio.ctx.createMediaStreamSource(stream);
        audio.src.connect(audio.analyser);
        var data = new Uint8Array(audio.analyser.frequencyBinCount);

        function tick() {
          audio.analyser.getByteTimeDomainData(data);
          var sum = 0;
          for (var i = 0; i < data.length; i++) {
            var v = (data[i] - 128) / 128;
            sum += v * v;
          }
          var rms = Math.sqrt(sum / data.length);
          // Suave â†’ lento; fuerte â†’ agitado
          var speed = Math.max(0.45, 2.8 - rms * 6);
          btn.style.setProperty("--ui-voice-speed", speed.toFixed(2) + "s");
          var turb = 0.5 + rms * 2.2;
          var orbit = btn.querySelector(".ui-voice-orbit");
          if (orbit) orbit.style.filter = "blur(" + Math.min(2.2, rms * 4).toFixed(2) + "px) brightness(" + turb.toFixed(2) + ")";
          audio.raf = requestAnimationFrame(tick);
        }
        audio.raf = requestAnimationFrame(tick);

        // Auto-stop analyser when idle again
        setTimeout(function () {
          if (
            !btn.classList.contains("control-btn--recording") &&
            !btn.classList.contains("voice-btn--spinning") &&
            window.SalomonBridge &&
            window.SalomonBridge.getState() === "IDLE"
          ) {
            stopAudioReactive();
          }
        }, 12000);
      })
      .catch(function () {});
  }

  function stopAudioReactive() {
    if (audio.raf) cancelAnimationFrame(audio.raf);
    audio.raf = 0;
    try {
      audio.stream && audio.stream.getTracks().forEach(function (t) {
        t.stop();
      });
    } catch (e) {}
    audio.stream = null;
    try {
      audio.ctx && audio.ctx.close();
    } catch (e) {}
    audio.ctx = null;
  }

  function polishInput() {
    var input =
      document.querySelector(".bottom-bar input[type='text']") ||
      document.querySelector(".bottom-bar .chat-input input") ||
      document.querySelector(".bottom-bar input.chat-input");
    if (!input) return;
    if (input.placeholder !== "Escribe tu mensaje...") {
      input.placeholder = "Escribe tu mensaje...";
    }
    input.setAttribute("aria-label", "Escribe tu mensaje");
    // Quitar Ã­conos extra a la derecha del texto (salvo send)
    var form = input.closest("form, .input-row, .chat-input");
    if (form) {
      form.querySelectorAll("button, span, i").forEach(function (el) {
        if (el.classList.contains("send-btn")) return;
        if (el.tagName === "INPUT") return;
        if (el.closest(".send-btn")) return;
        var aria = (el.getAttribute("aria-label") || "").toLowerCase();
        var txt = (el.textContent || "").trim();
        if (/adjunt|emoji|clip|mic|ðŸ“Ž|ðŸ˜Š|ï¼‹|\+/.test(aria + txt) || el.classList.contains("attach")) {
          el.style.display = "none";
        }
      });
    }
  }

  /* â€”â€”â€” Unidad neuronal de cÃ¡mara â€” ciclo limpio â€”â€”â€” */

  /**
   * Ciclo icono cÃ¡mara:
   * 1) cerrado â†’ TRASERA
   * 2) trasera â†’ SELFIE (espejo)
   * 3) selfie â†’ RECOGER cÃ¡mara â†’ solo modo agente
   */
  function onFooterCameraTap() {
    if (!canCycleCam()) return;
    // v13 aislada: no usa modoInterfaz / Bridge / dictado
    if (window.SalomonCameraV13 && typeof window.SalomonCameraV13.toggle === "function") {
      if (window.SalomonCameraV13.isOpen && window.SalomonCameraV13.isOpen()) {
        window.SalomonCameraV13.close();
      } else {
        try {
          stopCameraCompleto(true);
        } catch (e) {}
        window.SalomonCameraV13.open();
      }
      return;
    }
    // Fallback legacy solo si v13 no cargo
    if (modoInterfaz === "asistente") {
      setModoInterfaz("camara-trasera");
    } else if (modoInterfaz === "camara-trasera") {
      setModoInterfaz("camara-frontal");
    } else {
      setModoInterfaz("asistente");
    }
  }

  function enterSelfieMode() {
    setModoInterfaz("camara-frontal");
  }

  function updateCamActiveBadge() {
    // Pantalla limpia: sin textos de modo
    var badge = document.getElementById("ui-camera-active-badge");
    if (badge) {
      badge.textContent = "";
      badge.setAttribute("aria-hidden", "true");
      badge.style.display = "none";
    }
  }

  function syncCameraUiState() {
    var cam =
      document.querySelector(".controls-row .ui-smart-cam-btn") ||
      document.querySelector(".controls-row .boton-camara") ||
      document.querySelector('.controls-row .control-btn[aria-label="Camara"]');
    var active = isCamMode();
    var selfie = modoInterfaz === "camara-frontal";
    // open solo si hay stream real; opening = esperando getUserMedia
    if (!active) {
      camera.open = false;
      camera.opening = false;
    } else if (camera.stream && camera.videoEl) {
      camera.open = true;
    }
    camera.phase = !active ? "closed" : selfie ? "selfie" : "rear";
    camera.facing = selfie ? "user" : "environment";

    document.documentElement.classList.toggle("salomon-cam-mode", active);
    document.documentElement.classList.toggle("salomon-cam-selfie", selfie);
    document.documentElement.setAttribute("data-modo-interfaz", modoInterfaz);
    if (active) document.documentElement.setAttribute("data-salomon-camera-only", "1");
    else document.documentElement.removeAttribute("data-salomon-camera-only");

    var overlay = document.getElementById("ui-camera-overlay");
    if (overlay) {
      overlay.dataset.facing = selfie ? "user" : "environment";
      overlay.dataset.phase = camera.phase;
      overlay.dataset.modo = modoInterfaz;
      overlay.classList.toggle("is-selfie", selfie);
    }
    if (cam) {
      cam.classList.toggle("is-cam-active", active);
      cam.classList.toggle("is-selfie-phase", selfie);
      cam.dataset.facing = selfie ? "user" : "environment";
      cam.dataset.phase = camera.phase;
      cam.dataset.modo = modoInterfaz;
      cam.removeAttribute("title");
      cam.setAttribute("aria-label", " ");
    }
    var main = document.querySelector(".controls-row .control-btn--main");
    if (main) {
      ensureShutterCamIcon(main);
      main.classList.toggle("is-cam-shutter", active);
      if (active) {
        main.removeAttribute("title");
        main.setAttribute("aria-label", " ");
        main.dataset.captureMode = "1";
        main.dataset.uiMode = "";
        main.classList.remove("voice-btn--spinning", "control-btn--recording");
        main.classList.add("is-cam-live");
        stopAudioReactive();
      } else {
        main.removeAttribute("title");
        main.setAttribute("aria-label", " ");
        main.dataset.captureMode = "0";
        main.classList.remove("is-cam-live", "is-cam-shot");
      }
    }
    var writeBtn = getTextBtn();
    if (writeBtn) {
      writeBtn.toggleAttribute("disabled", active);
      writeBtn.setAttribute("aria-disabled", active ? "true" : "false");
    }
    document.querySelectorAll(".bottom-bar input, .bottom-bar textarea, .bottom-bar .send-btn").forEach(function (el) {
      if (active) {
        el.setAttribute("disabled", "disabled");
        el.setAttribute("tabindex", "-1");
      } else {
        el.removeAttribute("disabled");
        el.removeAttribute("tabindex");
      }
    });
    updateCamActiveBadge();
    applyCameraZoom(camera.zoom || 1);
  }

  function toggleCameraDirection() {
    if (!isCamMode()) {
      setModoInterfaz("camara-trasera");
      return;
    }
    setModoInterfaz(modoInterfaz === "camara-frontal" ? "camara-trasera" : "camara-frontal");
  }

  function swapFacingInPlace(prevFacing) {
    var video = camera.videoEl;
    if (!video || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      // Sin hardware swap: mantener fase selfie + espejo CSS
      camera.flipping = false;
      syncCameraUiState();
      return;
    }
    camera.flipping = true;
    var seq = ++camera.flipSeq;
    var prev = camera.stream;
    var smart = document.getElementById("ui-smart-button");
    if (smart) smart.dataset.flip = "1";
    var want = camera.facing || "user";
    navigator.mediaDevices
      .getUserMedia({
        video: { facingMode: { exact: want } },
        audio: false,
      })
      .catch(function () {
        return navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: want } },
          audio: false,
        });
      })
      .catch(function () {
        // Ãšltimo recurso: cualquier cÃ¡mara; UI sigue en selfie/espejo
        return navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      })
      .then(function (stream) {
        if (seq !== camera.flipSeq || !camera.open) {
          try {
            stream.getTracks().forEach(function (t) {
              t.stop();
            });
          } catch (e) {}
          return;
        }
        camera.stream = stream;
        video.srcObject = stream;
        var play = video.play();
        if (play && typeof play.catch === "function") play.catch(function () {});
        if (prev && prev !== stream) {
          try {
            prev.getTracks().forEach(function (t) {
              t.stop();
            });
          } catch (e) {}
        }
        // Fase selfie se conserva aunque el device no reporte facingMode
        if (modoInterfaz === "camara-frontal") camera.facing = "user";
      })
      .catch(function (err) {
        log("flip error (se mantiene selfie UI)", err && err.message);
        // NO revertir phase a rear: el usuario debe poder cerrar con 1 toque
        if (modoInterfaz === "camara-frontal") camera.facing = "user";
      })
      .then(function () {
        if (seq === camera.flipSeq) camera.flipping = false;
        if (smart) smart.dataset.flip = "0";
        syncCameraUiState();
      });
  }

  function flashShutter(overlay) {
    if (!overlay) return;
    var flash = overlay.querySelector(".ui-camera-flash");
    if (!flash) {
      flash = document.createElement("div");
      flash.className = "ui-camera-flash";
      flash.setAttribute("aria-hidden", "true");
      overlay.appendChild(flash);
    }
    flash.classList.remove("is-on");
    void flash.offsetWidth;
    flash.classList.add("is-on");
    queueMicrotask(function () {
      setTimeout(function () {
        flash.classList.remove("is-on");
      }, 180);
    });
    // Remolino plateado suave en botÃ³n inteligente / mic
    var main = document.querySelector(".controls-row .control-btn--main");
    var smart = document.getElementById("ui-smart-button");
    [main, smart].forEach(function (el) {
      if (!el) return;
      el.classList.remove("is-cam-shot");
      void el.offsetWidth;
      el.classList.add("is-cam-shot");
      setTimeout(function () {
        el.classList.remove("is-cam-shot");
      }, 900);
    });
  }

  function dataUrlToBlob(dataUrl) {
    try {
      var parts = dataUrl.split(",");
      var mime = (parts[0].match(/:(.*?);/) || [])[1] || "image/jpeg";
      var bin = atob(parts[1] || "");
      var arr = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
      return new Blob([arr], { type: mime });
    } catch (e) {
      return null;
    }
  }

  function touchDistance(t0, t1) {
    var dx = t0.clientX - t1.clientX;
    var dy = t0.clientY - t1.clientY;
    return Math.sqrt(dx * dx + dy * dy);
  }

  function clampZoom(z) {
    return Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, z));
  }

  function applyCameraZoom(z) {
    camera.zoom = clampZoom(z);
    var video = camera.videoEl || document.querySelector("#ui-camera-overlay video");
    var stage = document.querySelector("#ui-camera-overlay .ui-camera-stage");
    if (video) {
      video.style.transformOrigin = "center center";
      var mirror = modoInterfaz === "camara-frontal";
      video.style.transform = (mirror ? "scaleX(-1) " : "") + "scale(" + camera.zoom + ")";
    }
    if (stage) stage.dataset.zoom = String(camera.zoom.toFixed(2));

    // Zoom Ã³ptico/hardware si el track lo soporta (cÃ¡mara trasera)
    try {
      var track = camera.stream && camera.stream.getVideoTracks && camera.stream.getVideoTracks()[0];
      if (track && typeof track.getCapabilities === "function") {
        var caps = track.getCapabilities() || {};
        if (caps.zoom) {
          var min = caps.zoom.min || 1;
          var max = caps.zoom.max || ZOOM_MAX;
          var hw = min + ((camera.zoom - ZOOM_MIN) / (ZOOM_MAX - ZOOM_MIN)) * (max - min);
          track.applyConstraints({ advanced: [{ zoom: hw }] }).catch(function () {});
        }
      }
    } catch (e) {}
  }

  function resetCameraZoom() {
    camera.zoom = 1;
    camera.pinch.active = false;
    camera.pinch.moved = false;
    camera.pinch.startDist = 0;
    camera.pinch.startZoom = 1;
    applyCameraZoom(1);
  }

  /** Pellizco en preview: abrir = zoom in Â· cerrar = zoom out (sobre todo trasera) */
  function installPinchZoom(stage) {
    if (!stage || stage.dataset.uiPinch === "1") return;
    stage.dataset.uiPinch = "1";

    function onStart(e) {
      if (!camera.open) return;
      if (!e.touches || e.touches.length < 2) return;
      camera.pinch.active = true;
      camera.pinch.moved = false;
      camera.pinch.startDist = touchDistance(e.touches[0], e.touches[1]);
      camera.pinch.startZoom = camera.zoom || 1;
      if (e.cancelable) e.preventDefault();
      e.stopPropagation();
    }

    function onMove(e) {
      if (!camera.open || !camera.pinch.active) return;
      if (!e.touches || e.touches.length < 2) return;
      if (e.cancelable) e.preventDefault();
      e.stopPropagation();
      var dist = touchDistance(e.touches[0], e.touches[1]);
      if (!camera.pinch.startDist) return;
      var ratio = dist / camera.pinch.startDist;
      if (Math.abs(ratio - 1) > 0.03) camera.pinch.moved = true;
      // Abrir dedos â†’ acerca; cerrar â†’ aleja / normal
      applyCameraZoom(camera.pinch.startZoom * ratio);
    }

    function onEnd(e) {
      if (!camera.pinch.active) return;
      if (e.touches && e.touches.length >= 2) return;
      camera.pinch.active = false;
      // Evitar foto al soltar el pellizco
      if (camera.pinch.moved) {
        lastShotAt = Date.now();
        setTimeout(function () {
          camera.pinch.moved = false;
        }, 320);
      }
    }

    stage.addEventListener("touchstart", onStart, CAPTURE_OPTS);
    stage.addEventListener("touchmove", onMove, CAPTURE_OPTS);
    stage.addEventListener("touchend", onEnd, CAPTURE_OPTS);
    stage.addEventListener("touchcancel", onEnd, CAPTURE_OPTS);
  }

  function capturePhoto() {
    if (!isCamMode() || !camera.open || camera.capturing) return;
    // En selfie permitir foto aunque el flip aÃºn termine (si hay frame)
    var video = camera.videoEl || document.querySelector("#ui-camera-overlay video");
    var overlay = document.getElementById("ui-camera-overlay");
    if (!video || video.readyState < 2) {
      log("capture: video no listo");
      lastShotAt = 0;
      return;
    }
    camera.capturing = true;
    lockAgentOut();
    flashShutter(overlay);
    haptic([6, 12, 6]);
    try {
      var canvas = document.createElement("canvas");
      var vw = video.videoWidth || 720;
      var vh = video.videoHeight || 1280;
      canvas.width = vw;
      canvas.height = vh;
      var ctx = canvas.getContext("2d");
      var selfie = modoInterfaz === "camara-frontal";
      var z = clampZoom(camera.zoom || 1);
      var sw = vw / z;
      var sh = vh / z;
      var sx = (vw - sw) / 2;
      var sy = (vh - sh) / 2;
      if (selfie) {
        ctx.translate(canvas.width, 0);
        ctx.scale(-1, 1);
      }
      ctx.drawImage(video, sx, sy, sw, sh, 0, 0, vw, vh);
      var dataUrl = canvas.toDataURL("image/jpeg", 0.88);
      var blob = dataUrlToBlob(dataUrl);
      camera.capturing = false;
      if (!blob) return;
      var detail = {
        blob: blob,
        facing: selfie ? "user" : camera.facing,
        mode: camera.mode || "photo",
        width: canvas.width,
        height: canvas.height,
        dataUrl: dataUrl,
        deferChat: true,
        cameraOnly: true,
        phase: camera.phase,
        zoom: z,
      };
      window.dispatchEvent(new CustomEvent("salomon:ui-photo", { detail: detail }));
      log("foto OK (agente bloqueado)", detail.facing, camera.phase);
    } catch (e) {
      camera.capturing = false;
      lastShotAt = 0;
      log("capture fail", e && e.message);
    }
  }

  /** Nodo overlay = disparador */
  function wireSmartButton(btn) {
    if (!btn || btn.dataset.neuralBound === "1") return;
    btn.dataset.neuralBound = "1";

    function shoot(e) {
      if (!isPrimaryGesture(e)) return;
      if (e.cancelable) e.preventDefault();
      e.stopImmediatePropagation();
      e.stopPropagation();
      if (!canTakeShot()) return;
      capturePhoto();
    }

    ["touchend", "pointerup", "click"].forEach(function (type) {
      btn.addEventListener(type, shoot, type === "click" ? true : CAPTURE_OPTS);
    });
  }

  /** Preview: toque = disparo (solo si modoInterfaz es camara-*) */
  function bindStageShutter(stage) {
    unbindStageShutter();
    function onTap(ev) {
      if (!isCamMode()) return;
      if (camera.pinch.active || camera.pinch.moved) return;
      if (ev.target && ev.target.closest && ev.target.closest(".ui-smart-button, .ui-camera-close")) {
        return;
      }
      if (!isPrimaryGesture(ev)) return;
      if (ev.cancelable) ev.preventDefault();
      ev.stopImmediatePropagation();
      ev.stopPropagation();
      if (!canTakeShot()) return;
      capturePhoto();
    }
    camera.stageEl = stage;
    camera.stageTapHandler = onTap;
    ["touchend", "pointerup", "click"].forEach(function (type) {
      stage.addEventListener(type, onTap, type === "click" ? true : CAPTURE_OPTS);
    });
  }

  function unbindStageShutter() {
    if (camera.stageEl && camera.stageTapHandler) {
      var stage = camera.stageEl;
      var onTap = camera.stageTapHandler;
      ["touchend", "pointerup", "click"].forEach(function (type) {
        try {
          stage.removeEventListener(type, onTap, type === "click" ? true : CAPTURE_OPTS);
        } catch (e) {}
      });
    }
    camera.stageEl = null;
    camera.stageTapHandler = null;
  }

  function openNeuralCamera(opts) {
    opts = opts || {};
    if (opts.mode) camera.mode = opts.mode;
    if (opts.facing) camera.facing = opts.facing;
    else if (!opts.keepFacing && !camera.open) {
      camera.facing = "environment";
    }
    stopCameraCompleto(true);
    pauseChatForCapture();
    installCaptureEventWall();
    camera.opening = true;
    camera.open = false;
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      log("camara no disponible");
      camera.opening = false;
      modoInterfaz = "asistente";
      document.documentElement.setAttribute("data-modo-interfaz", "asistente");
      document.documentElement.classList.remove("salomon-cam-mode", "salomon-cam-selfie");
      unlockAgent();
      syncCameraUiState();
      return;
    }
    var seq = ++camera.openSeq;
    haptic(10);
    var facing = camera.facing || "environment";
    navigator.mediaDevices
      .getUserMedia({
        video: { facingMode: { exact: facing } },
        audio: false,
      })
      .catch(function () {
        return navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: facing } },
          audio: false,
        });
      })
      .then(function (stream) {
        if (seq !== camera.openSeq) {
          try {
            stream.getTracks().forEach(function (t) {
              t.stop();
            });
          } catch (e) {}
          return;
        }
        camera.stream = stream;
        camera.open = true;
        camera.opening = false;
        camera.flipping = false;
        if (modoInterfaz === "camara-frontal") {
          camera.phase = "selfie";
          camera.facing = "user";
        } else {
          modoInterfaz = "camara-trasera";
          camera.phase = "rear";
          camera.facing = "environment";
        }
        pauseChatForCapture();

        var overlay = document.createElement("div");
        overlay.className = "ui-camera-overlay neural-camera";
        overlay.id = "ui-camera-overlay";
        overlay.dataset.mode = camera.mode || "photo";
        overlay.setAttribute("data-salomon-layer", "camera");
        overlay.setAttribute("aria-hidden", "false");

        var video = document.createElement("video");
        video.playsInline = true;
        video.muted = true;
        video.autoplay = true;
        video.setAttribute("playsinline", "true");
        video.setAttribute("webkit-playsinline", "true");
        video.srcObject = stream;
        video.play().catch(function () {});
        camera.videoEl = video;

        var flash = document.createElement("div");
        flash.className = "ui-camera-flash";
        flash.setAttribute("aria-hidden", "true");

        var stage = document.createElement("div");
        stage.className = "ui-camera-stage";
        stage.appendChild(video);
        bindStageShutter(stage);
        installPinchZoom(stage);
        resetCameraZoom();

        var smart = document.createElement("button");
        smart.type = "button";
        smart.className = "ui-smart-button";
        smart.id = "ui-smart-button";
        smart.setAttribute("aria-label", " ");
        smart.removeAttribute("title");
        smart.innerHTML =
          '<span class="ui-smart-button__ring-plata" aria-hidden="true"></span>' +
          '<span class="ui-smart-button__swirl" aria-hidden="true"></span>' +
          '<span class="ui-smart-button__ring" aria-hidden="true"></span>' +
          '<span class="ui-smart-button__core ui-smart-button__core--shutter" aria-hidden="true"></span>';
        wireSmartButton(smart);

        var closeBtn = document.createElement("button");
        closeBtn.type = "button";
        closeBtn.className = "ui-camera-close";
        closeBtn.setAttribute("aria-label", "Cerrar");
        closeBtn.innerHTML = "<span aria-hidden=\"true\">Ã—</span>";
        closeBtn.addEventListener(
          "touchstart",
          function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            closeCamera();
          },
          CAPTURE_OPTS
        );
        closeBtn.addEventListener(
          "click",
          function (e) {
            e.preventDefault();
            e.stopPropagation();
            closeCamera();
          },
          true
        );

        overlay.appendChild(stage);
        overlay.appendChild(flash);
        overlay.appendChild(smart);
        overlay.appendChild(closeBtn);
        document.body.appendChild(overlay);
        syncCameraUiState();
        syncWritingUiState();

        queueMicrotask(function () {
          document.querySelectorAll(".camera-modal, .camera-backdrop, .camera-view").forEach(function (n) {
            n.style.display = "none";
            n.setAttribute("aria-hidden", "true");
          });
        });

        window.dispatchEvent(
          new CustomEvent("salomon:camera-open", {
            detail: { facing: camera.facing, mode: camera.mode },
          })
        );
      })
      .catch(function (err) {
        if (seq !== camera.openSeq) return;
        log("cÃ¡mara error", err && err.name, err && err.message);
        camera.open = false;
        camera.opening = false;
        camera.videoEl = null;
        modoInterfaz = "asistente";
        camera.phase = "closed";
        document.documentElement.classList.remove("salomon-cam-mode", "salomon-cam-selfie");
        document.documentElement.setAttribute("data-modo-interfaz", "asistente");
        unlockAgent();
        syncCameraUiState();
      });
  }

  /** CAPA 2 — detener tracks, desmontar overlay, sin listeners colgantes */
  function stopCameraCompleto(silent) {
    camera.openSeq += 1;
    camera.flipSeq += 1;
    unbindStageShutter();

    var overlay = document.getElementById("ui-camera-overlay");
    if (overlay) {
      try {
        overlay.querySelectorAll("video").forEach(function (v) {
          try {
            v.srcObject = null;
            v.removeAttribute("src");
            v.load();
          } catch (e) {}
        });
      } catch (e) {}
      overlay.remove();
    }

    if (camera.stream) {
      try {
        camera.stream.getTracks().forEach(function (t) {
          try {
            t.stop();
          } catch (e) {}
        });
      } catch (e) {}
    }
    camera.stream = null;
    camera.open = false;
    camera.opening = false;
    camera.capturing = false;
    camera.flipping = false;
    camera.videoEl = null;
    camera.phase = "closed";
    camera.zoom = 1;
    camera.pinch.active = false;
    camera.pinch.moved = false;
    if (!silent) {
      camera.facing = "environment";
      modoInterfaz = "asistente";
      document.documentElement.setAttribute("data-modo-interfaz", "asistente");
    }
    document.documentElement.classList.remove("salomon-cam-mode", "salomon-cam-selfie");
    if (!silent) unlockAgent();
    syncCameraUiState();
    if (!silent) {
      window.dispatchEvent(new CustomEvent("salomon:camera-close"));
      log("CAPA2: stream detenido + overlay off → asistente limpio");
    }
  }

  function closeCamera(silent) {
    stopCameraCompleto(silent);
  }

  function cycleCamera() {
    onFooterCameraTap();
  }
  function openCamera() {
    if (!isCamMode()) setModoInterfaz("camara-trasera");
  }
  function captureFromVideo() {
    capturePhoto();
  }

  /* â€”â€”â€” Burbujas: long-press menÃº â€”â€”â€” */
  function wireBubbles() {
    document.querySelectorAll(".bubble, .bubble-row .bubble").forEach(function (bubble) {
      if (bubble.dataset.uiMenu === "1") return;
      bubble.dataset.uiMenu = "1";
      var holdTimer = null;
      var startX = 0;
      var startY = 0;

      function textOf() {
        var t = bubble.querySelector(".bubble__text");
        return ((t && t.textContent) || bubble.textContent || "").trim();
      }

      bubble.addEventListener("pointerdown", function (e) {
        startX = e.clientX;
        startY = e.clientY;
        holdTimer = setTimeout(function () {
          showBubbleMenu(bubble, textOf(), e.clientX, e.clientY);
        }, 480);
      });
      bubble.addEventListener("pointermove", function (e) {
        if (Math.abs(e.clientX - startX) > 12 || Math.abs(e.clientY - startY) > 12) {
          clearTimeout(holdTimer);
        }
      });
      bubble.addEventListener("pointerup", function () {
        clearTimeout(holdTimer);
      });
      bubble.addEventListener("pointercancel", function () {
        clearTimeout(holdTimer);
      });
      bubble.addEventListener("contextmenu", function (e) {
        e.preventDefault();
        showBubbleMenu(bubble, textOf(), e.clientX, e.clientY);
      });
    });
  }

  function showBubbleMenu(bubble, text, x, y) {
    hideBubbleMenu();
    haptic(14);
    var menu = document.createElement("div");
    menu.className = "ui-bubble-menu";
    menu.id = "ui-bubble-menu";
    menu.innerHTML =
      '<button type="button" data-act="copy">Copiar mensaje</button>' +
      '<button type="button" data-act="forward">Reenviar</button>' +
      '<button type="button" data-act="share">Compartir</button>';
    document.body.appendChild(menu);
    var rect = menu.getBoundingClientRect();
    var left = Math.min(window.innerWidth - rect.width - 10, Math.max(10, x - rect.width / 2));
    var top = Math.min(window.innerHeight - rect.height - 10, Math.max(10, y - 8));
    menu.style.left = left + "px";
    menu.style.top = top + "px";

    menu.addEventListener("click", function (e) {
      var btn = e.target.closest("button");
      if (!btn) return;
      var act = btn.getAttribute("data-act");
      if (act === "copy") {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).catch(function () {});
        } else {
          window.prompt("Copia el mensaje:", text);
        }
      } else if (act === "forward") {
        var input =
          document.querySelector(".bottom-bar input[type='text']") ||
          document.querySelector(".bottom-bar .chat-input input");
        var textBtn = document.querySelector('.controls-row .control-btn[aria-label="Texto"]');
        if (textBtn) textBtn.click();
        setTimeout(function () {
          var inp =
            document.querySelector(".bottom-bar input[type='text']") ||
            document.querySelector(".bottom-bar .chat-input input");
          if (inp) {
            var proto = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value");
            if (proto && proto.set) proto.set.call(inp, text);
            else inp.value = text;
            inp.dispatchEvent(new Event("input", { bubbles: true }));
            inp.focus();
          }
        }, 120);
      } else if (act === "share") {
        if (navigator.share) {
          navigator.share({ text: text }).catch(function () {});
        } else if (navigator.clipboard) {
          navigator.clipboard.writeText(text).catch(function () {});
        }
      }
      hideBubbleMenu();
    });

    setTimeout(function () {
      document.addEventListener("pointerdown", outsideMenu, true);
    }, 10);
  }

  function outsideMenu(e) {
    var menu = document.getElementById("ui-bubble-menu");
    if (menu && !menu.contains(e.target)) hideBubbleMenu();
  }

  function hideBubbleMenu() {
    var menu = document.getElementById("ui-bubble-menu");
    if (menu) menu.remove();
    document.removeEventListener("pointerdown", outsideMenu, true);
  }

  /* â€”â€”â€” Drawer titles sync â€”â€”â€” */
  function polishDrawers() {
    document.querySelectorAll(".glass-panel").forEach(function (panel) {
      var isLeft = panel.classList.contains("glass-panel--left");
      // Tras swap visual: click izq abre tools (panel derecho React)â€¦
      // Actualizamos tÃ­tulos cuando el panel existe.
      var h2 = panel.querySelector(".glass-panel__header h2");
      if (!h2) return;
      if (isLeft) {
        // Panel izquierdo React = cuenta (se abre desde botÃ³n derecho UI)
        if (h2.textContent === "Correo" || h2.textContent === "Herramientas") {
          h2.textContent = "Cuenta y Planes";
        }
      } else {
        if (h2.textContent === "Herramientas" || h2.textContent === "Correo") {
          h2.textContent = "Herramientas";
        }
      }
      panel.setAttribute("aria-label", h2.textContent);
    });
  }

  function tick() {
    styleHeader();
    enhanceControls();
    stampEstructuraClasses();
    wireBubbles();
    polishDrawers();
    syncLogoState();
    syncWritingUiState();
  }

  function boot() {
    document.documentElement.classList.add("salomon-ui-shield");
    document.documentElement.classList.add("salomon-mockup-ui");
    installCaptureEventWall();
    tick();
    var n = 0;
    var id = setInterval(function () {
      tick();
      n += 1;
      if (n >= 20) clearInterval(id);
    }, 400);
    window.addEventListener("salomon:bridge-state", function () {
      syncLogoState();
    });
    window.addEventListener("salomon:ready", tick);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if (isCamMode()) setModoInterfaz("asistente");
        else if (isWritingOpen()) closeWritingIfOpen();
      }
    });
    // Observa montaje/desmontaje del panel de escritura (React)
    try {
      var root = document.getElementById("root") || document.body;
      var mo = new MutationObserver(function () {
        syncWritingUiState();
      });
      mo.observe(root, { childList: true, subtree: true });
    } catch (e) {}
    log("activo modo-interfaz-291");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.SalomonUIShield = {
    version: "modo-interfaz-291",
    getModoInterfaz: getModoInterfaz,
    setModoInterfaz: setModoInterfaz,
    isCamMode: isCamMode,
    cycleCamera: cycleCamera,
    closeCamera: closeCamera,
    stopCameraCompleto: stopCameraCompleto,
    openNeuralCamera: openNeuralCamera,
    toggleCameraDirection: toggleCameraDirection,
    capturePhoto: capturePhoto,
    syncCameraUiState: syncCameraUiState,
    syncWritingUiState: syncWritingUiState,
    applyCameraZoom: applyCameraZoom,
  };
})();


