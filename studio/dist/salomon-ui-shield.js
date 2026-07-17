/**
 * Salomón AI Studio — UI Shield v1
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
    phase: "closed", // closed | rear | selfie — ciclo UI (no depende del hardware)
    open: false,
    capturing: false,
    flipping: false,
    mode: "photo",
    videoEl: null,
    openSeq: 0,
    flipSeq: 0,
    agentLockTimer: 0,
  };
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
    if (!camera.open || camera.capturing) return false;
    // Selfie: permitir foto aunque flipping aún corra (si hay video)
    if (camera.flipping && camera.phase !== "selfie") return false;
    lastShotAt = now;
    return true;
  }

  function canCycleCam() {
    var now = Date.now();
    if (now - lastCamTap < CAM_CYCLE_MS) return false;
    if (camera.flipping || camera.capturing) return false;
    lastCamTap = now;
    return true;
  }

  /** Solo un evento “útil” por gesto táctil (evita touchend+click doble) */
  function isPrimaryGesture(e) {
    if (!e) return false;
    if (e.type === "touchend") return true;
    if (e.type === "pointerup") {
      if (e.pointerType === "touch") return false; // ya hubo touchend
      return true; // mouse / pen
    }
    if (e.type === "click") {
      if (e.pointerType === "touch") return false;
      // click sintético tras touch: detail suele ser 1; si hubo touch reciente, ignorar
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

  /* ——— Header: H izq (tools) / Perfil der (cuenta) + swap de clicks ——— */
  function styleHeader() {
    var header = document.querySelector(".studio-header");
    if (!header) return false;
    var btns = header.querySelectorAll(".header-menu-btn");
    if (btns.length < 2) return false;

    // Ocultar subtítulo
    var sub = header.querySelector(".logo-subtitle");
    if (sub) sub.style.display = "none";

    // Iconos
    injectHeaderIcon(btns[0], "h", ICON_H, "Herramientas");
    injectHeaderIcon(btns[1], "user", ICON_USER, "Cuenta y Planes");

    // Swap: React left=account, right=tools → UI left=tools, right=account
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

  /* ——— Bottom controls: camera / voice fx / text ——— */
  function enhanceControls() {
    var row = document.querySelector(".controls-row");
    if (!row) return false;
    var btns = row.querySelectorAll(".control-btn");
    if (btns.length < 3) return false;

    var cam = btns[0];
    var main = row.querySelector(".control-btn--main") || btns[1];
    var textBtn = btns[btns.length - 1];

    // Ciclo cámara: cerrado → trasera → selfie → cerrado (un solo gesto)
    if (cam.dataset.uiCam !== "1") {
      cam.dataset.uiCam = "1";
      cam.classList.add("ui-smart-cam-btn", "boton-camara");
      cam.setAttribute("aria-label", "Cámara");
      cam.title = "Cámara — trasera → selfie → cerrar";
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
          if (camera.open && !writeLock) {
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
    // CAPTURA manda: si el form de chat sigue en DOM, cerrar solo escritura (no apagar captura)
    if (open && camera.open) {
      closeWritingIfOpen();
      open = isWritingOpen();
    }
    if (textBtn) {
      textBtn.classList.add("ui-write-btn");
      textBtn.classList.toggle("is-write-active", open && !camera.open);
      textBtn.setAttribute("aria-label", "Texto");
      textBtn.title =
        camera.open ? "Escritura bloqueada (modo captura)" : open ? "Cerrar escritura" : "Escribe tu mensaje";
    }
    document.documentElement.classList.toggle("salomon-write-mode", open && !camera.open);
    if (!camera.open) polishInput();
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
    try {
      window.dispatchEvent(new CustomEvent("salomon:camera-agent-lock", { detail: { lock: false } }));
    } catch (e) {}
  }

  /** Controles permitidos en CAPTURA (resto del DOM = muro) */
  function isCaptureExemptTarget(t) {
    if (!t || !t.closest) return false;
    return !!(
      t.closest(".control-btn--main") ||
      t.closest(".voice-btn-wrap") ||
      t.closest(".boton-central") ||
      t.closest(".ui-smart-cam-btn") ||
      t.closest(".boton-camara") ||
      t.closest('.control-btn[aria-label="Cámara"]') ||
      t.closest(".ui-write-btn") ||
      t.closest(".boton-texto") ||
      t.closest(".ui-camera-close") ||
      t.closest("#ui-smart-button") ||
      t.closest(".ui-smart-button") ||
      t.closest("#salomon-update-btn") ||
      t.closest(".salomon-update-slot")
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
   * Gatillo de pantalla solo sobre preview/área de cámara (no footer).
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
      if (!camera.open) return;
      if (isCaptureExemptTarget(e.target)) return;
      if (e.cancelable) e.preventDefault();
      e.stopImmediatePropagation();
      e.stopPropagation();
    }
    blockTypes.forEach(function (type) {
      document.addEventListener(type, blockChat, CAPTURE_OPTS);
    });

    function onScreenShutter(e) {
      if (!camera.open) return;
      if (isCaptureExemptTarget(e.target)) return;
      if (!isPrimaryGesture(e)) return;
      if (!isScreenShutterTarget(e.target)) return;
      if (e.cancelable) e.preventDefault();
      e.stopImmediatePropagation();
      e.stopPropagation();
      if (!canTakeShot()) return;
      log("pantalla → capturePhoto");
      capturePhoto();
    }
    document.addEventListener("touchend", onScreenShutter, CAPTURE_OPTS);
    document.addEventListener("pointerup", onScreenShutter, CAPTURE_OPTS);

    if (document.documentElement.dataset.uiCamVol !== "1") {
      document.documentElement.dataset.uiCamVol = "1";
      function onVolume(e) {
        if (!camera.open) return;
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
          log("volumen → capturePhoto");
          capturePhoto();
        }
      }
      document.addEventListener("keydown", onVolume, true);
      document.addEventListener("keyup", onVolume, true);
    }
    log("muro CAPTURA + gatillos pantalla/volumen v2");
  }

  /** Botón central / mic = disparador con icono cámara */
  function wireMainShutterGate(main) {
    if (!main || main.dataset.uiShutterGate === "1") return;
    main.dataset.uiShutterGate = "1";
    var wrap = main.closest(".voice-btn-wrap") || main;
    var targets = wrap === main ? [main] : [wrap, main];

    function gate(e) {
      if (!camera.open) return;
      if (!isPrimaryGesture(e)) return;
      if (e.cancelable) e.preventDefault();
      e.stopImmediatePropagation();
      e.stopPropagation();
      if (!canTakeShot()) return;
      log("mic/shutter → capturePhoto (facing=" + camera.facing + ")");
      capturePhoto();
    }

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
        if (camera.open) {
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
            if (Date.now() - lastTap >= 300 && !camera.open) {
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
          // Suave → lento; fuerte → agitado
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
    // Quitar íconos extra a la derecha del texto (salvo send)
    var form = input.closest("form, .input-row, .chat-input");
    if (form) {
      form.querySelectorAll("button, span, i").forEach(function (el) {
        if (el.classList.contains("send-btn")) return;
        if (el.tagName === "INPUT") return;
        if (el.closest(".send-btn")) return;
        var aria = (el.getAttribute("aria-label") || "").toLowerCase();
        var txt = (el.textContent || "").trim();
        if (/adjunt|emoji|clip|mic|📎|😊|＋|\+/.test(aria + txt) || el.classList.contains("attach")) {
          el.style.display = "none";
        }
      });
    }
  }

  /* ——— Unidad neuronal de cámara — ciclo limpio ——— */

  /**
   * Ciclo icono cámara:
   * 1) cerrado → TRASERA
   * 2) trasera → SELFIE (espejo)
   * 3) selfie → RECOGER cámara → solo modo agente
   */
  function onFooterCameraTap() {
    if (!canCycleCam()) return;

    if (camera.phase === "closed" || !camera.open) {
      pauseChatForCapture();
      camera.phase = "rear";
      camera.facing = "environment";
      openNeuralCamera({ mode: "photo", facing: "environment", keepFacing: true });
      return;
    }

    if (camera.phase === "rear") {
      enterSelfieMode();
      return;
    }

    // selfie (u otra): un toque recoge la cámara → modo agente
    log("selfie → recoger cámara (modo agente)");
    closeCamera();
  }

  function enterSelfieMode() {
    camera.phase = "selfie";
    camera.facing = "user";
    log("ciclo → selfie (espejo)");
    haptic(8);
    syncCameraUiState();
    // Aplicar espejo de inmediato (aunque el stream tarde)
    var overlay = document.getElementById("ui-camera-overlay");
    if (overlay) {
      overlay.dataset.facing = "user";
      overlay.classList.add("is-selfie");
    }
    swapFacingInPlace("environment");
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
      document.querySelector('.controls-row .control-btn[aria-label="Cámara"]');
    var active = !!camera.open;
    var selfie = active && (camera.phase === "selfie" || camera.facing === "user");
    document.documentElement.classList.toggle("salomon-cam-mode", active);
    document.documentElement.classList.toggle("salomon-cam-selfie", selfie);
    if (active) document.documentElement.setAttribute("data-salomon-camera-only", "1");
    else document.documentElement.removeAttribute("data-salomon-camera-only");

    var overlay = document.getElementById("ui-camera-overlay");
    if (overlay) {
      overlay.dataset.facing = selfie ? "user" : "environment";
      overlay.dataset.phase = camera.phase || (active ? "rear" : "closed");
      overlay.classList.toggle("is-selfie", selfie);
    }
    if (cam) {
      cam.classList.toggle("is-cam-active", active);
      cam.classList.toggle("is-selfie-phase", selfie);
      cam.dataset.facing = selfie ? "user" : "environment";
      cam.dataset.phase = camera.phase || "closed";
      if (!active) {
        cam.title = "";
        cam.setAttribute("aria-label", "Cámara");
      } else if (selfie) {
        cam.title = "";
        cam.setAttribute("aria-label", "Cámara");
      } else {
        cam.title = "";
        cam.setAttribute("aria-label", "Cámara");
      }
    }
    var main = document.querySelector(".controls-row .control-btn--main");
    if (main) {
      ensureShutterCamIcon(main);
      main.classList.toggle("is-cam-shutter", active);
      if (active) {
        main.title = "";
        main.setAttribute("aria-label", "Disparar");
        main.dataset.captureMode = "1";
        main.dataset.uiMode = "";
        main.classList.remove("voice-btn--spinning", "control-btn--recording");
        main.classList.add("is-cam-live");
      } else {
        main.title = "";
        main.setAttribute("aria-label", "Núcleo Salomón");
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
  }

  function toggleCameraDirection() {
    if (!camera.open) {
      openNeuralCamera({ mode: camera.mode || "photo" });
      return;
    }
    if (camera.flipping || camera.capturing) return;
    var next = camera.facing === "environment" ? "user" : "environment";
    var prevFacing = camera.facing;
    camera.facing = next;
    log("facing →", camera.facing);
    haptic(8);
    syncCameraUiState();
    swapFacingInPlace(prevFacing);
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
        // Último recurso: cualquier cámara; UI sigue en selfie/espejo
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
        if (camera.phase === "selfie") camera.facing = "user";
      })
      .catch(function (err) {
        log("flip error (se mantiene selfie UI)", err && err.message);
        // NO revertir phase a rear: el usuario debe poder cerrar con 1 toque
        if (camera.phase === "selfie") camera.facing = "user";
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
    // Remolino plateado suave en botón inteligente / mic
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

  function capturePhoto() {
    if (!camera.open || camera.capturing) return;
    // En selfie permitir foto aunque el flip aún termine (si hay frame)
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
      canvas.width = video.videoWidth || 720;
      canvas.height = video.videoHeight || 1280;
      var ctx = canvas.getContext("2d");
      var selfie = camera.phase === "selfie" || camera.facing === "user";
      if (selfie) {
        ctx.translate(canvas.width, 0);
        ctx.scale(-1, 1);
      }
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
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

  /** Preview: toque = disparo (refuerzo; muro document también cubre) */
  function bindStageShutter(stage) {
    function onTap(ev) {
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
    ["touchend", "pointerup", "click"].forEach(function (type) {
      stage.addEventListener(type, onTap, type === "click" ? true : CAPTURE_OPTS);
    });
  }

  function openNeuralCamera(opts) {
    opts = opts || {};
    if (opts.mode) camera.mode = opts.mode;
    if (opts.facing) camera.facing = opts.facing;
    else if (!opts.keepFacing && !camera.open) {
      camera.facing = "environment";
    }
    closeCamera(true);
    pauseChatForCapture();
    installCaptureEventWall();
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      log("cámara no disponible");
      document.documentElement.classList.remove("salomon-cam-mode");
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
        camera.flipping = false;
        if (!camera.phase || camera.phase === "closed") camera.phase = "rear";
        pauseChatForCapture();

        var overlay = document.createElement("div");
        overlay.className = "ui-camera-overlay neural-camera";
        overlay.id = "ui-camera-overlay";
        overlay.dataset.mode = camera.mode || "photo";

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

        var smart = document.createElement("button");
        smart.type = "button";
        smart.className = "ui-smart-button";
        smart.id = "ui-smart-button";
        smart.setAttribute("aria-label", "Disparar");
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
        closeBtn.innerHTML = "<span aria-hidden=\"true\">×</span>";
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
        log("cámara error", err && err.name, err && err.message);
        camera.open = false;
        camera.videoEl = null;
        document.documentElement.classList.remove("salomon-cam-mode");
        syncCameraUiState();
      });
  }

  function closeCamera(silent) {
    camera.openSeq += 1;
    camera.flipSeq += 1;
    var overlay = document.getElementById("ui-camera-overlay");
    if (overlay) overlay.remove();
    if (camera.stream) {
      try {
        camera.stream.getTracks().forEach(function (t) {
          t.stop();
        });
      } catch (e) {}
    }
    camera.stream = null;
    camera.open = false;
    camera.capturing = false;
    camera.flipping = false;
    camera.videoEl = null;
    camera.phase = "closed";
    if (!silent) camera.facing = "environment";
    document.documentElement.classList.remove("salomon-cam-mode", "salomon-cam-selfie");
    if (!silent) unlockAgent();
    syncCameraUiState();
    if (!silent) {
      window.dispatchEvent(new CustomEvent("salomon:camera-close"));
      log("cámara recogida → modo agente");
    }
  }

  function cycleCamera() {
    onFooterCameraTap();
  }
  function openCamera() {
    if (!camera.open) {
      camera.facing = "environment";
      openNeuralCamera({ mode: "photo", facing: "environment", keepFacing: true });
    }
  }
  function captureFromVideo() {
    capturePhoto();
  }

  /* ——— Burbujas: long-press menú ——— */
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

  /* ——— Drawer titles sync ——— */
  function polishDrawers() {
    document.querySelectorAll(".glass-panel").forEach(function (panel) {
      var isLeft = panel.classList.contains("glass-panel--left");
      // Tras swap visual: click izq abre tools (panel derecho React)…
      // Actualizamos títulos cuando el panel existe.
      var h2 = panel.querySelector(".glass-panel__header h2");
      if (!h2) return;
      if (isLeft) {
        // Panel izquierdo React = cuenta (se abre desde botón derecho UI)
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
        if (camera.open) closeCamera();
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
    log("activo cam-clean-260");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.SalomonUIShield = {
    version: "cam-clean-260",
    cycleCamera: cycleCamera,
    closeCamera: closeCamera,
    openNeuralCamera: openNeuralCamera,
    toggleCameraDirection: toggleCameraDirection,
    capturePhoto: capturePhoto,
    syncCameraUiState: syncCameraUiState,
    syncWritingUiState: syncWritingUiState,
  };
})();


