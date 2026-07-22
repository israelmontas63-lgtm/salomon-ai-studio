/**
 * Salomón AI — Neutralizador Universal por Capas (Master Back)
 * Stack pop limpio: settings → Aa → cámara → AI lock.
 * No reinicia el núcleo / SalomonBrain.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  var Neutralizer = {
    init() {
      var btn = document.getElementById("btn-nav-back") || document.querySelector(".back-btn");
      if (!btn) return;
      btn.setAttribute("data-role", "universal-neutralizer");
      btn.setAttribute("aria-label", "Neutralizar capa / Volver");
      btn.addEventListener(
        "click",
        (e) => {
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
          this.neutralize();
        },
        true
      );
      this._sync();
      window.addEventListener("salomon:camera-state", () => this._sync());
      window.addEventListener("salomon:ai-lock", () => this._sync());
      window.addEventListener("salomon:deploy-notify", () => this._sync());
      var obs = new MutationObserver(() => this._sync());
      obs.observe(document.body, { attributes: true, attributeFilter: ["class"] });
      window.SalomonBack = this;
      window.SalomonNeutralizer = this;
    },

    hasActiveLayer() {
      if (document.body.classList.contains("control-layer-open")) return true;
      if (window.SalomonUiManager && window.SalomonUiManager.open) return true;
      if (window.SalomonCamera && window.SalomonCamera.isActive && window.SalomonCamera.isActive())
        return true;
      if (window.SalomonAILock && window.SalomonAILock.isActive && window.SalomonAILock.isActive())
        return true;
      if (document.body.classList.contains("vision-immersive")) return true;
      if (document.getElementById("input-layer") &&
          document.getElementById("input-layer").classList.contains("is-open"))
        return true;
      return false;
    },

    _sync() {
      var btn = document.getElementById("btn-nav-back") || document.querySelector(".back-btn");
      if (!btn) return;
      var active = this.hasActiveLayer();
      btn.classList.toggle("is-active", active);
      btn.classList.toggle("is-neutralizer-armed", active);
      btn.setAttribute("aria-disabled", active ? "false" : "true");
      document.body.classList.toggle("has-back-context", active);
      document.body.classList.toggle("neutralizer-armed", active);
    },

    /**
     * Neutraliza la capa activa más alta (stack pop).
     * Preserva el núcleo del asistente.
     */
    neutralize() {
      var closed = false;

      // 1) Control Layer / herramientas
      if (document.body.classList.contains("control-layer-open")) {
        if (window.SalomonSettings && window.SalomonSettings.close) {
          window.SalomonSettings.close();
          closed = true;
        }
      }

      // 2) Input Aa
      if (!closed && window.SalomonUiManager && window.SalomonUiManager.open) {
        if (window.SalomonUiManager.hide) {
          window.SalomonUiManager.hide();
          closed = true;
        }
      }

      // 3) Cámara / inmersivo
      if (
        !closed &&
        ((window.SalomonCamera &&
          window.SalomonCamera.isActive &&
          window.SalomonCamera.isActive()) ||
          document.body.classList.contains("vision-immersive"))
      ) {
        if (window.SalomonCamera && window.SalomonCamera.closeCamera) {
          window.SalomonCamera.closeCamera();
          closed = true;
        }
        document.body.classList.remove("vision-immersive", "camera-ui-elevated");
        var wrap = document.getElementById("cam-wrap");
        if (wrap) wrap.classList.remove("is-active", "is-elevated");
      }

      // 4) Lock de IA (cancelar sin destruir el cerebro)
      if (
        !closed &&
        window.SalomonAILock &&
        window.SalomonAILock.isActive &&
        window.SalomonAILock.isActive()
      ) {
        if (window.SalomonAILock.release) {
          window.SalomonAILock.release("neutralizer_back");
          closed = true;
        }
      }

      // Limpieza residual de UI flotante
      var toast = document.getElementById("update-toast");
      if (toast) toast.classList.remove("is-visible");

      window.dispatchEvent(
        new CustomEvent("salomon:layer-neutralized", {
          detail: { closed: closed, via: "universal_neutralizer" },
        })
      );
      this._sync();
      return closed;
    },

    /** alias estándar */
    goBack() {
      return this.neutralize();
    },
  };

  function boot() {
    Neutralizer.init();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
