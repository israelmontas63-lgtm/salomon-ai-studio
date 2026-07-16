/**
 * Salomón CI/CD — botón Actualizar en header (maqueta aprobada).
 * Estado 1: idle (borde oro). Estado 2: is-ready (relleno oro + badge).
 */
(function () {
  "use strict";

  var STORAGE_BUILD = "salomon_build_id";
  var POLL_MS = 45000;
  var AUTO_RELOAD_DELAY_MS = 3500;
  var VERSION = "mockup-header-1";
  var polling = false;
  var applying = false;
  var pendingBuild = null;
  var mountTries = 0;

  var SYNC_ICON =
    '<svg class="salomon-update-btn__svg" viewBox="0 0 24 24" aria-hidden="true">' +
    '<path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" ' +
    'd="M20 12a8 8 0 1 1-2.2-5.4"/>' +
    '<path fill="currentColor" d="M20 4v5h-5l5-5z"/>' +
    "</svg>";

  function log() {
    try {
      console.info.apply(console, ["[Salomon Update]"].concat([].slice.call(arguments)));
    } catch (e) {}
  }

  function isVoiceBusy() {
    try {
      if (!window.SalomonBridge || typeof window.SalomonBridge.getState !== "function") {
        return false;
      }
      var s = window.SalomonBridge.getState();
      return s === "DICTATING" || s === "CONVERSATION" || s === "PROCESSING";
    } catch (e) {
      return false;
    }
  }

  function ensureToast() {
    if (document.getElementById("salomon-update-toast")) return;
    var toast = document.createElement("div");
    toast.id = "salomon-update-toast";
    toast.setAttribute("role", "status");
    document.body.appendChild(toast);
  }

  function mountInHeader() {
    var existing = document.getElementById("salomon-update-btn");
    if (existing) {
      // Migrar FAB antiguo al header si quedó suelto
      if (!existing.closest(".studio-header")) {
        existing.remove();
      } else {
        return true;
      }
    }

    var header = document.querySelector(".studio-header");
    if (!header) return false;

    document.documentElement.classList.add("salomon-mockup-ui");

    var slot = document.createElement("div");
    slot.className = "salomon-update-slot";
    slot.innerHTML =
      '<button type="button" id="salomon-update-btn" class="salomon-update-btn" ' +
      'title="Actualizar Salomón desde Render" aria-label="Actualizar">' +
      '<span class="salomon-update-btn__icon">' +
      SYNC_ICON +
      "</span>" +
      '<span class="salomon-update-btn__label">Actualizar</span>' +
      '<span class="salomon-update-btn__badge" hidden aria-hidden="true"></span>' +
      "</button>";

    var btns = header.querySelectorAll(".header-menu-btn");
    if (btns.length >= 2) {
      btns[1].parentNode.insertBefore(slot, btns[1]);
    } else {
      header.appendChild(slot);
    }

    var btn = document.getElementById("salomon-update-btn");
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      applyUpdate({ reason: "manual", force: true });
    });

    ensureToast();
    log("Actualizar montado en header");
    return true;
  }

  function ensureUi() {
    if (mountInHeader()) return;
    mountTries += 1;
    if (mountTries < 40) {
      setTimeout(ensureUi, 250);
    }
  }

  function setBadge(on) {
    var btn = document.getElementById("salomon-update-btn");
    if (!btn) return;
    var badge = btn.querySelector(".salomon-update-btn__badge");
    btn.classList.toggle("is-ready", !!on);
    btn.setAttribute("data-state", on ? "2" : "1");
    if (badge) badge.hidden = !on;
  }

  function toast(msg) {
    ensureToast();
    var el = document.getElementById("salomon-update-toast");
    if (!el) return;
    el.textContent = msg || "";
    el.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(function () {
      el.classList.remove("show");
    }, 5000);
  }

  async function clearCaches() {
    if (!("caches" in window)) return;
    var keys = await caches.keys();
    await Promise.all(
      keys.map(function (k) {
        return caches.delete(k);
      })
    );
  }

  async function notifySw(type) {
    if (!("serviceWorker" in navigator)) return;
    var reg = await navigator.serviceWorker.getRegistration();
    if (!reg) return;
    if (reg.waiting) reg.waiting.postMessage({ type: type || "FORCE_UPDATE" });
    if (reg.active) reg.active.postMessage({ type: type || "PURGE_AND_CLAIM" });
    try {
      await reg.update();
    } catch (e) {}
  }

  async function applyUpdate(opts) {
    opts = opts || {};
    if (applying) return;
    if (!opts.force && isVoiceBusy()) {
      toast("Nueva versión lista. Se aplicará al terminar la conversación…");
      setBadge(true);
      setTimeout(function () {
        if (!isVoiceBusy()) applyUpdate({ reason: "retry-idle", force: true });
      }, 8000);
      return;
    }
    applying = true;
    var btn = document.getElementById("salomon-update-btn");
    if (btn) btn.classList.add("is-busy");
    toast("Actualizando Salomón desde Render…");
    try {
      await notifySw("PURGE_AND_CLAIM");
      await clearCaches();
      if (pendingBuild) localStorage.setItem(STORAGE_BUILD, pendingBuild);
      var url = new URL(window.location.href);
      url.searchParams.set("_salomon_update", String(Date.now()));
      window.location.replace(url.toString());
    } catch (e) {
      log("apply fail", e && e.message);
      applying = false;
      if (btn) btn.classList.remove("is-busy");
      toast("No se pudo actualizar. Reintenta.");
    }
  }

  async function fetchBuild() {
    var res = await fetch("/api/version?t=" + Date.now(), {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!res.ok) throw new Error("version_http_" + res.status);
    return res.json();
  }

  async function checkOnce() {
    try {
      var data = await fetchBuild();
      var build = String(data.build || data.build_id || "").trim();
      if (!build) return;
      var known = localStorage.getItem(STORAGE_BUILD) || "";
      if (!known) {
        localStorage.setItem(STORAGE_BUILD, build);
        return;
      }
      if (known !== build) {
        pendingBuild = build;
        setBadge(true);
        toast("Nueva versión en Render. Actualizando…");
        setTimeout(function () {
          applyUpdate({ reason: "auto", force: false });
        }, AUTO_RELOAD_DELAY_MS);
      }
    } catch (e) {
      log("check", e && e.message);
    }
  }

  function startPolling() {
    if (polling) return;
    polling = true;
    checkOnce();
    setInterval(checkOnce, POLL_MS);
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "visible") checkOnce();
    });
  }

  function registerSw() {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker
      .register("/sw.js?v=8")
      .then(function (reg) {
        reg.addEventListener("updatefound", function () {
          var nw = reg.installing;
          if (!nw) return;
          nw.addEventListener("statechange", function () {
            if (nw.state === "installed" && navigator.serviceWorker.controller) {
              setBadge(true);
              toast("Actualización lista. Aplicando…");
              setTimeout(function () {
                applyUpdate({ reason: "sw-updatefound", force: false });
              }, 1200);
            }
          });
        });
        try {
          reg.update();
        } catch (e) {}
      })
      .catch(function () {});

    var refreshing = false;
    navigator.serviceWorker.addEventListener("controllerchange", function () {
      if (refreshing) return;
      refreshing = true;
      window.location.reload();
    });
  }

  function boot() {
    ensureUi();
    registerSw();
    startPolling();
    window.SalomonUpdate = {
      version: VERSION,
      check: checkOnce,
      apply: function () {
        return applyUpdate({ reason: "api", force: true });
      },
      setReady: setBadge,
    };
    log("CI/CD header mockup", VERSION);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
