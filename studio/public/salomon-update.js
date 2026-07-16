/**
 * Salomón CI/CD — sincronización automática con Render.
 * Detecta nuevo build vía /api/version y fuerza descarga de activos.
 * No toca ELEVENLABS_* (viven en el servidor).
 */
(function () {
  "use strict";

  var STORAGE_BUILD = "salomon_build_id";
  var POLL_MS = 45000;
  var AUTO_RELOAD_DELAY_MS = 3500;
  var VERSION = "cicd-1";
  var polling = false;
  var applying = false;
  var pendingBuild = null;

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

  function ensureUi() {
    if (document.getElementById("salomon-update-btn")) return;
    var btn = document.createElement("button");
    btn.id = "salomon-update-btn";
    btn.type = "button";
    btn.className = "salomon-update-btn";
    btn.title = "Actualizar Salomón (nueva versión desde Render)";
    btn.setAttribute("aria-label", "Actualizar aplicación");
    btn.innerHTML =
      '<span class="salomon-update-btn__icon" aria-hidden="true">↻</span>' +
      '<span class="salomon-update-btn__badge" hidden>1</span>';
    btn.addEventListener("click", function () {
      applyUpdate({ reason: "manual", force: true });
    });
    document.body.appendChild(btn);

    if (!document.getElementById("salomon-update-css")) {
      var s = document.createElement("style");
      s.id = "salomon-update-css";
      s.textContent =
        "#salomon-update-btn{position:fixed;right:14px;top:calc(14px + env(safe-area-inset-top,0px));" +
        "z-index:350000;width:42px;height:42px;border-radius:50%;border:1px solid rgba(212,175,55,.55);" +
        "background:rgba(0,0,0,.72);color:#f0d78c;font-size:1.15rem;cursor:pointer;" +
        "display:flex;align-items:center;justify-content:center;" +
        "box-shadow:0 6px 18px rgba(0,0,0,.4);-webkit-tap-highlight-color:transparent}" +
        "#salomon-update-btn.is-ready{border-color:#f0d78c;animation:salomonUpdatePulse 1.4s ease-in-out infinite}" +
        "#salomon-update-btn.is-busy{opacity:.55;pointer-events:none}" +
        ".salomon-update-btn__badge{position:absolute;top:-2px;right:-2px;min-width:16px;height:16px;" +
        "border-radius:8px;background:#d4af37;color:#111;font:700 10px/16px Inter,system-ui,sans-serif;" +
        "padding:0 4px}" +
        "#salomon-update-toast{position:fixed;left:50%;bottom:calc(110px + env(safe-area-inset-bottom,0px));" +
        "transform:translateX(-50%);z-index:360000;max-width:92vw;padding:10px 14px;border-radius:12px;" +
        "background:rgba(12,12,14,.9);border:1px solid rgba(212,175,55,.45);color:#f0d78c;" +
        "font:500 12px/1.35 Inter,system-ui,sans-serif;text-align:center;display:none}" +
        "#salomon-update-toast.show{display:block}" +
        "@keyframes salomonUpdatePulse{0%,100%{box-shadow:0 0 0 0 rgba(212,175,55,.45)}" +
        "50%{box-shadow:0 0 0 8px rgba(212,175,55,0)}}";
      document.head.appendChild(s);
    }

    if (!document.getElementById("salomon-update-toast")) {
      var toast = document.createElement("div");
      toast.id = "salomon-update-toast";
      toast.setAttribute("role", "status");
      document.body.appendChild(toast);
    }
  }

  function setBadge(on) {
    var btn = document.getElementById("salomon-update-btn");
    if (!btn) return;
    var badge = btn.querySelector(".salomon-update-btn__badge");
    btn.classList.toggle("is-ready", !!on);
    if (badge) badge.hidden = !on;
  }

  function toast(msg) {
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
    await Promise.all(keys.map(function (k) {
      return caches.delete(k);
    }));
  }

  async function notifySw(type) {
    if (!("serviceWorker" in navigator)) return;
    var reg = await navigator.serviceWorker.getRegistration();
    if (!reg) return;
    if (reg.waiting) {
      reg.waiting.postMessage({ type: type || "FORCE_UPDATE" });
    }
    if (reg.active) {
      reg.active.postMessage({ type: type || "PURGE_AND_CLAIM" });
    }
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
      if (pendingBuild) {
        localStorage.setItem(STORAGE_BUILD, pendingBuild);
      }
      // Reload duro: fuerza index + shield/vision/voz cliente desde red
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
        log("build inicial", build);
        return;
      }
      if (known !== build) {
        pendingBuild = build;
        log("nuevo build en Render", known, "→", build);
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
    // Cuando la pestaña vuelve al frente
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
        // Pedir update al arrancar
        try {
          reg.update();
        } catch (e) {}
      })
      .catch(function () {});

    var refreshing = false;
    navigator.serviceWorker.addEventListener("controllerchange", function () {
      if (refreshing) return;
      refreshing = true;
      log("controllerchange → reload");
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
    };
    log("CI/CD activo", VERSION);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
