/**
 * Splash + boot PWA — Salomón AI (fuente public)
 */
(function () {
  const MIN_MS = 600;
  const MAX_BOOT_MS = 6500;
  const PING_MS = 3500;
  const t0 = performance.now();

  function isStandalone() {
    return (
      window.matchMedia("(display-mode: standalone)").matches ||
      window.navigator.standalone === true ||
      document.referrer.includes("android-app://")
    );
  }

  function setStep(msg) {
    const el = document.getElementById("splash-step");
    if (el) el.textContent = msg;
  }

  function setDots(n) {
    const wrap = document.getElementById("splash-dots");
    if (!wrap) return;
    wrap.querySelectorAll("i").forEach((d, i) => {
      d.classList.toggle("on", i < n);
    });
  }

  function hideSplash() {
    const splash = document.getElementById("salomon-splash");
    if (!splash || splash.classList.contains("hide")) return;
    splash.classList.add("hide");
    setTimeout(() => splash.remove(), 480);
    document.documentElement.classList.add("salomon-booted");
  }

  async function ping(path) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), PING_MS);
    try {
      const r = await fetch(path, {
        cache: "no-store",
        signal: ctrl.signal,
        credentials: "same-origin",
      });
      return r.ok;
    } catch {
      return false;
    } finally {
      clearTimeout(t);
    }
  }

  async function boot() {
    document.documentElement.classList.add(
      isStandalone() ? "salomon-standalone" : "salomon-browser"
    );

    const forceTimer = setTimeout(() => {
      setStep("Entrando…");
      hideSplash();
    }, MAX_BOOT_MS);

    try {
      setStep("Conectando con Salomón…");
      setDots(1);
      let salud = await ping("/api/salud");
      setDots(2);
      if (!salud) {
        for (let i = 0; i < 4 && !salud; i++) {
          setStep("Esperando servidor (" + (i + 1) + ")…");
          await new Promise((r) => setTimeout(r, 500));
          salud = await ping("/api/salud");
        }
      }
      setStep(salud ? "Núcleo en línea" : "Modo degradado — entrando…");
      setDots(3);
      ping("/api/cognicion/vdcp/estado");
      ping("/api/tunel/estado");
      setDots(4);
      setStep("Preparando interfaz…");
      await new Promise((r) =>
        setTimeout(r, Math.max(0, MIN_MS - (performance.now() - t0)))
      );
      await new Promise((resolve) => {
        const start = performance.now();
        const tick = () => {
          const root = document.getElementById("root");
          if (
            (root && root.childElementCount > 0) ||
            performance.now() - start > 2500
          ) {
            resolve();
            return;
          }
          requestAnimationFrame(tick);
        };
        tick();
      });
      setDots(5);
      setStep("Listo");
      hideSplash();
      window.dispatchEvent(
        new CustomEvent("salomon:ready", {
          detail: { standalone: isStandalone(), salud, origin: location.origin },
        })
      );
    } finally {
      clearTimeout(forceTimer);
      hideSplash();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
