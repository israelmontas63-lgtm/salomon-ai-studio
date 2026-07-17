/**
 * Salomón Security Kernel v23.0.0 — INMORTAL
 * Capa de defensa: Sandbox Proxy · Telemetría · Resource Limiter · Integrity Lock
 * NO modifica CameraEngine (Estado Dorado). Se envuelve por encima.
 */
(function (global) {
  "use strict";

  var VERSION = "23.0.0";
  var PROTOCOL = "SALOMON_INMORTAL";

  // Límites hardware (Redmi 13C / longevidad)
  var MAX_GUM_PER_MIN = 8;
  var MAX_SWITCH_PER_30S = 6;
  var MIN_SWITCH_GAP_MS = 400;
  var MIN_GUM_GAP_MS = 280;
  var ANOMALY_WINDOW_MS = 30000;

  var state = {
    gumCalls: [],
    switchCalls: [],
    lastGumAt: 0,
    lastSwitchAt: 0,
    redAlerts: 0,
    denied: 0,
    locked: true,
  };

  function now() {
    return Date.now();
  }

  function prune(arr, windowMs) {
    var t = now();
    while (arr.length && t - arr[0] > windowMs) arr.shift();
  }

  function stackTrace() {
    try {
      return (new Error("INTEGRITY")).stack || "(no stack)";
    } catch (e) {
      return "(stack unavailable)";
    }
  }

  function logAttempt(component, detail) {
    var entry = {
      at: new Date().toISOString(),
      component: component,
      detail: detail,
      protocol: PROTOCOL,
    };
    state.denied += 1;
    try {
      console.warn(
        "[SalomonInmortal] Intento de modificación/acceso no autorizado detectado en " +
          component +
          ". Acceso denegado.",
        detail
      );
    } catch (e) {}
    try {
      var key = "salomon_integrity_attempts";
      var prev = [];
      try {
        prev = JSON.parse(sessionStorage.getItem(key) || "[]");
      } catch (e2) {}
      prev.push(entry);
      if (prev.length > 40) prev = prev.slice(-40);
      sessionStorage.setItem(key, JSON.stringify(prev));
    } catch (e3) {}
    try {
      global.dispatchEvent(
        new CustomEvent("salomon:integrity-denied", { detail: entry })
      );
    } catch (e4) {}
    return entry;
  }

  /** ALERTA ROJA — anomalía térmica/CPU (ráfagas agresivas). */
  function redAlert(reason, meta) {
    state.redAlerts += 1;
    var payload = {
      level: "RED",
      reason: reason,
      meta: meta || {},
      stack: stackTrace(),
      at: new Date().toISOString(),
    };
    try {
      console.error(
        "[SalomonInmortal] ALERTA ROJA DE INTEGRIDAD — " + reason,
        payload
      );
    } catch (e) {}
    // Zero-Lag / Non-Distraction: liberar buffers solo bajo estrés (sin timers permanentes)
    try {
      if (state.gumCalls.length > 12) state.gumCalls = state.gumCalls.slice(-8);
      if (state.switchCalls.length > 12) state.switchCalls = state.switchCalls.slice(-6);
    } catch (eGc) {}
    try {
      global.dispatchEvent(
        new CustomEvent("salomon:integrity-red-alert", { detail: payload })
      );
    } catch (e2) {}
    return payload;
  }

  /**
   * Power & Resource Limiter — corta acceso agresivo al hardware.
   * @returns {{ok:boolean, reason?:string}}
   */
  function resourceAllow(kind) {
    var t = now();
    if (kind === "getUserMedia") {
      if (t - state.lastGumAt < MIN_GUM_GAP_MS) {
        redAlert("GUM_BURST", { gap: t - state.lastGumAt });
        return { ok: false, reason: "GUM_GAP" };
      }
      prune(state.gumCalls, 60000);
      if (state.gumCalls.length >= MAX_GUM_PER_MIN) {
        redAlert("GUM_RATE_LIMIT", { count: state.gumCalls.length });
        return { ok: false, reason: "GUM_RATE" };
      }
      state.gumCalls.push(t);
      state.lastGumAt = t;
      return { ok: true };
    }
    if (kind === "switch") {
      if (t - state.lastSwitchAt < MIN_SWITCH_GAP_MS) {
        redAlert("SWITCH_BURST", { gap: t - state.lastSwitchAt });
        return { ok: false, reason: "SWITCH_GAP" };
      }
      prune(state.switchCalls, ANOMALY_WINDOW_MS);
      if (state.switchCalls.length >= MAX_SWITCH_PER_30S) {
        redAlert("SWITCH_RATE_LIMIT", { count: state.switchCalls.length });
        return { ok: false, reason: "SWITCH_RATE" };
      }
      state.switchCalls.push(t);
      state.lastSwitchAt = t;
      return { ok: true };
    }
    return { ok: true };
  }

  /**
   * Proxy de Seguridad — valida acciones de hardware antes de llegar al Core.
   */
  function hardwareProxy(action, run) {
    var gate = resourceAllow(action);
    if (!gate.ok) {
      logAttempt("HardwareProxy:" + action, gate.reason);
      return Promise.reject(new Error("INMORTAL_BLOCKED:" + gate.reason));
    }
    try {
      return Promise.resolve(run());
    } catch (err) {
      redAlert("PROXY_THROW", { action: action, message: err && err.message });
      return Promise.reject(err);
    }
  }

  /** Envuelve getUserMedia sin alterar CameraEngine. */
  function installMediaDevicesProxy() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;
    if (navigator.mediaDevices.__salomonInmortalPatched) return;
    var native = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = function (constraints) {
      return hardwareProxy("getUserMedia", function () {
        return native(constraints);
      });
    };
    navigator.mediaDevices.__salomonInmortalPatched = true;
  }

  /** Envuelve API de cámara publicada (flip/switch) — sandbox sobre el Core. */
  function installCameraApiProxy() {
    var names = ["SalomonCameraV13", "SalomonCameraV14", "SalomonCameraV15", "SalomonCameraV16", "SalomonCameraV20"];
    names.forEach(function (name) {
      var api = global[name];
      if (!api || api.__salomonInmortalWrapped) return;
      ["flip", "rotateCamera", "switchFacing", "switchCamera"].forEach(function (fn) {
        if (typeof api[fn] !== "function") return;
        var orig = api[fn].bind(api);
        api[fn] = function () {
          var args = arguments;
          return hardwareProxy("switch", function () {
            return orig.apply(api, args);
          });
        };
      });
      api.__salomonInmortalWrapped = true;
    });
  }

  /**
   * Read-Only Lock virtual para Estado Dorado.
   * Expone chequeo; la escritura real la bloquea el agente Cursor + ledger.
   */
  var GOLDEN_LOCK = {
    protocol: PROTOCOL,
    version: VERSION,
    immutableCore: [
      "studio/dist/camera-engine.js",
      "studio/dist/camera-v13.js",
      "studio/src/features/camera_v13/MediaStreamManager.js",
    ],
    assertWritable: function (filePath) {
      var hit = GOLDEN_LOCK.immutableCore.some(function (p) {
        return filePath && (filePath === p || filePath.indexOf("camera-engine") !== -1);
      });
      if (hit && state.locked) {
        logAttempt(filePath || "GoldenCore", "READ_ONLY_LOCK");
        return {
          allowed: false,
          prompt:
            "Israel, el cambio propuesto en [" +
            (filePath || "GoldenCore") +
            "] altera el Golden State. ¿Autorizas la modificación o la rechazas para mantener la integridad?",
        };
      }
      return { allowed: true };
    },
  };

  function boot() {
    installMediaDevicesProxy();
    installCameraApiProxy();
    // Re-wrap cuando el UI camera cargue un instante después (defer)
    setTimeout(installCameraApiProxy, 0);
    setTimeout(installCameraApiProxy, 500);
    setTimeout(installCameraApiProxy, 1500);
    try {
      console.info(
        "[SalomonInmortal] Security Kernel " + VERSION + " — sandbox + limiter + telemetría ON"
      );
    } catch (e) {}
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  global.SalomonSecurityKernel = {
    version: VERSION,
    protocol: PROTOCOL,
    hardwareProxy: hardwareProxy,
    resourceAllow: resourceAllow,
    redAlert: redAlert,
    logAttempt: logAttempt,
    goldenLock: GOLDEN_LOCK,
    getStats: function () {
      return {
        redAlerts: state.redAlerts,
        denied: state.denied,
        gumWindow: state.gumCalls.length,
        switchWindow: state.switchCalls.length,
        locked: state.locked,
      };
    },
    unlockGoldenForSession: function (token) {
      // Solo con token simbólico AUTORIZADO (sesión; no persiste)
      if (token === "AUTORIZADO") {
        state.locked = false;
        return true;
      }
      logAttempt("unlockGoldenForSession", "token inválido");
      return false;
    },
  };
})(typeof window !== "undefined" ? window : this);
