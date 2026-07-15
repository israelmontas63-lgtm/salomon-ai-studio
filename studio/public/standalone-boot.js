/**
 * Splash boot — Salomón AI
 * try/catch + timeout 5s + botón "Reintentar Conexión" (sin recargar la página).
 */
(function () {
  const CONNECT_MS = 5000;
  const TAG = "[Salomón Boot]";
  const BOOT_SRC = "/standalone-boot.js?v=7";
  let finished = false;
  let hardTimer = null;

  function setStep(msg) {
    const el = document.getElementById("splash-step");
    if (el) el.textContent = msg;
    console.log(TAG, msg);
  }

  function ensureRetryUi(msg) {
    let box = document.getElementById("salomon-boot-error");
    if (!box) {
      box = document.createElement("div");
      box.id = "salomon-boot-error";
      box.setAttribute("role", "alert");
      box.style.cssText =
        "position:fixed;left:16px;right:16px;bottom:24px;z-index:100001;" +
        "padding:14px 16px;border-radius:12px;background:#2C2C2C;" +
        "border:1px solid #C5A059;color:#FFD700;font:500 14px/1.4 Inter,system-ui,sans-serif;" +
        "box-shadow:0 8px 28px rgba(0,0,0,.45);display:flex;flex-direction:column;gap:10px";
      document.body.appendChild(box);
    }

    box.innerHTML = "";
    const text = document.createElement("div");
    text.textContent = msg;
    box.appendChild(text);

    const btn = document.createElement("button");
    btn.type = "button";
    btn.id = "salomon-retry-btn";
    btn.textContent = "Reintentar Conexión";
    btn.style.cssText =
      "align-self:flex-start;padding:10px 14px;border-radius:10px;border:none;" +
      "background:linear-gradient(145deg,#FFD700,#C5A059);color:#1A1A1A;" +
      "font:600 13px/1 Inter,system-ui,sans-serif;cursor:pointer";
    btn.addEventListener("click", function () {
      console.log(TAG, "reintento manual — reiniciando boot sin recargar página");
      btn.disabled = true;
      btn.textContent = "Reintentando…";
      reloadBootScriptOnly();
    });
    box.appendChild(btn);
  }

  function clearRetryUi() {
    const box = document.getElementById("salomon-boot-error");
    if (box) box.remove();
  }

  function hideSplash() {
    const splash = document.getElementById("salomon-splash");
    if (splash && !splash.classList.contains("hide")) {
      splash.classList.add("hide");
      setTimeout(function () {
        if (splash.parentNode) splash.remove();
      }, 400);
    }
    document.documentElement.classList.add("salomon-booted");
  }

  function showSplashAgain() {
    finished = false;
    clearRetryUi();
    let splash = document.getElementById("salomon-splash");
    if (!splash) {
      splash = document.createElement("div");
      splash.id = "salomon-splash";
      splash.setAttribute("aria-live", "polite");
      splash.innerHTML =
        '<div class="splash-icon" role="img" aria-label="Salomón"></div>' +
        '<div class="splash-title">SALOMÓN</div>' +
        '<div id="splash-dots" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div>' +
        '<div class="splash-step" id="splash-step">Reintentando…</div>';
      document.body.appendChild(splash);
    } else {
      splash.classList.remove("hide");
    }
    document.documentElement.classList.remove("salomon-booted");
  }

  /** Recarga solo el script de boot (sin location.reload). */
  function reloadBootScriptOnly() {
    try {
      if (hardTimer) clearTimeout(hardTimer);
      showSplashAgain();
      setStep("Reintentando conexión…");
      document.querySelectorAll('script[data-salomon-boot="1"]').forEach(function (s) {
        s.remove();
      });
      const s = document.createElement("script");
      s.src = BOOT_SRC + "&t=" + Date.now();
      s.async = true;
      s.dataset.salomonBoot = "1";
      s.onerror = function () {
        console.error(TAG, "no se pudo recargar standalone-boot.js");
        // Fallback: reintentar connect en memoria
        finished = false;
        connect();
      };
      document.head.appendChild(s);
    } catch (err) {
      console.error(TAG, "reloadBootScriptOnly falló", err);
      finished = false;
      connect();
    }
  }

  async function pingSalud() {
    const ctrl = new AbortController();
    const timer = setTimeout(function () {
      ctrl.abort();
    }, CONNECT_MS);
    try {
      const absolute = new URL("/api/salud", location.origin).href;
      console.log(TAG, "fetch →", absolute);
      const r = await fetch("/api/salud", {
        cache: "no-store",
        signal: ctrl.signal,
        credentials: "same-origin",
      });
      console.log(TAG, "status", r.status, r.ok);
      return r.ok;
    } catch (err) {
      console.error(TAG, "error de conexión", err && err.name, err && err.message);
      throw err;
    } finally {
      clearTimeout(timer);
    }
  }

  async function connect() {
    if (hardTimer) clearTimeout(hardTimer);
    finished = false;
    clearRetryUi();
    setStep("Conectando con Salomón…");

    hardTimer = setTimeout(function () {
      if (finished) return;
      finished = true;
      console.warn(TAG, "timeout 5s");
      setStep("No se pudo conectar a tiempo");
      ensureRetryUi(
        "Salomón no respondió en 5 segundos. Puedes reintentar sin recargar la página."
      );
      hideSplash();
    }, CONNECT_MS);

    try {
      const ok = await pingSalud();
      if (finished) return;
      finished = true;
      clearTimeout(hardTimer);

      if (ok) {
        setStep("Listo");
        clearRetryUi();
        hideSplash();
        window.dispatchEvent(
          new CustomEvent("salomon:ready", {
            detail: { salud: true, origin: location.origin },
          })
        );
      } else {
        setStep("Sin conexión al servidor");
        ensureRetryUi(
          "El servidor respondió con error. Pulsa Reintentar Conexión cuando esté listo."
        );
        hideSplash();
      }
    } catch (err) {
      if (finished) return;
      finished = true;
      clearTimeout(hardTimer);
      console.error(TAG, "fallo en connect()", err);
      setStep("Error de conexión");
      ensureRetryUi(
        "Fallo de red: " +
          (err && err.name === "AbortError"
            ? "tiempo de espera agotado"
            : err && err.message
              ? err.message
              : "desconocido") +
          ". Pulsa Reintentar Conexión."
      );
      hideSplash();
    }
  }

  window.__salomonRetryBoot = reloadBootScriptOnly;

  try {
    if (document.readyState === "loading") {
      document.addEventListener(
        "DOMContentLoaded",
        function () {
          connect().catch(function (e) {
            console.error(TAG, "connect no controlado", e);
            ensureRetryUi("Error inesperado al iniciar. Pulsa Reintentar Conexión.");
            hideSplash();
          });
        },
        { once: true }
      );
    } else {
      connect().catch(function (e) {
        console.error(TAG, "connect no controlado", e);
        ensureRetryUi("Error inesperado al iniciar. Pulsa Reintentar Conexión.");
        hideSplash();
      });
    }
  } catch (err) {
    console.error(TAG, "error fatal al registrar boot", err);
    try {
      ensureRetryUi("No se pudo iniciar el boot. Pulsa Reintentar Conexión.");
      hideSplash();
    } catch (_) {}
  }
})();
