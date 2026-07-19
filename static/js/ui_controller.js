/**
 * Salomón AI — UI Controller
 * Cambia iconos del botón central según estado de cámara.
 * IDLE → logo "S" | CÁMARA_ACTIVA → gatillo (cámara)
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  const ICON_SHUTTER = "/static/assets/icon-shutter.svg";

  const UiController = {
    root: null,
    icon: null,
    glyph: null,
    label: null,

    init() {
      this.root = document.getElementById("smart-button");
      if (!this.root) return;
      this.icon = this.root.querySelector(".smart-button__icon");
      this.glyph = this.root.querySelector(".smart-button__glyph");
      this.label = this.root.querySelector(".smart-button__label");
      this.showLogoS();
      window.addEventListener("salomon:camera-state", (ev) => {
        const state = (ev.detail && ev.detail.state) || "IDLE";
        const wrap = document.getElementById("cam-wrap");
        if (wrap && ev.detail && ev.detail.facingMode) {
          wrap.dataset.facing = ev.detail.facingMode;
        }
        // Selfie mantiene gatillo; OFF/IDLE vuelve a logo S
        if (state === "CAMARA_ACTIVA" || state === "DISPARO") {
          this.showShutter();
        } else {
          this.showLogoS();
        }
      });
    },

    showLogoS() {
      if (!this.root) return;
      this.root.classList.remove("is-shutter", "is-listening", "is-camera");
      if (this.glyph) this.glyph.hidden = false;
      if (this.icon) this.icon.hidden = true;
      if (this.label) this.label.textContent = "Salomón AI";
      this.root.setAttribute("aria-label", "Salomón AI");
      this.root.dataset.role = "ai";
    },

    showShutter() {
      if (!this.root) return;
      this.root.classList.add("is-shutter");
      this.root.classList.remove("is-listening");
      if (this.glyph) this.glyph.hidden = true;
      if (this.icon) {
        this.icon.hidden = false;
        this.icon.src = ICON_SHUTTER;
        this.icon.alt = "Disparar";
      }
      if (this.label) this.label.textContent = "Disparar foto";
      this.root.setAttribute("aria-label", "Disparar foto");
      this.root.dataset.role = "shutter";
    },

    /** true si el micrófono del centro debe estar bloqueado */
    isMicBlocked() {
      return !!(window.SalomonCamera && window.SalomonCamera.isActive());
    },
  };

  function boot() {
    UiController.init();
    window.SalomonUI = UiController;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
