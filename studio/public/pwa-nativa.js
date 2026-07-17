/**
 * PWA Nativa v103 — registro SW, install prompt, nucleo identidad/inmune.
 * Created by Israel Monta - Salomon AI Studio
 */
(function () {
  "use strict";
  if (window.__SalomonPwaNativa) return;

  var SW_URL = "/service-worker.js?v=105";
  var IDENTITY_KEY = "salomon_pwa_identidad_v105";
  var deferredPrompt = null;

  function log() {
    try {
      if (localStorage.getItem("salomon_pwa_debug") === "1") {
        console.log.apply(console, ["[PWA105]"].concat([].slice.call(arguments)));
      }
    } catch (_) {}
  }

  function registerSw() {
    if (!("serviceWorker" in navigator)) return Promise.resolve(null);
    return navigator.serviceWorker
      .register(SW_URL, { scope: "/" })
      .then(function (reg) {
        log("SW registered", reg.scope);
        try {
          reg.update();
        } catch (_) {}
        return reg;
      })
      .catch(function (err) {
        log("SW register fail", err);
        return navigator.serviceWorker.register("/sw.js?v=105").catch(function () {
          return null;
        });
      });
  }

  function hydrateIdentidad() {
    return fetch("/api/identidad", { credentials: "same-origin" })
      .then(function (r) {
        return r.ok ? r.json() : null;
      })
      .then(function (data) {
        if (!data) return null;
        try {
          localStorage.setItem(IDENTITY_KEY, JSON.stringify(data));
        } catch (_) {}
        window.__SalomonIdentidad = data;
        log("identidad en núcleo PWA", data.creador);
        return data;
      })
      .catch(function () {
        try {
          var raw = localStorage.getItem(IDENTITY_KEY);
          if (raw) {
            window.__SalomonIdentidad = JSON.parse(raw);
            return window.__SalomonIdentidad;
          }
        } catch (_) {}
        return null;
      });
  }

  function hydrateInmune() {
    return fetch("/api/inmune", { credentials: "same-origin" })
      .then(function (r) {
        return r.ok ? r.json() : null;
      })
      .then(function (data) {
        if (data) window.__SalomonInmune = data;
        return data;
      })
      .catch(function () {
        return null;
      });
  }

  function hydrateWebArchitect() {
    return fetch("/api/web/arquitecto", { credentials: "same-origin" })
      .then(function (r) {
        return r.ok ? r.json() : null;
      })
      .then(function (data) {
        if (data) window.__SalomonWebArchitect = data;
        return data;
      })
      .catch(function () {
        return null;
      });
  }

  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;
    window.__SalomonPwaInstallReady = true;
    document.documentElement.setAttribute("data-pwa-installable", "1");
    log("install prompt ready");
  });

  window.addEventListener("appinstalled", function () {
    deferredPrompt = null;
    window.__SalomonPwaInstalled = true;
    document.documentElement.setAttribute("data-pwa-installed", "1");
    log("app installed");
  });

  function promptInstall() {
    if (!deferredPrompt) {
      return Promise.resolve({ ok: false, reason: "no_prompt" });
    }
    deferredPrompt.prompt();
    return deferredPrompt.userChoice.then(function (choice) {
      deferredPrompt = null;
      return { ok: choice.outcome === "accepted", outcome: choice.outcome };
    });
  }

  function isStandalone() {
    return (
      window.matchMedia("(display-mode: standalone)").matches ||
      window.navigator.standalone === true
    );
  }

  function boot() {
    document.documentElement.setAttribute("data-pwa-v", "97");
    if (isStandalone()) {
      document.documentElement.setAttribute("data-pwa-standalone", "1");
    }
    registerSw();
    hydrateIdentidad();
    hydrateInmune();
    hydrateWebArchitect();
  }

  window.__SalomonPwaNativa = {
    version: "97.0.0",
    registerSw: registerSw,
    promptInstall: promptInstall,
    isStandalone: isStandalone,
    getIdentidad: function () {
      return window.__SalomonIdentidad || null;
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
