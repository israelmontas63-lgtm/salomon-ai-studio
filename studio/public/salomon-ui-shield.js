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

  var camera = { stream: null, facing: "environment", open: false, step: 0 };
  var audio = { ctx: null, analyser: null, src: null, raf: 0, stream: null };
  var swapLock = false;
  var lastTap = 0;

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

    // Cámara
    if (cam.dataset.uiCam !== "1") {
      cam.dataset.uiCam = "1";
      cam.setAttribute("aria-label", "Cámara");
      cam.addEventListener(
        "click",
        function (e) {
          e.preventDefault();
          e.stopImmediatePropagation();
          cycleCamera();
        },
        true
      );
    }

    // Texto
    if (textBtn.dataset.uiText !== "1") {
      textBtn.dataset.uiText = "1";
      textBtn.setAttribute("aria-label", "Texto");
      textBtn.title = "Escribe tu mensaje";
    }

    // Voz central: órbita + nube + audio
    if (main && main.dataset.uiVoice !== "1") {
      main.dataset.uiVoice = "1";
      ensureVoiceFx(main);
      wireVoiceGestures(main);
    } else if (main) {
      ensureVoiceFx(main);
    }

    polishInput();
    return true;
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

  function wireVoiceGestures(btn) {
    btn.addEventListener(
      "click",
      function () {
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
            if (Date.now() - lastTap >= 300) {
              btn.dataset.uiMode = "dictation";
              startAudioReactive(btn);
            }
          }, 300);
        }
      },
      false
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

  /* ——— Cámara: 1 trasera, 2 frontal, 3 cierra; tap preview = foto ——— */
  function cycleCamera() {
    haptic(12);
    if (!camera.open) {
      camera.facing = "environment";
      camera.step = 1;
      openCamera();
      return;
    }
    if (camera.step === 1) {
      camera.facing = "user";
      camera.step = 2;
      openCamera();
      return;
    }
    closeCamera();
    camera.step = 0;
  }

  function openCamera() {
    closeCamera(true);
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      log("cámara no disponible");
      return;
    }
    navigator.mediaDevices
      .getUserMedia({
        video: { facingMode: { ideal: camera.facing } },
        audio: false,
      })
      .then(function (stream) {
        camera.stream = stream;
        camera.open = true;
        var overlay = document.createElement("div");
        overlay.className = "ui-camera-overlay";
        overlay.id = "ui-camera-overlay";
        var video = document.createElement("video");
        video.playsInline = true;
        video.muted = true;
        video.autoplay = true;
        video.srcObject = stream;
        video.play().catch(function () {});
        var hint = document.createElement("div");
        hint.className = "ui-camera-hint";
        hint.textContent = "Toca la vista para capturar · botón cámara para cambiar/cerrar";
        overlay.appendChild(video);
        overlay.appendChild(hint);
        overlay.addEventListener("click", function (ev) {
          if (ev.target === hint) return;
          captureFromVideo(video);
        });
        document.body.appendChild(overlay);
        // Cerrar modal React de cámara si aparece
        setTimeout(function () {
          document.querySelectorAll(".camera-modal, .camera-backdrop").forEach(function (n) {
            n.style.display = "none";
          });
        }, 50);
      })
      .catch(function (err) {
        log("cámara error", err && err.message);
        camera.open = false;
      });
  }

  function closeCamera(silent) {
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
    if (!silent) camera.step = 0;
  }

  function captureFromVideo(video) {
    try {
      var canvas = document.createElement("canvas");
      canvas.width = video.videoWidth || 720;
      canvas.height = video.videoHeight || 1280;
      var ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(function (blob) {
        if (!blob) return;
        haptic([8, 20, 8]);
        // Disparar evento para que capas existentes puedan reaccionar
        window.dispatchEvent(
          new CustomEvent("salomon:ui-photo", { detail: { blob: blob, facing: camera.facing } })
        );
        // Intentar pegar en input file oculto o notificar
        try {
          var url = URL.createObjectURL(blob);
          var img = new Image();
          img.src = url;
          log("foto capturada", camera.facing, canvas.width + "x" + canvas.height);
        } catch (e) {}
        closeCamera();
      }, "image/jpeg", 0.92);
    } catch (e) {
      log("capture fail", e && e.message);
    }
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
  }

  function boot() {
    document.documentElement.classList.add("salomon-ui-shield");
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
    log("activo v1");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.SalomonUIShield = { version: "ui-shield-1", cycleCamera: cycleCamera, closeCamera: closeCamera };
})();
