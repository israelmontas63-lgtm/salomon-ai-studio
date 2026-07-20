/**
 * Salomón AI — Botón de retorno estándar (UI header, top-left)
 * Aislado del cerebro: solo cierra capas UI (settings / Aa / cámara).
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  var BackButton = {
    init() {
      var btn = document.getElementById("btn-back");
      if (!btn) return;
      btn.addEventListener(
        "click",
        (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.goBack();
        },
        true
      );
      this._syncVisibility();
      window.addEventListener("salomon:camera-state", () => this._syncVisibility());
      window.addEventListener("salomon:ai-lock", () => this._syncVisibility());
      // Observa capas abiertas
      var obs = new MutationObserver(() => this._syncVisibility());
      obs.observe(document.body, {
        attributes: true,
        attributeFilter: ["class"],
      });
      window.SalomonBack = this;
    },

    canGoBack() {
      if (document.body.classList.contains("control-layer-open")) return true;
      if (window.SalomonUiManager && window.SalomonUiManager.open) return true;
      if (window.SalomonCamera && window.SalomonCamera.isActive && window.SalomonCamera.isActive())
        return true;
      return false;
    },

    _syncVisibility() {
      var btn = document.getElementById("btn-back");
      if (!btn) return;
      var active = this.canGoBack();
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-disabled", active ? "false" : "true");
      document.body.classList.toggle("has-back-context", active);
    },

    goBack() {
      // Prioridad: settings → input → cámara (estándar de pila UI)
      if (document.body.classList.contains("control-layer-open")) {
        if (window.SalomonSettings && window.SalomonSettings.close) {
          window.SalomonSettings.close();
        }
        this._syncVisibility();
        return;
      }
      if (window.SalomonUiManager && window.SalomonUiManager.open) {
        if (window.SalomonUiManager.hide) window.SalomonUiManager.hide();
        this._syncVisibility();
        return;
      }
      if (window.SalomonCamera && window.SalomonCamera.isActive && window.SalomonCamera.isActive()) {
        if (window.SalomonCamera.closeCamera) window.SalomonCamera.closeCamera();
        this._syncVisibility();
        return;
      }
      this._syncVisibility();
    },
  };

  function boot() {
    BackButton.init();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
