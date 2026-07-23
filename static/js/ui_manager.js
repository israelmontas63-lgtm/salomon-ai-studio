/**
 * Salomón AI — UI Manager (Input Layer)
 * Muestra/oculta el campo Aa sin interferir con Smart Button ni cámara.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  const UiManager = {
    open: false,
    layer: null,
    btnAa: null,
    input: null,

    init() {
      this.layer = document.getElementById("input-layer");
      this.btnAa = document.getElementById("btn-aa");
      this.input = document.getElementById("input-msg");
      if (!this.layer || !this.btnAa) return;

      this.btnAa.addEventListener("click", (e) => {
        var brainOk =
          this.btnAa.getAttribute("data-brain-bind") === "1" &&
          typeof window.__salomonTap !== "undefined";
        if (brainOk) return;
        e.preventDefault();
        e.stopPropagation();
        // Zero-Conflict: menú herramientas abierto
        if (document.body.classList.contains("control-layer-open")) return;
        // ui_layer_manager: exclusividad del botón central
        var gateAa =
          window.request_ui_action ||
          (window.SalomonAILock && window.SalomonAILock.request_ui_action);
        if (gateAa && !gateAa("aa_input")) return;
        // No abrir durante cámara inmersiva
        if (document.body.classList.contains("vision-immersive")) return;
        if (window.SalomonCamera && window.SalomonCamera.isActive()) return;
        this.toggle();
      });

      // Cerrar si se abre la cámara
      window.addEventListener("salomon:camera-state", (ev) => {
        const state = (ev.detail && ev.detail.state) || "IDLE";
        if (state === "CAMARA_ACTIVA" || state === "DISPARO") {
          this.hide();
        }
      });

      // Tap fuera del sheet (sobre chat) cierra
      const chat = document.getElementById("chat");
      if (chat) {
        chat.addEventListener("click", () => {
          if (this.open) this.hide();
        });
      }
    },

    toggle() {
      if (this.open) this.hide();
      else this.show();
    },

    show() {
      if (!this.layer) return;
      this.open = true;
      this.layer.classList.add("is-open");
      this.layer.setAttribute("aria-hidden", "false");
      document.body.classList.add("input-sheet-open");
      if (this.btnAa) this.btnAa.classList.add("is-input-open");
      requestAnimationFrame(() => {
        if (this.input) {
          this.input.focus({ preventScroll: false });
        }
      });
      window.dispatchEvent(new CustomEvent("salomon:input-open"));
    },

    hide() {
      if (!this.layer) return;
      this.open = false;
      this.layer.classList.remove("is-open");
      this.layer.setAttribute("aria-hidden", "true");
      document.body.classList.remove("input-sheet-open");
      if (this.btnAa) this.btnAa.classList.remove("is-input-open");
      if (this.input) this.input.blur();
      window.dispatchEvent(new CustomEvent("salomon:input-close"));
    },

    isOpen() {
      return !!this.open;
    },
  };

  function boot() {
    UiManager.init();
    window.SalomonUiManager = UiManager;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
