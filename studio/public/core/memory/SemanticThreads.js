/**
 * core/memory/SemanticThreads — hilos semánticos por área (voz/visión/razón).
 */
(function (global) {
  "use strict";
  var KEY = "salomon_core_threads_v1";

  function load() {
    try {
      return JSON.parse(localStorage.getItem(KEY) || "{}") || {};
    } catch (e) {
      return {};
    }
  }

  function save(map) {
    try {
      localStorage.setItem(KEY, JSON.stringify(map));
    } catch (e) {}
  }

  var SemanticThreads = {
    areas: ["voz", "vision", "razonamiento", "memoria", "hilos"],
    bind: function (sessionId, area) {
      var map = load();
      var sid = sessionId || "default";
      map[sid] = map[sid] || { area: "razonamiento", notes: [] };
      if (area) map[sid].area = area;
      map[sid].updated = Date.now();
      save(map);
      return map[sid];
    },
    note: function (sessionId, text, area) {
      var map = load();
      var sid = sessionId || "default";
      map[sid] = map[sid] || { area: area || "razonamiento", notes: [] };
      map[sid].notes.push({ at: Date.now(), text: String(text || "").slice(0, 500), area: area });
      if (map[sid].notes.length > 40) map[sid].notes = map[sid].notes.slice(-40);
      save(map);
    },
    get: function (sessionId) {
      return load()[sessionId || "default"] || null;
    },
  };

  global.SalomonCore = global.SalomonCore || {};
  global.SalomonCore.SemanticThreads = SemanticThreads;
})(typeof window !== "undefined" ? window : globalThis);
