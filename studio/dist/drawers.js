/**
 * Arquitectura final de menús — Salomón AI
 * Izq (=) Correo · Der (...) Herramientas · paneles vacíos + glassmorphism
 */
(function () {
  const LABEL_LEFT = "Correo";
  const LABEL_RIGHT = "Herramientas";

  function haptic() {
    try {
      if (navigator.vibrate) navigator.vibrate(8);
    } catch (_) {}
  }

  function ensureLabel(btn, text) {
    let lab = btn.querySelector(".menu-label");
    if (!lab) {
      lab = document.createElement("span");
      lab.className = "menu-label";
      btn.appendChild(lab);
    }
    lab.textContent = text;
  }

  function setIcon(btn, kind) {
    // kind: 'dots' | 'lines'
    const html =
      kind === "dots"
        ? '<span class="dots-icon" aria-hidden="true"><i></i><i></i><i></i></span>'
        : '<span class="lines-icon" aria-hidden="true"><i></i><i></i></span>';
    const oldIcon = btn.querySelector(".dots-icon, .lines-icon");
    if (oldIcon) {
      oldIcon.outerHTML = html;
    } else {
      btn.insertAdjacentHTML("afterbegin", html);
    }
  }

  function styleHeader() {
    const header = document.querySelector(".studio-header");
    if (!header) return;
    const btns = header.querySelectorAll(".header-menu-btn");
    if (btns.length < 2) return;

    const left = btns[0];
    const right = btns[1];

    // Izquierda: dos líneas + Correo
    setIcon(left, "lines");
    ensureLabel(left, LABEL_LEFT);
    left.setAttribute("aria-label", LABEL_LEFT);
    left.title = LABEL_LEFT;

    // Derecha: tres puntos + Herramientas
    setIcon(right, "dots");
    ensureLabel(right, LABEL_RIGHT);
    right.setAttribute("aria-label", LABEL_RIGHT);
    right.title = LABEL_RIGHT;

    if (!header.dataset.drawerBound) {
      header.dataset.drawerBound = "1";
      btns.forEach((btn) => {
        btn.addEventListener("click", () => haptic(), { passive: true });
      });
    }
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
    panel.classList.add("drawer-open");
  }

  function watchPanels() {
    const obs = new MutationObserver(() => {
      styleHeader();
      document.querySelectorAll(".glass-panel").forEach(emptyPanel);
    });
    obs.observe(document.body, { childList: true, subtree: true });
  }

  function bindBackdrop() {
    document.addEventListener(
      "touchend",
      (e) => {
        const bd = e.target.closest?.(".glass-backdrop");
        if (bd) {
          haptic();
          bd.click();
        }
      },
      { passive: true }
    );
  }

  function boot() {
    styleHeader();
    bindBackdrop();
    watchPanels();
    document.documentElement.classList.add("salomon-drawers");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
  window.addEventListener("salomon:ready", boot);
})();
