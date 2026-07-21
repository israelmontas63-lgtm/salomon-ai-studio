/**
 * Salomón AI — Motor Definitivo del Botón Inteligente (Seamless)
 * Tap rápido (<300ms típico / suelta antes de 500ms) → Dictado
 * Long press (≥500ms) → Conversacional IA
 * Tap con modo activo → Neutralizador Maestro (baseline)
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  var TAP_MAX_MS = 300;
  var HOLD_MS = 500;
  var States = Object.freeze({
    IDLE: "IDLE",
    PRESSING: "PRESSING",
    DICTATION: "DICTATION",
    CONVERSATIONAL: "CONVERSATIONAL",
    PROCESSING: "PROCESSING",
  });

  function lock() {
    return window.SalomonAILock || null;
  }

  function haptic(pattern) {
    try {
      if (navigator.vibrate) navigator.vibrate(pattern || 12);
    } catch (_) {}
  }

  class SmartButton {
    constructor(root) {
      this.root = root;
      this.state = States.IDLE;
      this.recognition = null;
      this._holdTimer = null;
      this._pressStart = 0;
      this._holdFired = false;
      this._pointerId = null;
      this._ignoreClickUntil = 0;

      this.root.addEventListener("pointerdown", (e) => this._onPointerDown(e));
      this.root.addEventListener("pointerup", (e) => this._onPointerUp(e));
      this.root.addEventListener("pointercancel", (e) => this._onPointerCancel(e));
      this.root.addEventListener("pointerleave", (e) => {
        if (this.state === States.PRESSING && e.pointerType === "mouse") {
          this._onPointerCancel(e);
        }
      });
      this.root.addEventListener("click", (e) => this._onClickFallback(e));
      this.root.addEventListener("contextmenu", (e) => e.preventDefault());

      window.addEventListener("salomon:ai-lock", (ev) => {
        var d = (ev && ev.detail) || {};
        if (d.action === "release") {
          this.root.classList.remove(
            "is-ai-locked",
            "is-holographic",
            "is-conversational",
            "is-dictation"
          );
          if (
            this.state === States.CONVERSATIONAL ||
            this.state === States.DICTATION ||
            this.state === States.PROCESSING
          ) {
            this._setState(States.IDLE);
          }
        }
        if (d.action === "activate") {
          this.root.classList.add("is-ai-locked");
        }
      });

      this.root.classList.add("is-seamless");
      this.root.setAttribute("data-gesture-engine", "seamless-smart-button");
      this.root.setAttribute("data-hold-ms", String(HOLD_MS));
      this.root.setAttribute("data-tap-max-ms", String(TAP_MAX_MS));
      this.root.setAttribute(
        "aria-label",
        "Salomón: toque = dictado · mantén = conversar · toque otra vez = salir"
      );

      window.SalomonGestureEngine = {
        HOLD_MS: HOLD_MS,
        TAP_MAX_MS: TAP_MAX_MS,
        states: States,
        getState: () => this.state,
        engine: "seamless",
      };
      window.SalomonSeamlessButton = this;
      this._setState(States.IDLE);
    }

    _setState(next) {
      this.state = next;
      this.root.setAttribute("data-gesture-state", next);
      this.root.classList.toggle("is-pressing", next === States.PRESSING);
      this.root.classList.toggle("is-dictation", next === States.DICTATION);
      this.root.classList.toggle("is-conversational", next === States.CONVERSATIONAL);
      this.root.classList.toggle(
        "is-holographic",
        next === States.CONVERSATIONAL || next === States.PRESSING
      );
      this.root.classList.toggle("is-processing", next === States.PROCESSING);
      window.dispatchEvent(
        new CustomEvent("salomon:gesture-state", {
          detail: { state: next, holdMs: HOLD_MS, tapMaxMs: TAP_MAX_MS },
        })
      );
    }

    _blockedByUi() {
      if (document.body.classList.contains("control-layer-open")) return true;
      if (window.SalomonSettings && window.SalomonSettings.isOpen()) return true;
      if (window.SalomonUI && window.SalomonUI.isMicBlocked()) return true;
      if (window.SalomonCamera && window.SalomonCamera.isActive()) return true;
      return false;
    }

    _onPointerDown(e) {
      if (this._blockedByUi()) return;
      if (e.button != null && e.button !== 0) return;

      if (
        this.state === States.DICTATION ||
        this.state === States.CONVERSATIONAL ||
        this.state === States.PROCESSING ||
        (lock() &&
          lock().isActive() &&
          this.state !== States.IDLE &&
          this.state !== States.PRESSING)
      ) {
        e.preventDefault();
        e.stopPropagation();
        this.neutralize("tap_while_active");
        this._ignoreClickUntil = Date.now() + 400;
        return;
      }

      if (this.state !== States.IDLE) return;

      e.preventDefault();
      try {
        this.root.setPointerCapture(e.pointerId);
      } catch (_) {}
      this._pointerId = e.pointerId;
      this._pressStart = Date.now();
      this._holdFired = false;
      this._setState(States.PRESSING);
      this.root.classList.add("is-active");
      haptic(8);

      clearTimeout(this._holdTimer);
      this._holdTimer = setTimeout(() => {
        this._holdTimer = null;
        if (this.state !== States.PRESSING) return;
        this._holdFired = true;
        haptic([16, 30, 16]);
        this._enterConversational();
      }, HOLD_MS);
    }

    _onPointerUp(e) {
      if (this._pointerId != null && e.pointerId !== this._pointerId) return;
      this._pointerId = null;
      try {
        this.root.releasePointerCapture(e.pointerId);
      } catch (_) {}

      clearTimeout(this._holdTimer);
      this._holdTimer = null;

      if (this.state === States.PRESSING && !this._holdFired) {
        e.preventDefault();
        this._ignoreClickUntil = Date.now() + 400;
        this._enterDictation();
        return;
      }

      if (this.state === States.CONVERSATIONAL) {
        this._ignoreClickUntil = Date.now() + 400;
      }
    }

    _onPointerCancel(e) {
      if (this._pointerId != null && e.pointerId !== this._pointerId) return;
      clearTimeout(this._holdTimer);
      this._holdTimer = null;
      this._pointerId = null;
      if (this.state === States.PRESSING && !this._holdFired) {
        this.root.classList.remove("is-active", "is-pressing", "is-holographic");
        this._setState(States.IDLE);
      }
    }

    _onClickFallback(e) {
      if (Date.now() < this._ignoreClickUntil) {
        e.preventDefault();
        e.stopPropagation();
        return;
      }
      if (this._blockedByUi()) return;
      if (e.detail === 0) {
        e.preventDefault();
        if (
          this.state === States.DICTATION ||
          this.state === States.CONVERSATIONAL ||
          (lock() && lock().isActive())
        ) {
          this.neutralize("keyboard_tap");
        } else if (this.state === States.IDLE) {
          this._enterDictation();
        }
      }
    }

    neutralize(reason) {
      haptic(10);
      this._stopMic(false);
      var L = lock();
      if (L && L.isActive()) L.release(reason || "gesture_neutralize");
      this.root.classList.remove(
        "is-active",
        "is-listening",
        "is-ai-locked",
        "is-holographic",
        "is-dictation",
        "is-conversational",
        "is-pressing",
        "is-processing"
      );
      this._setState(States.IDLE);
      window.dispatchEvent(
        new CustomEvent("salomon:gesture-neutralized", {
          detail: { reason: reason || "tap" },
        })
      );
    }

    _enterDictation() {
      var L = lock();
      // Mantener ojos activos: antes closeCamera mataba el frame de visión
      if (L) L.activate("gesture_dictation", { keepCamera: true });
      this._setState(States.DICTATION);
      this.root.classList.add("is-ai-locked", "is-active", "is-listening");
      this.root.classList.remove("is-holographic", "is-conversational");
      this._notify("Te escucho — dicta tu nota o búsqueda. Un toque para salir.");
      this._startMic({ continuous: false, mode: "dictation" });
    }

    _enterConversational() {
      var L = lock();
      if (L) L.activate("gesture_conversational", { keepCamera: true });
      this._setState(States.CONVERSATIONAL);
      this.root.classList.add(
        "is-ai-locked",
        "is-active",
        "is-listening",
        "is-holographic",
        "is-conversational"
      );
      this._notify(
        "Conversación con Salomón abierta. Habla con calma — un toque para cerrar."
      );
      this._startMic({ continuous: true, mode: "conversational" });
    }

    _startMic(opts) {
      opts = opts || {};
      var continuous = !!opts.continuous;
      var mode = opts.mode || "dictation";

      if (this.recognition) {
        try {
          this.recognition.onend = null;
          this.recognition.stop();
        } catch (_) {}
        this.recognition = null;
      }

      var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SR) {
        this._sendFromInputOrNotify();
        return;
      }

      try {
        this.recognition = new SR();
        this.recognition.lang = "es-DO";
        this.recognition.interimResults = continuous;
        this.recognition.continuous = continuous;
        this.root.classList.add("is-listening", "is-active");

        this.recognition.onresult = (ev) => {
          var text = "";
          for (var i = ev.resultIndex; i < ev.results.length; i++) {
            if (ev.results[i].isFinal) {
              text += (ev.results[i][0] && ev.results[i][0].transcript) || "";
            }
          }
          text = (text || "").trim();
          if (!text) return;

          if (mode === "dictation") {
            this._stopMic(true);
            this._callBrain(text, { mode: "dictation" });
          } else {
            this._callBrain(text, { mode: "conversational", keepMic: true });
          }
        };

        this.recognition.onerror = () => {
          if (mode === "dictation") {
            this._stopMic(true);
            var L = lock();
            if (L) L.release("mic_error");
            this._setState(States.IDLE);
            this.root.classList.remove("is-active", "is-ai-locked", "is-listening");
          }
          if (mode === "conversational" && this.state === States.CONVERSATIONAL) {
            setTimeout(() => {
              if (this.state === States.CONVERSATIONAL) {
                this._startMic({ continuous: true, mode: "conversational" });
              }
            }, 350);
          }
        };

        this.recognition.onend = () => {
          if (mode === "conversational" && this.state === States.CONVERSATIONAL) {
            try {
              if (this.recognition) this.recognition.start();
            } catch (_) {
              this.recognition = null;
              this._startMic({ continuous: true, mode: "conversational" });
            }
            return;
          }
          if (this.recognition) this._stopMic(true);
        };

        this.recognition.start();
      } catch (_) {
        this._notify("No pude abrir el micrófono. Prueba con Aa o otro navegador.");
        this._stopMic(true);
        var L2 = lock();
        if (L2) L2.release("mic_exception");
        this._setState(States.IDLE);
      }
    }

    _stopMic(keepLock) {
      if (this.recognition) {
        try {
          this.recognition.onend = null;
          this.recognition.onresult = null;
          this.recognition.onerror = null;
          this.recognition.stop();
        } catch (_) {}
        this.recognition = null;
      }
      this.root.classList.remove("is-listening");
      if (!keepLock) {
        this.root.classList.remove(
          "is-active",
          "is-ai-locked",
          "is-holographic",
          "is-dictation",
          "is-conversational",
          "is-pressing"
        );
        if (this.state !== States.PROCESSING) this._setState(States.IDLE);
      }
    }

    async _callBrain(text, opts) {
      opts = opts || {};
      var keepMic = !!opts.keepMic;
      var L = lock();
      var chat = document.getElementById("chat");
      if (chat) {
        var userEl = document.createElement("div");
        userEl.className = "bubble user";
        userEl.textContent = text;
        chat.appendChild(userEl);
        var typing = document.createElement("div");
        typing.className = "bubble bot typing";
        typing.innerHTML =
          '<span class="typing-label">Salomón está pensando</span>' +
          '<span class="typing-dots" aria-hidden="true"><i></i><i></i><i></i></span>';
        chat.appendChild(typing);
        chat.scrollTop = chat.scrollHeight;
      }

      var prevState = this.state;
      if (!keepMic) this._setState(States.PROCESSING);

      var VT = window.SalomonVisionModeTrigger;
      if (VT && VT.matches && VT.matches(text)) {
        document.body.classList.add("salomon-processing");
        var engaged = await VT.engage({ source: "smart_button_voice" });
        document.body.classList.remove("salomon-processing");
        if (chat) {
          var typingVis = chat.querySelector(".bubble.typing");
          if (typingVis) typingVis.remove();
          var botVis = document.createElement("div");
          botVis.className = "bubble bot";
          botVis.textContent =
            (engaged && engaged.texto) ||
            "Modo visión activo. Mis ojos están encendidos.";
          chat.appendChild(botVis);
          chat.scrollTop = chat.scrollHeight;
        }
        if (!keepMic) this.neutralize("vision_mode_trigger");
        return;
      }

      document.body.classList.add("salomon-processing");

      var result =
        (window.trigger_ai_core || (L && L.trigger_ai_core) || (L && L.callBrainDirect))
          ? await (window.trigger_ai_core || L.trigger_ai_core || L.callBrainDirect).call(
              null,
              {
                mensaje: text,
                reason:
                  opts.mode === "conversational"
                    ? "seamless_hold_ai"
                    : "seamless_tap_dictation",
                keep_lock: keepMic,
              }
            )
          : await this._fallbackFetch(text);

      document.body.classList.remove("salomon-processing");

      var data = (result && result.data) || {};
      var meta = data.metadata || {};
      if (meta.activar_modo_vision && VT && VT.engage) {
        await VT.engage({ source: "brain_meta" });
      }

      if (chat) {
        var typingEl = chat.querySelector(".bubble.typing");
        if (typingEl) typingEl.remove();
        // vision_local: vision_engine ya escribió la burbuja (sin eco duplicado)
        if (!(meta && meta.vision_local)) {
          var bot = document.createElement("div");
          bot.className = "bubble bot";
          bot.textContent =
            (result && result.ok && data.texto) ||
            data.detail ||
            "No pude completar la respuesta. ¿Lo intentamos de nuevo?";
          chat.appendChild(bot);
          chat.scrollTop = chat.scrollHeight;
        }
      }

      if (result && result.ok && data.session_id) {
        localStorage.setItem("salomon_session_id", data.session_id);
      }
      if (result && result.ok) {
        window.dispatchEvent(
          new CustomEvent("salomon:chat-turn", {
            detail: {
              session_id:
                data.session_id || localStorage.getItem("salomon_session_id"),
              preview: text,
              mensaje: text,
            },
          })
        );
      }

      if (result && result.data && result.data.audio_base64) {
        try {
          if (
            window.SalomonVoiceLayer &&
            window.SalomonVoiceLayer.playFromResponse
          ) {
            window.SalomonVoiceLayer.playFromResponse(result.data);
          } else {
            var mime = result.data.audio_mime || "audio/mpeg";
            var audio = new Audio(
              "data:" + mime + ";base64," + result.data.audio_base64
            );
            audio.play().catch(function () {});
          }
        } catch (_) {}
      }

      if (keepMic && prevState === States.CONVERSATIONAL) {
        this._setState(States.CONVERSATIONAL);
        this.root.classList.add(
          "is-ai-locked",
          "is-active",
          "is-listening",
          "is-holographic",
          "is-conversational"
        );
        return;
      }

      this.root.classList.remove(
        "is-active",
        "is-listening",
        "is-ai-locked",
        "is-holographic",
        "is-dictation",
        "is-conversational",
        "is-processing"
      );
      this._setState(States.IDLE);
      if (L && L.isActive() && !keepMic) L.release("dictation_done");
    }

    async _fallbackFetch(text) {
      try {
        var res = await fetch("/api/ai/central-button", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mensaje: text }),
          credentials: "same-origin",
        });
        var pack = await res.json().catch(function () {
          return {};
        });
        var data = pack.brain || pack;
        return { ok: res.ok && !!(data && data.texto), data: data, pack: pack };
      } catch (_) {
        return { ok: false, data: {} };
      } finally {
        var L = lock();
        if (L) L.release("fallback_done");
      }
    }

    _sendFromInputOrNotify() {
      var input = document.getElementById("input-msg");
      var text = (input && input.value ? input.value : "").trim();
      if (text) {
        if (input) input.value = "";
        this._callBrain(text, { mode: "dictation" });
        return;
      }
      this._notify("Micrófono no disponible. Escribe con Aa cuando quieras.");
      this.neutralize("no_speech_api");
    }

    _notify(msg) {
      var chat = document.getElementById("chat");
      if (!chat) return;
      var el = document.createElement("div");
      el.className = "bubble bot";
      el.textContent = msg;
      chat.appendChild(el);
      chat.scrollTop = chat.scrollHeight;
    }

    onClick(e) {
      this._onClickFallback(e);
    }
    toggleMic() {
      if (this.recognition) this.neutralize("toggle_mic");
      else this._enterDictation();
    }
  }

  function boot() {
    var root = document.getElementById("smart-button");
    if (!root) return;
    window.SalomonSmartButton = new SmartButton(root);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
