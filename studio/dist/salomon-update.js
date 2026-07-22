/**
 * Módulo de Actualización Proactiva — Salomón AI
 * Compara /version.json del servidor vs localStorage.
 * Si el servidor es más nuevo → force-reload invisible.
 * Indicador discreto: "Versión: X.X"
 * "Actualizar" vive solo dentro del menú H (Herramientas).
 */
(function () {
  "use strict";

  var STORAGE_KEY = "salomon_version_manifest";
  var POLL_MS = 25000;
  var VERSION_SCRIPT = "camera-13.0.0";
  var MENU_LABEL = "Actualizar";
  var polling = false;
  var applying = false;
  var menuObserver = null;

  function log() {
    try {
      console.info.apply(console, ["[Salomon Update]"].concat([].slice.call(arguments)));
    } catch (e) {}
  }

  function readLocal() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function writeLocal(manifest) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(manifest));
    } catch (e) {}
  }

  function parseVer(v) {
    return String(v || "0")
      .split(/[.+-]/)
      .map(function (n) {
        var x = parseInt(n, 10);
        return isNaN(x) ? 0 : x;
      });
  }

  /** true si remote es más nuevo que local */
  function isNewer(remote, local) {
    if (!remote) return false;
    if (!local) return false;
    var rt = Number(remote.timestamp) || 0;
    var lt = Number(local.timestamp) || 0;
    if (rt > 0 && lt > 0 && rt > lt) return true;
    var rv = parseVer(remote.version);
    var lv = parseVer(local.version);
    var len = Math.max(rv.length, lv.length);
    for (var i = 0; i < len; i++) {
      var a = rv[i] || 0;
      var b = lv[i] || 0;
      if (a > b) return true;
      if (a < b) return false;
    }
    var rb = String(remote.build || "");
    var lb = String(local.build || "");
    if (rb && lb && rb !== lb && rt >= lt) return true;
    return false;
  }

  function ensureToast() {
    if (document.getElementById("salomon-update-toast")) return;
    var toast = document.createElement("div");
    toast.id = "salomon-update-toast";
    toast.setAttribute("role", "status");
    document.body.appendChild(toast);
  }

  function ensureVersionBadge(manifest) {
    var el = document.getElementById("salomon-version-badge");
    if (!el) {
      el = document.createElement("div");
      el.id = "salomon-version-badge";
      el.setAttribute("aria-live", "polite");
      document.body.appendChild(el);
    }
    var ver = (manifest && manifest.version) || "—";
    el.textContent = "Versión: " + ver;
    el.title = manifest
      ? "build " + (manifest.build || "?") + " · " + (manifest.timestamp_iso || "")
      : "Salomón AI";
  }

  /** Quita el botón flotante del header (ya no debe aparecer fuera del menú H). */
  function removeHeaderUpdateButton() {
    var slots = document.querySelectorAll(".salomon-update-slot");
    for (var i = 0; i < slots.length; i++) slots[i].remove();
    var orphan = document.getElementById("salomon-update-btn");
    if (orphan && !orphan.classList.contains("glass-panel__item")) orphan.remove();
  }

  function toolsPanelNav() {
    var panel =
      document.querySelector(".glass-panel.drawer-open.glass-panel--right") ||
      document.querySelector(".glass-panel--right.drawer-open") ||
      document.querySelector('.glass-panel[aria-label="Herramientas"]');
    if (!panel) {
      var panels = document.querySelectorAll(".glass-panel");
      for (var i = 0; i < panels.length; i++) {
        var h2 = panels[i].querySelector(".glass-panel__header h2");
        if (h2 && /Herramientas/i.test(h2.textContent || "")) {
          panel = panels[i];
          break;
        }
      }
    }
    return panel ? panel.querySelector(".glass-panel__list") : null;
  }

  function findUpdateMenuItem(nav) {
    if (!nav) return null;
    var items = nav.querySelectorAll(".glass-panel__item, button");
    for (var i = 0; i < items.length; i++) {
      var t = (items[i].textContent || "").replace(/\s+/g, " ").trim();
      if (t === MENU_LABEL || items[i].id === "salomon-update-btn") return items[i];
    }
    return null;
  }

  function onUpdateClick(e) {
    e.preventDefault();
    e.stopPropagation();
    applyUpdate({ reason: "manual", force: true, silent: false });
  }

  function ensureUpdateInToolsMenu() {
    removeHeaderUpdateButton();
    var nav = toolsPanelNav();
    if (!nav) return false;

    var existing = findUpdateMenuItem(nav);
    if (existing) {
      existing.id = "salomon-update-btn";
      existing.classList.add("glass-panel__item", "salomon-update-menu-item");
      if (!existing.dataset.salomonUpdateBound) {
        existing.dataset.salomonUpdateBound = "1";
        existing.addEventListener("click", onUpdateClick);
      }
      return true;
    }

    // React aún no pintó items: no insertar placeholder suelto
    if (!nav.querySelector(".glass-panel__item")) return false;

    var btn = document.createElement("button");
    btn.type = "button";
    btn.id = "salomon-update-btn";
    btn.className = "glass-panel__item salomon-update-menu-item";
    btn.textContent = MENU_LABEL;
    btn.setAttribute("aria-label", MENU_LABEL);
    btn.title = "Forzar actualización desde Render";
    btn.dataset.salomonUpdateBound = "1";
    btn.addEventListener("click", onUpdateClick);
    nav.appendChild(btn);
    return true;
  }

  function watchToolsMenu() {
    if (menuObserver) return;
    var root = document.getElementById("root") || document.body;
    menuObserver = new MutationObserver(function () {
      ensureUpdateInToolsMenu();
    });
    try {
      menuObserver.observe(root, { childList: true, subtree: true });
    } catch (e) {}
  }

  function setBadge(on) {
    var btn = document.getElementById("salomon-update-btn");
    if (!btn) return;
    btn.classList.toggle("is-ready", !!on);
    if (on) btn.setAttribute("data-update-ready", "1");
    else btn.removeAttribute("data-update-ready");
  }

  function toast(msg) {
    if (!msg) return;
    ensureToast();
    var el = document.getElementById("salomon-update-toast");
    if (!el) return;
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(function () {
      el.classList.remove("show");
    }, 5000);
  }

  async function clearCaches() {
    if (!("caches" in window)) return;
    var keys = await caches.keys();
    await Promise.all(keys.map(function (k) { return caches.delete(k); }));
  }

  async function unregisterAllSw() {
    if (!("serviceWorker" in navigator)) return;
    var regs = await navigator.serviceWorker.getRegistrations();
    await Promise.all(regs.map(function (r) { return r.unregister(); }));
  }

  async function warmNetworkBust() {
    var stamp = String(Date.now());
    var urls = [
      "/version.json?t=" + stamp,
      "/?_salomon_force=" + stamp,
      "/salomon-ui-shield.css?v=p-" + stamp,
      "/salomon-update.js?v=p-" + stamp,
      "/salomon-self-heal.js?v=p-" + stamp,
      "/salomon-ui-shield.js?v=p-" + stamp,
      "/salomon-orchestrator-bridge.js?v=p-" + stamp,
      "/vision-overlay.js?v=p-" + stamp,
      "/header-logo-spec.css?v=p-" + stamp,
    ];
    await Promise.all(
      urls.map(function (u) {
        return fetch(u, { cache: "reload", credentials: "same-origin" }).catch(function () {});
      })
    );
  }

  async function applyUpdate(opts) {
    opts = opts || {};
    if (applying) return;
    applying = true;
    var btn = document.getElementById("salomon-update-btn");
    if (btn) btn.classList.add("is-busy");
    if (!opts.silent) toast("Actualizando Salomón…");

    try {
      if (navigator.serviceWorker && navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({ type: "FORCE_RELOAD_PREP" });
      }
      await clearCaches();
      await unregisterAllSw();
      await clearCaches();
      await warmNetworkBust();
      if (opts.manifest) writeLocal(opts.manifest);
      window.location.replace(
        "/?_salomon_force=" + Date.now() + "&_v=" + encodeURIComponent(VERSION_SCRIPT)
      );
    } catch (e) {
      log("apply fail", e && e.message);
      applying = false;
      if (btn) btn.classList.remove("is-busy");
      if (!opts.silent) toast("Reintentando actualización…");
      setTimeout(function () {
        window.location.href = "/?_salomon_force=" + Date.now();
      }, 350);
    }
  }

  async function fetchRemoteVersion() {
    var res = await fetch("/version.json?t=" + Date.now(), {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!res.ok) {
      res = await fetch("/api/version?t=" + Date.now(), { cache: "no-store" });
    }
    if (!res.ok) throw new Error("version_http_" + res.status);
    return res.json();
  }

  async function checkOnce(opts) {
    opts = opts || {};
    try {
      var remote = await fetchRemoteVersion();
      if (!remote || !remote.version) return;
      ensureVersionBadge(remote);

      var local = readLocal();
      if (!local) {
        writeLocal(remote);
        ensureVersionBadge(remote);
        log("manifest inicial", remote.version, remote.build);
        return;
      }

      if (isNewer(remote, local)) {
        log("servidor más nuevo → reload invisible", local.version, "→", remote.version);
        setBadge(true);
        writeLocal(remote);
        applyUpdate({
          reason: opts.reason || "proactive",
          force: true,
          silent: true,
          manifest: remote,
        });
        return;
      }

      writeLocal(remote);
      ensureVersionBadge(remote);
      setBadge(false);
    } catch (e) {
      log("check", e && e.message);
      ensureVersionBadge(readLocal());
    }
  }

  function startPolling() {
    if (polling) return;
    polling = true;
    checkOnce({ reason: "boot" });
    setInterval(function () {
      checkOnce({ reason: "poll" });
    }, POLL_MS);
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "visible") checkOnce({ reason: "focus" });
    });
  }

  function registerSw() {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/service-worker.js?v=107").then(function (reg) {
      try {
        reg.update();
      } catch (e) {}
    }).catch(function () {
      navigator.serviceWorker.register("/sw.js?v=107").catch(function () {});
    });
  }

  function boot() {
    document.documentElement.classList.add("salomon-mockup-ui");
    removeHeaderUpdateButton();
    ensureToast();
    ensureVersionBadge(readLocal());
    ensureUpdateInToolsMenu();
    watchToolsMenu();
    registerSw();
    startPolling();
    window.SalomonUpdate = {
      version: VERSION_SCRIPT,
      check: function () {
        return checkOnce({ reason: "api" });
      },
      apply: function () {
        return applyUpdate({ reason: "api", force: true, silent: false });
      },
    };
    log("actualización proactiva activa", VERSION_SCRIPT);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
