/**
 * Menús Salomón — solo DOM tras carga segura (sin MutationObserver).
 */
(function () {
  const LABEL_LEFT = "Correo";
  const LABEL_RIGHT = "Herramientas";
  let applied = false;
  let intervalId = null;

  function haptic() {
    try {
      if (navigator.vibrate) navigator.vibrate(8);
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

  function setIcon(btn, kind) {
    if (!btn || btn.dataset.iconKind === kind) return;
    btn.dataset.iconKind = kind;
    const html =
      kind === "dots"
        ? '<span class="dots-icon" aria-hidden="true"><i></i><i></i><i></i></span>'
        : '<span class="lines-icon" aria-hidden="true"><i></i><i></i></span>';
    const oldIcon = btn.querySelector(".dots-icon, .lines-icon");
    if (oldIcon) oldIcon.outerHTML = html;
    else btn.insertAdjacentHTML("afterbegin", html);
  }

  function styleHeader() {
    if (!domReady()) return false;
    const header = document.querySelector(".studio-header");
    if (!header) return false;
    const btns = header.querySelectorAll(".header-menu-btn");
    if (btns.length < 2) return false;

    setIcon(btns[0], "lines");
    ensureLabel(btns[0], LABEL_LEFT);
    btns[0].setAttribute("aria-label", LABEL_LEFT);
    btns[0].title = LABEL_LEFT;

    setIcon(btns[1], "dots");
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
    const title = isLeft ? LABEL_LEFT : LABEL_RIGHT;
    const hint = isLeft
      ? "Registro, correo y planes de servicio. Pronto aquí."
      : "Herramientas de Salomón. Pronto aquí.";
    const h2 = panel.querySelector(".glass-panel__header h2");
    if (h2) h2.textContent = title;
    panel.setAttribute("aria-label", title);
    const nav = panel.querySelector(".glass-panel__list");
    if (nav) {
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
