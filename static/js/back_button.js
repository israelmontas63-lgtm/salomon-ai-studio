/**
 * Salomón AI — Global Negative System (Master Back)
 * 1) Si hay capa → neutralize (settings / Aa / cámara / AI lock)
 * 2) Si home → exitSystem (cerrar aplicación / salir del sistema)
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  var Neutralizer = {
    init() {
      var btn =
        document.getElementById("btn-nav-back") ||
        document.querySelector(".back-btn");
      if (!btn) return;
      btn.setAttribute("data-role", "global-negative");
      btn.setAttribute("aria-label", "Salir del sistema / Cerrar capa");
      btn.addEventListener(
        "click",
        (e) => {
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
          this.onBackTap();
        },
        true
      );
      this._sync();
      window.addEventListener("salomon:camera-state", () => this._sync());
      window.addEventListener("salomon:ai-lock", () => this._sync());
      window.addEventListener("salomon:deploy-notify", () => this._sync());
      var obs = new MutationObserver(() => this._sync());
      obs.observe(document.body, {
        attributes: true,
        attributeFilter: ["class"],
      });
      window.SalomonBack = this;
      window.SalomonNeutralizer = this;
    },

    hasActiveLayer() {
      if (document.body.classList.contains("control-layer-open")) return true;
      if (window.SalomonUiManager && window.SalomonUiManager.open) return true;
      if (
        window.SalomonCamera &&
        window.SalomonCamera.isActive &&
        window.SalomonCamera.isActive()
      )
        return true;
      if (
        window.SalomonAILock &&
        window.SalomonAILock.isActive &&
        window.SalomonAILock.isActive()
      )
        return true;
      if (document.body.classList.contains("vision-immersive")) return true;
      var input = document.getElementById("input-layer");
      if (input && input.classList.contains("is-open")) return true;
      return false;
    },

    /** Operador negativo global */
    onBackTap() {
      if (this.hasActiveLayer()) {
        this.neutralize();
        return;
      }
      this.exitSystem();
    },

    /**
     * Home / sin capas: cerrar la aplicación (PWA / fallback).
     */
    exitSystem() {
      window.dispatchEvent(
        new CustomEvent("salomon:system-exit", {
          detail: { via: "global_negative_back" },
        })
      );

      var standalone =
        (window.matchMedia &&
          window.matchMedia("(display-mode: standalone)").matches) ||
        window.navigator.standalone === true;

      try {
        if (standalone) {
          window.close();
        }
      } catch (_) {}

      try {
        if (window.history && window.history.length > 1) {
          window.history.go(-(window.history.length - 1));
        }
      } catch (_) {}

      try {
        window.location.replace("about:blank");
      } catch (_) {}
    },

    _sync() {
      var btn =
        document.getElementById("btn-nav-back") ||
        document.querySelector(".back-btn");
      if (!btn) return;
      /* Siempre armado (Global Negative) — también en home */
      btn.classList.add("is-active", "is-neutralizer-armed");
      btn.setAttribute("aria-disabled", "false");
      btn.setAttribute("aria-label", "Salir del sistema / Cerrar capa");
      document.body.classList.add("has-back-context", "neutralizer-armed");
    },

    /**
     * Neutraliza la capa activa más alta (stack pop).
     * Preserva el núcleo del asistente.
     */
    neutralize() {
      var closed = false;

      if (document.body.classList.contains("control-layer-open")) {
        if (window.SalomonSettings && window.SalomonSettings.close) {
          window.SalomonSettings.close();
          closed = true;
        }
      }

      if (!closed && window.SalomonUiManager && window.SalomonUiManager.open) {
        if (window.SalomonUiManager.hide) {
          window.SalomonUiManager.hide();
          closed = true;
        }
      }

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

      var toast = document.getElementById("update-toast");
      if (toast) toast.classList.remove("is-visible");

      window.dispatchEvent(
        new CustomEvent("salomon:layer-neutralized", {
          detail: { closed: closed, via: "global_negative" },
        })
      );
      this._sync();
      return closed;
    },

    goBack() {
      return this.onBackTap();
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
