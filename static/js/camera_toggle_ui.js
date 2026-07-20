/**
 * Salomón AI — Camera Toggle UI (capa aislada)
 * SOLO animación de elevación / retorno. No llama al cerebro ni a vision_engine.
 * Escucha salomon:camera-state emitido por camera_logic.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  var ELEVATE_CLASS = "camera-ui-elevated";
  var WRAP_CLASS = "is-elevated";

  var CameraToggleUI = {
    init() {
      window.addEventListener("salomon:camera-state", (ev) => {
        var state = (ev.detail && ev.detail.state) || "IDLE";
        if (state === "CAMARA_ACTIVA" || state === "DISPARO") {
          this.elevate();
        } else {
          this.returnHome();
        }
      });
      window.SalomonCameraToggleUI = this;
    },

    elevate() {
      document.body.classList.add(ELEVATE_CLASS);
      var wrap = document.getElementById("cam-wrap");
      if (wrap) wrap.classList.add(WRAP_CLASS);
    },

    returnHome() {
      document.body.classList.remove(ELEVATE_CLASS);
      var wrap = document.getElementById("cam-wrap");
      if (wrap) wrap.classList.remove(WRAP_CLASS);
    },
  };

  function boot() {
    CameraToggleUI.init();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
