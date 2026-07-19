/**
 * Salomón AI — Pantalla de Visión Inmersiva
 * Toggle: oculta chat/UI; deja video full-screen + trío (gatillo, giro, cerrar).
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  const CameraFull = {
    active: false,

    init() {
      window.addEventListener("salomon:camera-state", (ev) => {
        const state = (ev.detail && ev.detail.state) || "IDLE";
        if (state === "CAMARA_ACTIVA" || state === "DISPARO") {
          this.enter();
        } else if (state === "OFF" || state === "IDLE") {
          this.exit();
        }
      });
    },

    enter() {
      if (this.active) return;
      this.active = true;
      requestAnimationFrame(() => {
        document.body.classList.add("vision-immersive");
        document.body.setAttribute("data-vision", "immersive");
        const stage = document.getElementById("camera-stage");
        if (stage) {
          stage.classList.add("is-visible", "is-immersive");
          stage.setAttribute("aria-hidden", "false");
        }
        const flip = document.getElementById("btn-flip");
        if (flip) flip.tabIndex = 0;
        // Ocultar restos no cubiertos por CSS
        this._setHidden(
          ["header", "chat", "form-chat", "btn-aa"],
          true
        );
      });
    },

    exit() {
      if (!this.active && !document.body.classList.contains("vision-immersive")) {
        return;
      }
      this.active = false;
      requestAnimationFrame(() => {
        document.body.classList.remove("vision-immersive");
        document.body.removeAttribute("data-vision");
        const stage = document.getElementById("camera-stage");
        if (stage) {
          stage.classList.remove("is-immersive");
          stage.setAttribute("aria-hidden", "true");
        }
        const flip = document.getElementById("btn-flip");
        if (flip) flip.tabIndex = -1;
        this._setHidden(
          ["header", "chat", "form-chat", "btn-aa"],
          false
        );
      });
    },

    _setHidden(ids, hidden) {
      ids.forEach((id) => {
        const el =
          document.getElementById(id) ||
          document.querySelector("." + id);
        if (!el) return;
        if (hidden) {
          el.setAttribute("data-immersive-prev", el.style.display || "");
          el.style.display = "none";
        } else {
          const prev = el.getAttribute("data-immersive-prev");
          el.style.display = prev || "";
          el.removeAttribute("data-immersive-prev");
        }
      });
    },
  };

  function boot() {
    CameraFull.init();
    window.SalomonCameraFull = CameraFull;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
