/**
 * Visión Standalone — cámara + puntos de seguimiento + captura VDCP
 */
(function () {
  const SESSION_KEY = "salomon_session_id";

  function apiKey() {
    return (
      localStorage.getItem("salomon_api_key_ui") ||
      window.__SALOMON_API_KEY__ ||
      ""
    );
  }

  function headers(json) {
    const h = {};
    if (json) h["Content-Type"] = "application/json";
    const k = apiKey();
    if (k) h["X-API-Key"] = k;
    return h;
  }

  function ensureUi() {
    if (document.getElementById("vision-hud")) return;

    const style = document.createElement("style");
    style.id = "vision-overlay-css";
    style.textContent = `
/* FAB lateral izquierdo eliminado — visión solo vía SalomonVision.open() / cámara */
#vision-fab{display:none!important}
#vision-hud{display:none;position:fixed;inset:0;z-index:95;background:#0a0a0a;flex-direction:column}
#vision-hud.open{display:flex}
#vision-stage{position:relative;flex:1;min-height:0;background:#000}
#vision-video{width:100%;height:100%;object-fit:cover}
#vision-canvas{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
#vision-bar{display:flex;gap:10px;padding:12px 14px calc(14px + env(safe-area-inset-bottom,0px));
  background:linear-gradient(transparent,#1A1A1A);border-top:1px solid rgba(212,175,55,.3)}
#vision-bar button{flex:1;padding:12px;border-radius:12px;border:1px solid rgba(212,175,55,.45);
  background:#2C2C2C;color:#FFD700;font:600 13px/1 Inter,system-ui,sans-serif;cursor:pointer}
#vision-bar button.primary{background:linear-gradient(145deg,#FFD700,#D4AF37);color:#1A1A1A;border:none}
#vision-status{position:absolute;top:12px;left:12px;right:12px;z-index:2;padding:8px 12px;
  border-radius:10px;background:rgba(26,26,26,.78);border:1px solid rgba(212,175,55,.35);
  color:#E8C547;font:500 12px/1.3 Inter,system-ui,sans-serif}
#vision-result{max-height:28vh;overflow:auto;padding:10px 14px;color:#ddd;font:12px/1.4 Inter,system-ui,sans-serif;
  background:#1A1A1A;border-top:1px solid rgba(212,175,55,.2);display:none}
#vision-result.open{display:block}
.vision-dot{position:absolute;width:10px;height:10px;margin:-5px 0 0 -5px;border-radius:50%;
  background:#FFD700;box-shadow:0 0 10px rgba(255,215,0,.8);animation:vPulse 1.2s ease-in-out infinite}
@keyframes vPulse{0%,100%{transform:scale(1);opacity:.85}50%{transform:scale(1.35);opacity:1}}
`;
    document.head.appendChild(style);

    // Botón circular lateral (◉) eliminado permanentemente de la UI.
    const staleFab = document.getElementById("vision-fab");
    if (staleFab) staleFab.remove();

    const hud = document.createElement("div");
    hud.id = "vision-hud";
    hud.innerHTML = `
      <div id="vision-stage">
        <div id="vision-status">Visión lista — toca Capturar</div>
        <video id="vision-video" playsinline muted autoplay></video>
        <canvas id="vision-canvas"></canvas>
      </div>
      <div id="vision-result"></div>
      <div id="vision-bar">
        <button type="button" id="vision-close">Cerrar</button>
        <button type="button" id="vision-capture" class="primary">Capturar + VDCP</button>
      </div>
    `;
    document.body.appendChild(hud);

    let stream = null;
    let anim = 0;
    const video = () => document.getElementById("vision-video");
    const canvas = () => document.getElementById("vision-canvas");
    const status = (t) => {
      const el = document.getElementById("vision-status");
      if (el) el.textContent = t;
    };

    function drawPoints() {
      const v = video();
      const c = canvas();
      if (!v || !c || v.readyState < 2) {
        anim = requestAnimationFrame(drawPoints);
        return;
      }
      const w = c.clientWidth || v.clientWidth;
      const h = c.clientHeight || v.clientHeight;
      if (c.width !== w || c.height !== h) {
        c.width = w;
        c.height = h;
      }
      const ctx = c.getContext("2d");
      ctx.clearRect(0, 0, w, h);
      // Cruz central (fóvea) + puntos de seguimiento
      const cx = w * 0.5;
      const cy = h * 0.45;
      const pts = [
        [cx, cy],
        [w * 0.28, h * 0.32],
        [w * 0.72, h * 0.3],
        [w * 0.35, h * 0.68],
        [w * 0.66, h * 0.7],
        [w * 0.5, h * 0.18],
      ];
      const t = Date.now() / 1000;
      pts.forEach(([x, y], i) => {
        const ox = x + Math.sin(t * 1.4 + i) * 3;
        const oy = y + Math.cos(t * 1.1 + i) * 3;
        ctx.beginPath();
        ctx.arc(ox, oy, 5, 0, Math.PI * 2);
        ctx.fillStyle = i === 0 ? "#FFD700" : "rgba(212,175,55,0.85)";
        ctx.fill();
        ctx.strokeStyle = "rgba(255,215,0,0.35)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(ox, oy, 14 + (i === 0 ? 6 : 0), 0, Math.PI * 2);
        ctx.stroke();
      });
      // marco foveal
      ctx.strokeStyle = "rgba(212,175,55,0.5)";
      ctx.lineWidth = 1.5;
      const fw = w * 0.34;
      const fh = h * 0.22;
      ctx.strokeRect(cx - fw / 2, cy - fh / 2, fw, fh);
      anim = requestAnimationFrame(drawPoints);
    }

    async function openHud() {
      hud.classList.add("open");
      status("Activando cámara…");
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" } },
          audio: false,
        });
        const v = video();
        v.srcObject = stream;
        await v.play();
        status("Gran angular activo · puntos de seguimiento VDCP");
        cancelAnimationFrame(anim);
        drawPoints();
      } catch (e) {
        status("Sin cámara: " + (e.message || e) + " — puedes cerrar y reintentar");
      }
    }

    function closeHud() {
      hud.classList.remove("open");
      cancelAnimationFrame(anim);
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
        stream = null;
      }
      const v = video();
      if (v) v.srcObject = null;
    }

    async function capturarVdcp() {
      const v = video();
      if (!v || v.readyState < 2) {
        status("Espera a que la cámara cargue");
        return;
      }
      status("Foveando y leyendo…");
      const off = document.createElement("canvas");
      off.width = v.videoWidth || 1280;
      off.height = v.videoHeight || 720;
      off.getContext("2d").drawImage(v, 0, 0, off.width, off.height);
      const dataUrl = off.toDataURL("image/jpeg", 0.86);
      const b64 = dataUrl.split(",")[1];
      try {
        let key = apiKey();
        if (!key) {
          key = window.prompt("API key Salomón (X-Api-Key):") || "";
          if (key) localStorage.setItem("salomon_api_key_ui", key);
        }
        const res = await fetch("/api/cognicion/vdcp", {
          method: "POST",
          headers: headers(true),
          body: JSON.stringify({
            imagen_base64: b64,
            max_foveas: 8,
            session_id: localStorage.getItem(SESSION_KEY),
          }),
        });
        if (res.status === 401) {
          status("API key requerida — guárdala e intenta de nuevo");
          return;
        }
        const data = await res.json();
        const box = document.getElementById("vision-result");
        box.classList.add("open");
        box.textContent =
          data.narrativa_consolidada ||
          (data.textos || []).join(" / ") ||
          data.error ||
          "Sin lectura";
        status(
          data.exito
            ? "VDCP listo · " + (data.hallazgos || []).length + " fóveas"
            : "VDCP con avisos"
        );
      } catch (e) {
        status("Error VDCP: " + (e.message || e));
      }
    }

    document.getElementById("vision-close").onclick = () => closeHud();
    document.getElementById("vision-capture").onclick = () => capturarVdcp();

    window.SalomonVision = { open: openHud, close: closeHud };
  }

  function start() {
    ensureUi();
  }

  window.addEventListener("salomon:ready", start);
  if (document.readyState === "complete") {
    setTimeout(start, 200);
  } else {
    window.addEventListener("load", () => setTimeout(start, 200));
  }
})();
