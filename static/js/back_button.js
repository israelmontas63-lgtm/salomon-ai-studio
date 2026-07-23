/**
 * Salomón AI — Global Negative System (Master Back)
 * 1) Capa activa → neutralize
 * 2) Home → intentar cerrar PWA SIN destruir la sesión (no about:blank)
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
      if (btn.getAttribute("data-brain-bind") !== "1") {
        btn.addEventListener(
          "click",
          (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.onBackTap();
          },
          false
        );
      }
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

    onBackTap() {
      if (this.hasActiveLayer()) {
        this.neutralize();
        return;
      }
      this.exitSystem();
    },

    /**
     * Intenta cerrar la PWA. NUNCA navega a about:blank (deja la app muerta).
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

      /* Si el SO bloquea close(): avisar, no destruir el DOM */
      try {
        if (window.SalomonToast && typeof window.SalomonToast.show === "function") {
          window.SalomonToast.show("Usa el gesto del sistema para salir de la app.");
          return;
        }
      } catch (_) {}

      var toast = document.getElementById("update-toast");
      if (toast) {
        var text = toast.querySelector(".update-toast__text");
        if (text) {
          text.textContent = "Para salir: cierra la app desde el sistema.";
        }
        toast.classList.add("is-visible");
        setTimeout(function () {
          toast.classList.remove("is-visible");
        }, 2800);
      }
    },

    _sync() {
      var btn =
        document.getElementById("btn-nav-back") ||
        document.querySelector(".back-btn");
      if (!btn) return;
      btn.classList.add("is-active", "is-neutralizer-armed");
      btn.setAttribute("aria-disabled", "false");
      btn.setAttribute("aria-label", "Salir del sistema / Cerrar capa");
      document.body.classList.add("has-back-context", "neutralizer-armed");
    },

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
