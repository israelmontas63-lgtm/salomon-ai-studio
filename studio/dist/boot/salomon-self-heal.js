/**
 * Salomón AI — Sistema de Autosaneamiento v2.0.0 (Self-Healing)
 * Vigilante: evaluateHealth() → forceReset() / Default Layout de emergencia.
 * No sustituye el bundle estable; cura pantallas blancas y estados rotos.
 *
 * Consola (cada evaluación):
 *   Salomón AI - Status: [OK/ERROR] - Action: [Healed/Active]
 */
(function () {
  "use strict";

  var TAG = "Salomón AI";
  var VERSION = "self-heal-2.0.0";
  var CHECK_MS = 2200;
  var MAX_HEALS = 2;
  var healCount = 0;
  var lastStatus = "INIT";
  var watching = false;
  var whiteHits = 0;

  function logStatus(status, action) {
    try {
      console.info(TAG + " - Status: [" + status + "] - Action: [" + action + "]");
    } catch (e) {}
  }

  function rootEl() {
    return document.getElementById("root");
  }

  function hasCriticalUi() {
    var root = rootEl();
    if (!root) return false;
    var shell = root.querySelector(".app-shell");
    var chat = root.querySelector(".chat-body");
    var bar = root.querySelector(".bottom-bar, .controls-row");
    if (!shell || !chat || !bar) return false;
    if (typeof shell === "undefined" || typeof chat === "undefined" || typeof bar === "undefined") {
      return false;
    }
    return true;
  }

  function isLoadingLoop() {
    var splash = document.getElementById("salomon-splash");
    var booted = document.documentElement.classList.contains("salomon-booted");
    if (splash && !splash.classList.contains("hide") && booted) return true;
    var root = rootEl();
    if (root && !root.children.length && booted) return true;
    if (document.getElementById("salomon-boot-error") && !hasCriticalUi()) return true;
    return false;
  }

  function isWhiteScreen() {
    var root = rootEl();
    if (!root) return true;
    if (!root.children.length) return true;
    if (!hasCriticalUi()) {
      try {
        var bg = window.getComputedStyle(document.body).backgroundColor || "";
        if (/rgb\(\s*255\s*,\s*255\s*,\s*255\s*\)/i.test(bg) || bg === "rgba(0, 0, 0, 0)") {
          return true;
        }
        var rect = root.getBoundingClientRect();
        if (rect.height < 40 && !document.querySelector(".ui-camera-overlay, .camera-view")) {
          return true;
        }
      } catch (e) {
        return true;
      }
      return true;
    }
    return false;
  }

  /**
   * Evaluación previa/continua. Verifica componentes críticos, bucles de carga y blanco.
   * Imprime siempre el log de diagnóstico requerido.
   */
  function evaluateHealth() {
    var result;
    try {
      if (typeof document === "undefined" || !document.body) {
        result = { ok: false, reason: "document_undefined" };
      } else if (!rootEl()) {
        result = { ok: false, reason: "root_undefined" };
      } else {
        var splash = document.getElementById("salomon-splash");
        var booted = document.documentElement.classList.contains("salomon-booted");
        var stillBooting = splash && !splash.classList.contains("hide") && !booted;
        if (stillBooting) {
          result = { ok: true, reason: "booting" };
        } else {
          try {
            if (typeof performance !== "undefined" && performance.now() < 5500 && !hasCriticalUi()) {
              result = { ok: true, reason: "grace_mount" };
            }
          } catch (e) {}
          if (!result) {
            if (isLoadingLoop()) {
              result = { ok: false, reason: "loading_loop" };
            } else if (isWhiteScreen()) {
              result = { ok: false, reason: "white_screen" };
            } else if (!hasCriticalUi()) {
              result = { ok: false, reason: "critical_undefined" };
            } else {
              result = { ok: true, reason: "healthy" };
            }
          }
        }
      }
    } catch (err) {
      result = { ok: false, reason: "exception:" + ((err && err.message) || "unknown") };
    }

    // Log de diagnóstico obligatorio en cada evaluación
    if (result.ok) logStatus("OK", "Active");
    else logStatus("ERROR", "Healed");
    return result;
  }

  function injectDefaultLayout() {
    var root = rootEl();
    if (!root) {
      root = document.createElement("div");
      root.id = "root";
      document.body.appendChild(root);
    }
    if (document.getElementById("salomon-emergency-layout")) return;

    var box = document.createElement("div");
    box.id = "salomon-emergency-layout";
    box.setAttribute("role", "alert");
    box.style.cssText =
      "position:fixed;inset:0;z-index:200000;display:flex;flex-direction:column;" +
      "align-items:center;justify-content:center;gap:16px;padding:24px;" +
      "background:#0a0a0a;color:#f0d78c;font:500 15px/1.45 Inter,system-ui,sans-serif;text-align:center";
    box.innerHTML =
      '<div style="font-size:1.4rem;letter-spacing:0.12em;color:#d4af37">SALOMÓN AI</div>' +
      '<div style="max-width:340px;opacity:0.9">Modo de emergencia activo. La interfaz principal se está regenerando.</div>' +
      '<button type="button" id="salomon-heal-reload" style="' +
      "margin-top:8px;padding:12px 18px;border:none;border-radius:12px;cursor:pointer;" +
      "background:linear-gradient(145deg,#f0d78c,#d4af37);color:#1a1508;font:600 14px Inter,sans-serif" +
      '">Reintentar ahora</button>';
    document.body.appendChild(box);

    var btn = document.getElementById("salomon-heal-reload");
    if (btn) {
      btn.addEventListener("click", function () {
        forceReset(true);
      });
    }
  }

  function clearEmergencyLayout() {
    var el = document.getElementById("salomon-emergency-layout");
    if (el) el.remove();
  }

  /** Recarga segura del estado inicial + layout de emergencia (no colapsa en blanco). */
  function forceReset(hard) {
    healCount += 1;
    try {
      sessionStorage.setItem("salomon_heal_count", String(healCount));
      sessionStorage.setItem("salomon_last_heal", String(Date.now()));
    } catch (e) {}

    clearEmergencyLayout();
    injectDefaultLayout();
    logStatus("ERROR", "Healed");

    if (hard || healCount >= MAX_HEALS) {
      setTimeout(function () {
        var url = "/?_salomon_heal=" + Date.now() + "&_v=2.0.4";
        window.location.replace(url);
      }, 350);
      return;
    }

    try {
      var splash = document.getElementById("salomon-splash");
      if (splash) {
        splash.classList.add("hide");
        splash.remove();
      }
      document.documentElement.classList.add("salomon-booted");
    } catch (e) {}

    setTimeout(runWatchdog, 900);
  }

  function runWatchdog() {
    var health = evaluateHealth();
    if (health.ok) {
      clearEmergencyLayout();
      lastStatus = "OK";
      return;
    }
    lastStatus = "ERROR";
    whiteHits += 1;
    if (whiteHits >= 2 || healCount >= MAX_HEALS) {
      forceReset(true);
    } else {
      forceReset(false);
    }
  }

  function startWatching() {
    if (watching) return;
    watching = true;
    try {
      healCount = parseInt(sessionStorage.getItem("salomon_heal_count") || "0", 10) || 0;
      var last = parseInt(sessionStorage.getItem("salomon_last_heal") || "0", 10) || 0;
      if (Date.now() - last > 120000) {
        healCount = 0;
        sessionStorage.setItem("salomon_heal_count", "0");
      }
    } catch (e) {}

    // Evaluación previa (antes de que un blanco prolongado llegue al usuario)
    setTimeout(function () {
      var pre = evaluateHealth();
      if (!pre.ok) setTimeout(runWatchdog, CHECK_MS);
    }, 1200);

    setInterval(function () {
      var h = evaluateHealth();
      if (h.ok) {
        lastStatus = "OK";
        whiteHits = 0;
        clearEmergencyLayout();
      } else {
        runWatchdog();
      }
    }, CHECK_MS + 800);
  }

  window.SalomonSelfHeal = {
    version: VERSION,
    evaluateHealth: evaluateHealth,
    forceReset: forceReset,
    injectDefaultLayout: injectDefaultLayout,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startWatching);
  } else {
    startWatching();
  }
})();
