/**
 * core/memory/HistoryBuffer — buffer de turnos en sesión (cliente).
 */
(function (global) {
  "use strict";
  var KEY = "salomon_core_history_v1";
  var MAX = 60;

  function load() {
    try {
      return JSON.parse(localStorage.getItem(KEY) || "[]") || [];
    } catch (e) {
      return [];
    }
  }

  function save(arr) {
    try {
      localStorage.setItem(KEY, JSON.stringify(arr.slice(-MAX)));
    } catch (e) {}
  }

  var HistoryBuffer = {
    push: function (rol, texto) {
      var arr = load();
      arr.push({ at: Date.now(), rol: rol, texto: String(texto || "").slice(0, 2000) });
      save(arr);
      return arr.length;
    },
    recent: function (n) {
      return load().slice(-(n || 12));
    },
    clear: function () {
      save([]);
    },
    snapshot: function () {
      return load().slice();
    },
  };

  global.SalomonCore = global.SalomonCore || {};
  global.SalomonCore.HistoryBuffer = HistoryBuffer;
})(typeof window !== "undefined" ? window : globalThis);
