/**
 * core/config.js — variables globales del kernel (sin secretos en cliente).
 */
(function (global) {
  "use strict";
  global.SalomonConfig = {
    version: "109.1.0",
    owner: "Israel Monta",
    apiBase: "",
    endpoints: {
      chat: "/api/chat",
      nuevo: "/api/chat/nuevo",
      mente: "/api/mente/conexion",
      kernel: "/api/core/kernel",
      tts: "/api/tts",
      salud: "/api/salud",
    },
    voice: {
      bandHz: [300, 3400],
      sensitivity: 0.8,
      lang: "es-ES",
      noiseGate: true,
    },
    vision: { enabled: true, inInputFlow: true },
    cortex: {
      webOnlyIf: "Busca en la web sobre…",
      externalLocked: true,
    },
    permissions: ["microphone", "camera"],
  };
  global.SalomonCore = global.SalomonCore || {};
  console.info("[config] SalomonConfig listo");
})(typeof window !== "undefined" ? window : globalThis);
