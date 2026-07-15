/**
 * Splash + boot Standalone — Salomón PWA
 * Mantiene pantalla de carga negro-dorado hasta salud + visión + UI.
 */
(function () {
  const MIN_MS = 900;
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

  async function ping(url) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 5000);
    try {
      const r = await fetch(url, { cache: "no-store", signal: ctrl.signal });
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

    setStep("Conectando con Salomón…");
    setDots(1);

    const salud = await ping("/api/salud");
    setDots(2);
    setStep(salud ? "Núcleo en línea" : "Reintentando servidor…");

    if (!salud) {
      // reintentos cortos (túnel / BCA reiniciando)
      for (let i = 0; i < 8 && !(await ping("/api/salud")); i++) {
        setStep("Esperando servidor (" + (i + 1) + ")…");
        await new Promise((r) => setTimeout(r, 700));
      }
    }

    setDots(3);
    setStep("Inicializando visión VDCP…");
    await ping("/api/cognicion/vdcp/estado");
    await ping("/api/tunel/estado");

    setDots(4);
    setStep("Preparando interfaz…");

    // Esperar a que React monte #root con contenido
    await new Promise((resolve) => {
      const start = performance.now();
      const tick = () => {
        const root = document.getElementById("root");
        const ready =
          root && root.childElementCount > 0 && performance.now() - t0 >= MIN_MS;
        if (ready || performance.now() - start > 8000) {
          resolve();
          return;
        }
        requestAnimationFrame(tick);
      };
      tick();
    });

    setDots(5);
    setStep("Listo");

    const splash = document.getElementById("salomon-splash");
    if (splash) {
      splash.classList.add("hide");
      setTimeout(() => splash.remove(), 480);
    }

    document.documentElement.classList.add("salomon-booted");
    window.dispatchEvent(
      new CustomEvent("salomon:ready", {
        detail: { standalone: isStandalone(), salud },
      })
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
