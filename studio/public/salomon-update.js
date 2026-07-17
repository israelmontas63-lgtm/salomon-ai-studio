/**
 * Módulo de Actualización Proactiva — Salomón AI
 * Compara /version.json del servidor vs localStorage.
 * Si el servidor es más nuevo → force-reload invisible.
 * Indicador discreto: "Versión: X.X"
 */
(function () {
  "use strict";

  var STORAGE_KEY = "salomon_version_manifest";
  var POLL_MS = 25000;
  var VERSION_SCRIPT = "cam-2.0.7";
  var polling = false;
  var applying = false;
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
    if (!local) return false; // primera visita: solo guardar, no recargar en loop
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

  function mountInHeader() {
    var existing = document.getElementById("salomon-update-btn");
    if (existing) {
      if (!existing.closest(".studio-header")) existing.remove();
      else {
        ensureVersionBadge(readLocal());
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
      'title="Forzar actualización desde Render" aria-label="Actualizar">' +
      '<span class="salomon-update-btn__icon">' +
      SYNC_ICON +
      "</span>" +
      '<span class="salomon-update-btn__label">Actualizar</span>' +
      '<span class="salomon-update-btn__badge" hidden aria-hidden="true"></span>' +
      "</button>";

    var btns = header.querySelectorAll(".header-menu-btn");
    if (btns.length >= 2) btns[1].parentNode.insertBefore(slot, btns[1]);
    else header.appendChild(slot);

    document.getElementById("salomon-update-btn").addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      applyUpdate({ reason: "manual", force: true, silent: false });
    });

    ensureToast();
    ensureVersionBadge(readLocal());
    return true;
  }

  function ensureUi() {
    if (mountInHeader()) return;
    mountTries += 1;
    if (mountTries < 40) setTimeout(ensureUi, 250);
  }

  function setBadge(on) {
    var btn = document.getElementById("salomon-update-btn");
    if (!btn) return;
    var badge = btn.querySelector(".salomon-update-btn__badge");
    btn.classList.toggle("is-ready", !!on);
    if (badge) badge.hidden = !on;
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
      // Fallback API
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
        // Invisible: sin toast, force inmediato
        applyUpdate({
          reason: opts.reason || "proactive",
          force: true,
          silent: true,
          manifest: remote,
        });
        return;
      }

      // Misma versión: refrescar badge/build local
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
    // Al abrir la app
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
    navigator.serviceWorker.register("/sw.js?v=16").then(function (reg) {
      try {
        reg.update();
      } catch (e) {}
    }).catch(function () {});
  }

  function boot() {
    ensureUi();
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
