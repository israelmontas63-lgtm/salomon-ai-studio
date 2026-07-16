/**
 * Menús Salomón — solo DOM tras carga segura (sin MutationObserver).
 * UI Shield redefine iconos H / Perfil; aquí solo títulos glass y labels.
 */
(function () {
  const LABEL_LEFT = "Herramientas";
  const LABEL_RIGHT = "Cuenta y Planes";
  let applied = false;
  let intervalId = null;

  function haptic() {
    try {
      if (!navigator.vibrate) return;
      if (navigator.userActivation && !navigator.userActivation.hasBeenActive) return;
      navigator.vibrate(8);
    } catch (_) {}
  }

  function domReady() {
    return (
      !!document.body &&
      (document.readyState === "interactive" || document.readyState === "complete")
    );
  }

  function ensureLabel(btn, text) {
    if (!btn) return;
    let lab = btn.querySelector(".menu-label");
    if (!lab) {
      lab = document.createElement("span");
      lab.className = "menu-label";
      btn.appendChild(lab);
    }
    if (lab.textContent !== text) lab.textContent = text;
  }

  function styleHeader() {
    if (!domReady()) return false;
    const header = document.querySelector(".studio-header");
    if (!header) return false;
    const btns = header.querySelectorAll(".header-menu-btn");
    if (btns.length < 2) return false;

    // Labels (iconos los pone salomon-ui-shield.js)
    ensureLabel(btns[0], LABEL_LEFT);
    btns[0].setAttribute("aria-label", LABEL_LEFT);
    btns[0].title = LABEL_LEFT;

    ensureLabel(btns[1], LABEL_RIGHT);
    btns[1].setAttribute("aria-label", LABEL_RIGHT);
    btns[1].title = LABEL_RIGHT;

    if (!header.dataset.drawerBound) {
      header.dataset.drawerBound = "1";
      btns.forEach(function (btn) {
        btn.addEventListener(
          "click",
          function () {
            haptic();
          },
          { passive: true }
        );
      });
    }
    return true;
  }

  function emptyPanel(panel) {
    if (!panel || panel.dataset.placeholderReady === "1") return;
    const isLeft = panel.classList.contains("glass-panel--left");
    // React: left panel = cuenta, right = herramientas
    const title = isLeft ? "Cuenta y Planes" : "Herramientas";
    const hint = isLeft
      ? "Perfil, correo y planes de servicio."
      : "Herramientas de Salomón.";
    const h2 = panel.querySelector(".glass-panel__header h2");
    if (h2) h2.textContent = title;
    panel.setAttribute("aria-label", title);
    const nav = panel.querySelector(".glass-panel__list");
    if (nav && !nav.querySelector(".glass-panel__item") && !nav.querySelector(".drawer-placeholder")) {
      nav.innerHTML = "";
      const ph = document.createElement("div");
      ph.className = "drawer-placeholder";
      ph.innerHTML = "<strong>" + title + "</strong>" + hint;
      nav.appendChild(ph);
    }
    panel.dataset.placeholderReady = "1";
  }

  function applyOnce() {
    if (!domReady()) return;
    styleHeader();
    document.querySelectorAll(".glass-panel").forEach(emptyPanel);
  }

  function boot() {
    if (!domReady()) {
      document.addEventListener("DOMContentLoaded", boot, { once: true });
      return;
    }
    if (applied) {
      applyOnce();
      return;
    }
    applied = true;
    document.documentElement.classList.add("salomon-drawers");
    applyOnce();

    var tries = 0;
    if (intervalId) clearInterval(intervalId);
    intervalId = setInterval(function () {
      tries += 1;
      var ok = styleHeader();
      document.querySelectorAll(".glass-panel").forEach(emptyPanel);
      if (ok || tries >= 10) {
        clearInterval(intervalId);
        intervalId = null;
      }
    }, 500);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
  window.addEventListener("salomon:ready", applyOnce);
})();
