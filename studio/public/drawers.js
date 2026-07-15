/**
 * Menús Salomón — sin MutationObserver recursivo (causaba freeze del navegador).
 */
(function () {
  const LABEL_LEFT = "Correo";
  const LABEL_RIGHT = "Herramientas";
  let applied = false;

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
    if (lab.textContent !== text) lab.textContent = text;
  }

  function setIcon(btn, kind) {
    if (btn.dataset.iconKind === kind) return;
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
    const header = document.querySelector(".studio-header");
    if (!header) return false;
    const btns = header.querySelectorAll(".header-menu-btn");
    if (btns.length < 2) return false;

    const left = btns[0];
    const right = btns[1];
    setIcon(left, "lines");
    ensureLabel(left, LABEL_LEFT);
    left.setAttribute("aria-label", LABEL_LEFT);
    left.title = LABEL_LEFT;

    setIcon(right, "dots");
    ensureLabel(right, LABEL_RIGHT);
    right.setAttribute("aria-label", LABEL_RIGHT);
    right.title = LABEL_RIGHT;

    if (!header.dataset.drawerBound) {
      header.dataset.drawerBound = "1";
      btns.forEach(function (btn) {
        btn.addEventListener("click", function () {
          haptic();
        }, { passive: true });
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
    styleHeader();
    document.querySelectorAll(".glass-panel").forEach(emptyPanel);
  }

  function boot() {
    if (applied) {
      applyOnce();
      return;
    }
    applied = true;
    document.documentElement.classList.add("salomon-drawers");
    applyOnce();

    // Reintentos acotados (máx 10) — NO MutationObserver (provocaba bucle infinito)
    var tries = 0;
    var id = setInterval(function () {
      tries += 1;
      var ok = styleHeader();
      document.querySelectorAll(".glass-panel").forEach(emptyPanel);
      if (ok || tries >= 10) clearInterval(id);
    }, 500);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
  window.addEventListener("salomon:ready", applyOnce);
})();
