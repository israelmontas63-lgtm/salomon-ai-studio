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
    facing: "user", // selfie por defecto (facingMode: user)
    open: false,
    capturing: false,
    flipping: false,
    mode: "photo", // photo | vdcp
    videoEl: null,
    openSeq: 0,
    flipSeq: 0,
  };
  var audio = { ctx: null, analyser: null, src: null, raf: 0, stream: null };
  var swapLock = false;
  var writeLock = false;
  var closingWrite = false;
  var lastTap = 0;
  var lastCamTap = 0;
  var HOLD_CAPTURE_MS = 500;
  var CAPTURE_OPTS = { capture: true, passive: false };

  function log() {
    try {
      console.info.apply(console, ["[UI Shield]"].concat([].slice.call(arguments)));
    } catch (e) {}
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

    // Cámara legacy (shield overlay) — Chat permanece montado; aislamiento por z-index
    if (cam.dataset.uiCam !== "1") {
      cam.dataset.uiCam = "1";
      cam.classList.add("ui-smart-cam-btn");
      cam.setAttribute("aria-label", "Cámara");
      cam.title = "Abrir cámara";
      cam.addEventListener(
        "click",
        function (e) {
          e.preventDefault();
          e.stopImmediatePropagation();
          onFooterCameraTap();
        },
        true
      );
    }

    // Escritura (Aa): bloqueada en CAPTURA; en CHAT React togglea el panel
    if (textBtn.dataset.uiText !== "1") {
      textBtn.dataset.uiText = "1";
      textBtn.classList.add("ui-write-btn");
      textBtn.setAttribute("aria-label", "Texto");
      textBtn.addEventListener(
        "click",
        function (e) {
          // writeLock = cierre forzado del panel mientras CAPTURA (dejar pasar a React)
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

    // Voz/disparador central: gate de exclusividad CAPTURA vs CHAT
    if (main) {
      ensureVoiceFx(main);
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

  /** Cancela chat/voz antes de entrar en modo Captura */
  function pauseChatForCapture() {
    closeWritingIfOpen();
    stopAudioReactive();
    try {
      if (window.SalomonBridge && typeof window.SalomonBridge.cancelAll === "function") {
        window.SalomonBridge.cancelAll("camera-capture-mode");
      }
    } catch (e) {}
    var main = document.querySelector(".controls-row .control-btn--main");
    if (main) {
      main.dataset.uiMode = "";
      main.classList.remove("voice-btn--spinning", "control-btn--recording");
      main.removeAttribute("data-button-state");
    }
    document.documentElement.classList.add("salomon-cam-mode");
  }

  /** Controles permitidos en CAPTURA (resto del DOM = muro de eventos) */
  function isCaptureExemptTarget(t) {
    if (!t || !t.closest) return false;
    return !!(
      t.closest(".control-btn--main") ||
      t.closest(".voice-btn-wrap") ||
      t.closest(".ui-smart-cam-btn") ||
      t.closest('.control-btn[aria-label="Cámara"]') ||
      t.closest(".ui-camera-close") ||
      t.closest("#ui-smart-button") ||
      t.closest(".ui-smart-button") ||
      t.closest("#salomon-update-btn") ||
      t.closest(".salomon-update-slot")
    );
  }

  /**
   * Muro total: con cámara activa, todo toque fuera del disparador/cierres
   * recibe preventDefault + stopPropagation (el chat/React no ve el gesto).
   */
  function installCaptureEventWall() {
    if (document.documentElement.dataset.uiCamWall === "1") return;
    document.documentElement.dataset.uiCamWall = "1";
    var types = [
      "touchstart",
      "touchend",
      "touchmove",
      "pointerdown",
      "pointerup",
      "pointermove",
      "click",
      "mousedown",
      "mouseup",
    ];
    function wall(e) {
      if (!camera.open) return;
      if (isCaptureExemptTarget(e.target)) return;
      if (e.cancelable) e.preventDefault();
      e.stopImmediatePropagation();
      e.stopPropagation();
    }
    types.forEach(function (type) {
      document.addEventListener(type, wall, CAPTURE_OPTS);
    });
    log("muro de eventos CAPTURA instalado");
  }

  /**
   * Botón grande → exclusivamente capturePhoto() si cámara activa.
   * React VoiceButton no recibe el gesto.
   */
  function wireMainShutterGate(main) {
    if (!main || main.dataset.uiShutterGate === "1") return;
    main.dataset.uiShutterGate = "1";
    var wrap = main.closest(".voice-btn-wrap") || main;
    var lastShot = 0;
    var targets = wrap === main ? [main] : [wrap, main];

    function gate(e) {
      if (!camera.open) return; // modo CHAT
      if (e.cancelable) e.preventDefault();
      e.stopImmediatePropagation();
      e.stopPropagation();
      if (e.type === "pointerup" || e.type === "touchend" || e.type === "click") return;
      if (e.type === "pointerdown" && e.pointerType === "touch") return;
      var now = Date.now();
      if (now - lastShot < 480) return;
      lastShot = now;
      log("disparador → capturePhoto (facing=" + camera.facing + ")");
      capturePhoto();
    }

    ["touchstart", "pointerdown", "touchend", "pointerup", "click"].forEach(function (type) {
      targets.forEach(function (el) {
        el.addEventListener(type, gate, CAPTURE_OPTS);
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

  /* ——— Unidad neuronal de cámara — latencia ultra-baja ——— */

  function onFooterCameraTap() {
    var now = Date.now();
    if (now - lastCamTap < 380) return;
    lastCamTap = now;
    if (camera.flipping || camera.capturing) return;
    // Toggle: abierto → cerrar al instante; cerrado → abrir trasera
    if (camera.open) {
      closeCamera();
      return;
    }
    pauseChatForCapture();
    openNeuralCamera({ mode: "photo" });
  }

  function updateCamActiveBadge() {
    var badge = document.getElementById("ui-camera-active-badge");
    if (!badge) return;
    badge.textContent =
      camera.facing === "user" ? "CÁMARA ACTIVA — SELFIE" : "CÁMARA ACTIVA — TRASERA";
  }

  function syncCameraUiState() {
    var cam =
      document.querySelector(".controls-row .ui-smart-cam-btn") ||
      document.querySelector('.controls-row .control-btn[aria-label="Cámara"]');
    var active = !!camera.open;
    document.documentElement.classList.toggle("salomon-cam-mode", active);
    if (cam) {
      cam.classList.toggle("is-cam-active", active);
      cam.dataset.facing = camera.facing || "environment";
      cam.title = active ? "Cerrar cámara" : "Cámara — toque: abrir";
    }
    var main = document.querySelector(".controls-row .control-btn--main");
    if (main) {
      main.classList.toggle("is-cam-shutter", active);
      if (active) {
        main.title = "Disparar foto";
        main.setAttribute("aria-label", "Disparador");
        main.dataset.captureMode = "1";
      } else {
        main.title = "Núcleo Salomón — dictado / conversación";
        main.setAttribute("aria-label", "Núcleo Salomón — mantener dictado, doble conversación, toque cancela");
        main.dataset.captureMode = "0";
      }
    }
    var writeBtn = getTextBtn();
    if (writeBtn) {
      writeBtn.toggleAttribute("disabled", active);
      writeBtn.setAttribute("aria-disabled", active ? "true" : "false");
    }
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
      if (prevFacing) camera.facing = prevFacing;
      return;
    }
    camera.flipping = true;
    var seq = ++camera.flipSeq;
    var prev = camera.stream;
    var smart = document.getElementById("ui-smart-button");
    if (smart) smart.dataset.flip = "1";
    navigator.mediaDevices
      .getUserMedia({
        video: { facingMode: { exact: camera.facing } },
        audio: false,
      })
      .catch(function () {
        return navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: camera.facing } },
          audio: false,
        });
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
      })
      .catch(function (err) {
        log("flip error", err && err.message);
        // Sincronía: revertir facing si el hardware falló
        if (prevFacing && seq === camera.flipSeq) camera.facing = prevFacing;
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
    // Limpieza no bloqueante (no atrasa el disparo)
    queueMicrotask(function () {
      setTimeout(function () {
        flash.classList.remove("is-on");
      }, 180);
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
    if (!camera.open || camera.capturing || camera.flipping) return;
    var video = camera.videoEl || document.querySelector("#ui-camera-overlay video");
    var overlay = document.getElementById("ui-camera-overlay");
    if (!video || video.readyState < 2) {
      log("capture: video no listo");
      return;
    }
    camera.capturing = true;
    // Flash + frame en el mismo tick (sin debounce)
    flashShutter(overlay);
    haptic([6, 12, 6]);
    try {
      var canvas = document.createElement("canvas");
      canvas.width = video.videoWidth || 720;
      canvas.height = video.videoHeight || 1280;
      canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
      // Encode síncrono → evento inmediato (evita cola de toBlob)
      var dataUrl = canvas.toDataURL("image/jpeg", 0.88);
      var blob = dataUrlToBlob(dataUrl);
      camera.capturing = false;
      if (!blob) return;
      var detail = {
        blob: blob,
        facing: camera.facing,
        mode: camera.mode || "photo",
        width: canvas.width,
        height: canvas.height,
        dataUrl: dataUrl,
      };
      window.dispatchEvent(new CustomEvent("salomon:ui-photo", { detail: detail }));
      log("foto capturada", detail.mode, detail.facing, detail.width + "x" + detail.height);
      if (camera.mode !== "vdcp") {
        closeCamera();
      }
    } catch (e) {
      camera.capturing = false;
      log("capture fail", e && e.message);
    }
  }

  /** Nodo overlay: solo voltear (el disparo es exclusivo del botón central) */
  function wireSmartButton(btn) {
    if (!btn || btn.dataset.neuralBound === "1") return;
    btn.dataset.neuralBound = "1";
    var lastFlip = 0;

    function flip(e) {
      if (e.cancelable) e.preventDefault();
      e.stopImmediatePropagation();
      e.stopPropagation();
      if (e.type !== "touchstart" && e.type !== "pointerdown") return;
      if (e.type === "pointerdown" && e.pointerType === "touch") return;
      var now = Date.now();
      if (now - lastFlip < 400) return;
      lastFlip = now;
      toggleCameraDirection();
    }

    ["touchstart", "pointerdown", "click"].forEach(function (type) {
      btn.addEventListener(type, flip, CAPTURE_OPTS);
    });
  }

  /** Preview: toques ignorados (no disparan ni llegan al chat) */
  function bindStageIgnore(stage) {
    function kill(ev) {
      if (ev.target && ev.target.closest && ev.target.closest(".ui-smart-button, .ui-camera-close")) {
        return;
      }
      if (ev.cancelable) ev.preventDefault();
      ev.stopImmediatePropagation();
      ev.stopPropagation();
    }
    ["touchstart", "touchend", "pointerdown", "pointerup", "click"].forEach(function (type) {
      stage.addEventListener(type, kill, CAPTURE_OPTS);
    });
  }

  function openNeuralCamera(opts) {
    opts = opts || {};
    if (opts.mode) camera.mode = opts.mode;
    // Selfie forzada por defecto (facingMode: user)
    if (!opts.keepFacing && !camera.open) {
      camera.facing = "user";
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
    var facing = camera.facing || "user";
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
        // Descartar streams huérfanos (apertura supersedida / cerrada)
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

        var overlay = document.createElement("div");
        overlay.className = "ui-camera-overlay neural-camera";
        overlay.id = "ui-camera-overlay";
        overlay.dataset.mode = camera.mode || "photo";

        var video = document.createElement("video");
        video.playsInline = true;
        video.muted = true;
        video.autoplay = true;
        video.srcObject = stream;
        video.play().catch(function () {});
        camera.videoEl = video;

        var flash = document.createElement("div");
        flash.className = "ui-camera-flash";
        flash.setAttribute("aria-hidden", "true");

        var stage = document.createElement("div");
        stage.className = "ui-camera-stage";
        stage.appendChild(video);
        bindStageIgnore(stage);

        var smart = document.createElement("button");
        smart.type = "button";
        smart.className = "ui-smart-button";
        smart.id = "ui-smart-button";
        smart.setAttribute("aria-label", "Voltear cámara");
        smart.title = "Toque: voltear · Mantener: disparar";
        smart.innerHTML =
          '<span class="ui-smart-button__ring" aria-hidden="true"></span>' +
          '<span class="ui-smart-button__core" aria-hidden="true"></span>';
        wireSmartButton(smart);

        var badge = document.createElement("div");
        badge.id = "ui-camera-active-badge";
        badge.className = "ui-camera-active-badge";
        badge.setAttribute("aria-live", "polite");
        badge.textContent =
          camera.facing === "user" ? "CÁMARA ACTIVA — SELFIE" : "CÁMARA ACTIVA — TRASERA";

        var closeBtn = document.createElement("button");
        closeBtn.type = "button";
        closeBtn.className = "ui-camera-close";
        closeBtn.setAttribute("aria-label", "Cerrar cámara");
        closeBtn.textContent = "×";
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

        var hint = document.createElement("div");
        hint.className = "ui-camera-hint";
        hint.textContent =
          "Solo botón central = disparar · nodo = voltear · icono cámara = cerrar";

        overlay.appendChild(stage);
        overlay.appendChild(flash);
        overlay.appendChild(badge);
        overlay.appendChild(smart);
        overlay.appendChild(closeBtn);
        overlay.appendChild(hint);
        document.body.appendChild(overlay);
        syncCameraUiState();
        syncWritingUiState();

        // Sin delay artificial: ocultar modal React en microtask
        queueMicrotask(function () {
          document.querySelectorAll(".camera-modal, .camera-backdrop").forEach(function (n) {
            n.style.display = "none";
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
        log("cámara error", err && err.message);
        camera.open = false;
        camera.videoEl = null;
        syncCameraUiState();
      });
  }

  function closeCamera(silent) {
    camera.openSeq += 1; // invalida getUserMedia en vuelo
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
    syncCameraUiState();
    if (!silent) {
      window.dispatchEvent(new CustomEvent("salomon:camera-close"));
    }
  }

  // Compat: nombres anteriores
  function cycleCamera() {
    if (!camera.open) openNeuralCamera({ mode: "photo" });
    else toggleCameraDirection();
  }
  function openCamera() {
    openNeuralCamera({ mode: "photo" });
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
    log("activo stable-zindex-162");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.SalomonUIShield = {
    version: "stable-zindex-162",
    cycleCamera: cycleCamera,
    closeCamera: closeCamera,
    openNeuralCamera: openNeuralCamera,
    toggleCameraDirection: toggleCameraDirection,
    capturePhoto: capturePhoto,
    syncCameraUiState: syncCameraUiState,
    syncWritingUiState: syncWritingUiState,
  };
})();


