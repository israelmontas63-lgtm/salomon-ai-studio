/**
 * Indicador de Progreso Visual — Multimodal Core v70
 * Se muestra si la generación/búsqueda supera 5s (SystemGuard budget).
 * No toca CameraEngine.
 */
(function () {
  "use strict";
  if (window.__SalomonVisualProgress) return;

  var BUDGET_MS = 5000;
  var overlay = null;
  var timer = null;
  var startedAt = 0;
  var phases = [
    "Mejorando prompt HD…",
    "Desplegando motor visual…",
    "Generando / buscando…",
    "Afinando calidad…",
    "Casi listo…",
  ];

  function ensureDom() {
    if (overlay) return overlay;
    overlay = document.createElement("div");
    overlay.id = "salomon-visual-progress";
    overlay.setAttribute("aria-live", "polite");
    overlay.innerHTML =
      '<div class="svp-card">' +
      '<div class="svp-pulse"></div>' +
      '<div class="svp-title">Salomón · Visión</div>' +
      '<div class="svp-msg" id="svp-msg">Preparando…</div>' +
      '<div class="svp-bar"><span id="svp-bar"></span></div>' +
      "</div>";
    var css = document.createElement("style");
    css.textContent =
      "#salomon-visual-progress{position:fixed;inset:auto 0 1.25rem 0;display:none;z-index:99990;pointer-events:none;justify-content:center}" +
      "#salomon-visual-progress.on{display:flex}" +
      "#salomon-visual-progress .svp-card{min-width:min(92vw,320px);padding:0.85rem 1rem;border-radius:14px;background:rgba(10,10,12,.92);border:1px solid rgba(201,169,98,.45);color:#f0f0f0;font-family:system-ui,sans-serif;box-shadow:0 8px 28px rgba(0,0,0,.45)}" +
      "#salomon-visual-progress .svp-title{font-size:0.7rem;letter-spacing:.18em;text-transform:uppercase;color:#c9a962;margin-bottom:0.35rem}" +
      "#salomon-visual-progress .svp-msg{font-size:0.92rem;margin-bottom:0.55rem}" +
      "#salomon-visual-progress .svp-bar{height:3px;background:rgba(255,255,255,.12);border-radius:99px;overflow:hidden}" +
      "#salomon-visual-progress .svp-bar span{display:block;height:100%;width:8%;background:linear-gradient(90deg,#c9a962,#39ff14);animation:svpLoad 1.4s ease-in-out infinite}" +
      "@keyframes svpLoad{0%{width:8%;transform:translateX(0)}50%{width:55%}100%{width:8%;transform:translateX(160%)}}" +
      "@media (prefers-reduced-motion:reduce){#salomon-visual-progress .svp-bar span{animation:none;width:40%}}";
    document.head.appendChild(css);
    document.body.appendChild(overlay);
    return overlay;
  }

  function setMsg(t) {
    ensureDom();
    var el = document.getElementById("svp-msg");
    if (el) el.textContent = t || "";
  }

  function start(label) {
    ensureDom();
    startedAt = Date.now();
    overlay.classList.add("on");
    setMsg(label || phases[0]);
    var i = 0;
    clearInterval(timer);
    timer = setInterval(function () {
      i = Math.min(i + 1, phases.length - 1);
      setMsg(phases[i]);
    }, BUDGET_MS);
  }

  function tickAfterBudget(label) {
    // Solo muestra overlay si ya pasaron 5s
    var wait = Math.max(0, BUDGET_MS - (Date.now() - (startedAt || Date.now())));
    if (!startedAt) startedAt = Date.now();
    setTimeout(function () {
      if (startedAt) start(label || "Procesando visión…");
    }, wait);
  }

  function arm() {
    startedAt = Date.now();
    clearInterval(timer);
    timer = setTimeout(function () {
      start(phases[1]);
    }, BUDGET_MS);
  }

  function stop() {
    clearInterval(timer);
    timer = null;
    startedAt = 0;
    if (overlay) overlay.classList.remove("on");
  }

  window.__SalomonVisualProgress = {
    BUDGET_MS: BUDGET_MS,
    arm: arm,
    start: start,
    tickAfterBudget: tickAfterBudget,
    stop: stop,
    setMsg: setMsg,
  };
})();
