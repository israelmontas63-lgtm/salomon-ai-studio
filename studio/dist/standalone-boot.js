/**
 * Splash + boot PWA — Salomón AI
 * Rutas relativas (/api/...). Logs en consola para diagnosticar conexión.
 */
(function () {
  const MIN_MS = 600;
  const MAX_BOOT_MS = 6500;
  const PING_MS = 4000;
  const t0 = performance.now();
  const TAG = "[Salomón Boot]";

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
    console.log(TAG, "paso:", msg);
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
    console.log(TAG, "splash oculto");
  }

  async function ping(path) {
    const url = path; // relativa — nunca localhost
    const absolute = new URL(path, window.location.origin).href;
    console.log(TAG, "fetch →", absolute);

    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), PING_MS);
    try {
      const r = await fetch(url, {
        cache: "no-store",
        signal: ctrl.signal,
        credentials: "same-origin",
      });
      let bodyPreview = "";
      try {
        bodyPreview = (await r.clone().text()).slice(0, 180);
      } catch (_) {}
      console.log(TAG, "respuesta", {
        url: absolute,
        status: r.status,
        ok: r.ok,
        body: bodyPreview,
      });
      if (!r.ok) {
        console.error(TAG, "error HTTP", r.status, bodyPreview || r.statusText);
      }
      return r.ok;
    } catch (err) {
      console.error(TAG, "fallo de conexión", {
        url: absolute,
        name: err && err.name,
        message: err && err.message,
        error: err,
      });
      return false;
    } finally {
      clearTimeout(t);
    }
  }

  async function boot() {
    console.log(TAG, "inicio", {
      origin: window.location.origin,
      href: window.location.href,
      standalone: isStandalone(),
      online: navigator.onLine,
    });

    document.documentElement.classList.add(
      isStandalone() ? "salomon-standalone" : "salomon-browser"
    );

    const forceTimer = setTimeout(() => {
      console.warn(TAG, "timeout global — forzando entrada a la UI");
      setStep("Entrando…");
      hideSplash();
    }, MAX_BOOT_MS);

    try {
      setStep("Conectando con Salomón…");
      setDots(1);

      let salud = await ping("/api/salud");
      setDots(2);

      if (!salud) {
        setStep("Reintentando servidor…");
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

      const waitUi = Math.max(0, MIN_MS - (performance.now() - t0));
      await new Promise((r) => setTimeout(r, waitUi));

      await new Promise((resolve) => {
        const start = performance.now();
        const tick = () => {
          const root = document.getElementById("root");
          if (
            (root && root.childElementCount > 0) ||
            performance.now() - start > 2500
          ) {
            console.log(TAG, "UI root", {
              children: root ? root.childElementCount : 0,
            });
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
          detail: {
            standalone: isStandalone(),
            salud,
            origin: window.location.origin,
          },
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
