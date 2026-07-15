/**
 * Splash boot — Salomón AI
 * Timeout duro 5s. Sin bucles rAF. Sin recursión.
 * Si no conecta, muestra error y libera la UI.
 */
(function () {
  const CONNECT_MS = 5000;
  const TAG = "[Salomón Boot]";
  let finished = false;

  function setStep(msg) {
    const el = document.getElementById("splash-step");
    if (el) el.textContent = msg;
    console.log(TAG, msg);
  }

  function showError(msg) {
    let box = document.getElementById("salomon-boot-error");
    if (!box) {
      box = document.createElement("div");
      box.id = "salomon-boot-error";
      box.setAttribute("role", "alert");
      box.style.cssText =
        "position:fixed;left:16px;right:16px;bottom:24px;z-index:100001;" +
        "padding:14px 16px;border-radius:12px;background:#2C2C2C;" +
        "border:1px solid #C5A059;color:#FFD700;font:500 14px/1.4 Inter,system-ui,sans-serif;" +
        "box-shadow:0 8px 28px rgba(0,0,0,.45)";
      document.body.appendChild(box);
    }
    box.textContent = msg;
  }

  function hideSplash() {
    if (finished) return;
    finished = true;
    const splash = document.getElementById("salomon-splash");
    if (splash) {
      splash.classList.add("hide");
      setTimeout(function () {
        if (splash.parentNode) splash.remove();
      }, 400);
    }
    document.documentElement.classList.add("salomon-booted");
  }

  function pingSalud() {
    const ctrl = new AbortController();
    const timer = setTimeout(function () {
      ctrl.abort();
    }, CONNECT_MS);
    const url = "/api/salud";
    console.log(TAG, "fetch →", new URL(url, location.origin).href);
    return fetch(url, { cache: "no-store", signal: ctrl.signal })
      .then(function (r) {
        console.log(TAG, "status", r.status, r.ok);
        return r.ok;
      })
      .catch(function (err) {
        console.error(TAG, "error de conexión", err && err.name, err && err.message);
        return false;
      })
      .finally(function () {
        clearTimeout(timer);
      });
  }

  function boot() {
    setStep("Conectando con Salomón…");

    // Timeout absoluto: a los 5s SIEMPRE liberamos el navegador
    const hard = setTimeout(function () {
      console.warn(TAG, "timeout 5s — liberando UI");
      setStep("No se pudo conectar a tiempo");
      showError(
        "Salomón no respondió en 5 segundos. Revisa la conexión o recarga. " +
          "API: " +
          location.origin +
          "/api/salud"
      );
      hideSplash();
    }, CONNECT_MS);

    pingSalud().then(function (ok) {
      clearTimeout(hard);
      if (finished) return;
      if (ok) {
        setStep("Listo");
      } else {
        setStep("Sin conexión al servidor");
        showError(
          "No se pudo conectar con el servidor. Recarga en unos segundos. " +
            location.origin +
            "/api/salud"
        );
      }
      hideSplash();
      try {
        window.dispatchEvent(
          new CustomEvent("salomon:ready", {
            detail: { salud: ok, origin: location.origin },
          })
        );
      } catch (_) {}
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
