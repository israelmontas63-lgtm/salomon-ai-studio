/**
 * Elevación .active-touch → translateY(-25px) en .bottom-dock.
 * Created by Israel Monta - Salomón AI Studio
 */
(function () {
  "use strict";

  var dock = null;
  var pointersDown = 0;

  function setActiveTouch(on) {
    if (!dock) return;
    if (document.body.classList.contains("input-sheet-open")) {
      dock.classList.remove("active-touch");
      return;
    }
    dock.classList.toggle("active-touch", Boolean(on));
  }

  function bind() {
    dock =
      document.querySelector(".bottom-dock") ||
      document.getElementById("nav_bar_container");
    if (!dock) return;
    dock.classList.add("bottom-dock");

    dock.addEventListener(
      "pointerdown",
      function (e) {
        if (!dock.contains(e.target)) return;
        pointersDown += 1;
        setActiveTouch(true);
      },
      { passive: true }
    );

    function onUp() {
      pointersDown = Math.max(0, pointersDown - 1);
      if (pointersDown === 0) setActiveTouch(false);
    }

    window.addEventListener("pointerup", onUp, { passive: true });
    window.addEventListener("pointercancel", onUp, { passive: true });

    window.addEventListener("salomon:input-open", function () {
      setActiveTouch(false);
    });
    window.addEventListener("salomon:input-close", function () {
      setActiveTouch(false);
    });

    setActiveTouch(false);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
