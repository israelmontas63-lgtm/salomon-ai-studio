/**
 * Panel multimedia inyectado en dist (sin rebuild completo).
 * Abre con el botón flotante o window.SalomonMedia.open()
 */
(function () {
  const API_KEY = localStorage.getItem("salomon_api_key_ui") || "";
  const SESSION_KEY = "salomon_session_id";

  function headers(json) {
    const h = {};
    if (json) h["Content-Type"] = "application/json";
    const key = API_KEY || (window.__SALOMON_API_KEY__ || "");
    if (key) h["X-API-Key"] = key;
    // Intentar leer meta del build si existe
    const meta = document.querySelector('meta[name="salomon-api-key"]');
    if (meta && meta.content) h["X-API-Key"] = meta.content;
    return h;
  }

  function sessionId() {
    return localStorage.getItem(SESSION_KEY) || null;
  }

  function ensureStyles() {
    if (document.getElementById("salomon-media-css")) return;
    const s = document.createElement("style");
    s.id = "salomon-media-css";
    s.textContent = `
      #salomon-media-fab{position:fixed;right:16px;bottom:96px;z-index:70;width:48px;height:48px;
        border-radius:50%;border:1px solid #c9a962;background:#0c0c0e;color:#c9a962;font-size:20px;cursor:pointer}
      #salomon-media-modal{position:fixed;inset:0;z-index:90;background:rgba(0,0,0,.72);display:none;
        align-items:flex-end;justify-content:center;padding:16px}
      #salomon-media-modal.open{display:flex}
      #salomon-media-modal .box{width:min(440px,100%);background:#0c0c0e;border:1px solid #c9a96266;
        border-radius:16px;padding:14px 16px 18px;color:#f5f5f5;font-family:Inter,system-ui,sans-serif}
      #salomon-media-modal h2{font-family:"Cormorant Garamond",Georgia,serif;color:#c9a962;font-size:1.3rem;margin:0}
      #salomon-media-modal .tabs{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0}
      #salomon-media-modal .tabs button,#salomon-media-modal .actions button{padding:10px;border-radius:10px;border:1px solid #333;background:#16161a;color:#bbb;cursor:pointer}
      #salomon-media-modal .tabs button.on{border-color:#c9a962;color:#c9a962}
      #salomon-media-modal label{display:flex;flex-direction:column;gap:6px;font-size:12px;color:#a8a8a8;margin-bottom:8px}
      #salomon-media-modal input,#salomon-media-modal textarea,#salomon-media-modal select{background:#121214;border:1px solid #333;border-radius:8px;color:#fff;padding:10px;font:inherit}
      #salomon-media-modal .go{width:100%;margin-top:8px;background:#c9a962;color:#111;border:none;border-radius:10px;padding:12px;font-weight:600;cursor:pointer}
      #salomon-media-modal .preview{margin-top:10px;max-width:100%;border-radius:8px;border:1px solid #333}
      #salomon-media-modal .status{font-size:12px;color:#c9a962;min-height:16px;margin-top:8px}
      #salomon-media-modal .head{display:flex;justify-content:space-between;align-items:center}
      #salomon-media-modal .row{display:grid;grid-template-columns:1fr 1fr;gap:8px}
    `;
    document.head.appendChild(s);
  }

  function mount() {
    if (document.getElementById("salomon-media-fab")) return;
    ensureStyles();

    const fab = document.createElement("button");
    fab.id = "salomon-media-fab";
    fab.title = "Multimedia";
    fab.type = "button";
    fab.textContent = "⧉";
    document.body.appendChild(fab);

    const modal = document.createElement("div");
    modal.id = "salomon-media-modal";
    modal.innerHTML = `
      <div class="box">
        <div class="head"><h2>Multimedia Salomón</h2><button type="button" id="sm-close" style="background:none;border:none;color:#c9a962;font-size:22px">×</button></div>
        <div class="tabs">
          <button type="button" class="on" data-tab="img">Generar imagen</button>
          <button type="button" data-tab="vid">Editar video</button>
        </div>
        <div id="sm-img">
          <label>Prompt<textarea id="sm-prompt" rows="4" placeholder="Describe la imagen…"></textarea></label>
          <button class="go" id="sm-gen" type="button">Generar</button>
        </div>
        <div id="sm-vid" style="display:none">
          <label>Archivo de video<input id="sm-file" type="file" accept="video/*"></label>
          <label>Operación
            <select id="sm-op">
              <option value="cortar">Cortar</option>
              <option value="overlay_texto">Superponer texto</option>
              <option value="filtro_bn">Filtro B/N</option>
              <option value="filtro_brillo">Filtro brillo</option>
              <option value="info">Info</option>
            </select>
          </label>
          <div class="row">
            <label>Inicio (s)<input id="sm-ini" value="0"></label>
            <label>Fin (s)<input id="sm-fin" placeholder="fin"></label>
          </div>
          <label>Texto overlay<input id="sm-ov" value="Salomón"></label>
          <button class="go" id="sm-edit" type="button">Subir y editar</button>
        </div>
        <div class="status" id="sm-status"></div>
        <img class="preview" id="sm-preview" alt="" style="display:none"/>
        <video class="preview" id="sm-vprev" controls style="display:none"></video>
      </div>`;
    document.body.appendChild(modal);

    const status = () => document.getElementById("sm-status");
    const setStatus = (t) => {
      status().textContent = t || "";
    };

    fab.onclick = () => modal.classList.add("open");
    document.getElementById("sm-close").onclick = () => modal.classList.remove("open");
    modal.addEventListener("click", (e) => {
      if (e.target === modal) modal.classList.remove("open");
    });

    modal.querySelectorAll(".tabs button").forEach((btn) => {
      btn.onclick = () => {
        modal.querySelectorAll(".tabs button").forEach((b) => b.classList.remove("on"));
        btn.classList.add("on");
        const tab = btn.getAttribute("data-tab");
        document.getElementById("sm-img").style.display = tab === "img" ? "" : "none";
        document.getElementById("sm-vid").style.display = tab === "vid" ? "" : "none";
      };
    });

    async function apiKeyHeader() {
      // Reutilizar clave del frontend embebida si el bundle la tiene en fetch wrappers
      try {
        const salud = await fetch("/api/salud");
        if (salud.ok) return headers(true);
      } catch (_) {}
      return headers(true);
    }

    document.getElementById("sm-gen").onclick = async () => {
      const prompt = document.getElementById("sm-prompt").value.trim();
      if (!prompt) return;
      setStatus("Generando imagen…");
      document.getElementById("sm-preview").style.display = "none";
      try {
        const h = await apiKeyHeader();
        // La app usa X-Api-Key; intentamos sin y con localStorage
        const keys = [h["X-API-Key"], localStorage.getItem("VITE_SALOMON_API_KEY")].filter(Boolean);
        let data = null;
        let lastErr = null;
        for (const attempt of [0, 1]) {
          const hh = { "Content-Type": "application/json" };
          if (keys[0]) hh["X-API-Key"] = keys[0];
          // Leer de cookie/meta no disponible: pedir al usuario una vez si 401
          const res = await fetch("/api/media/route", {
            method: "POST",
            headers: hh,
            body: JSON.stringify({
              prompt,
              hint: "imagen_hd",
              session_id: sessionId(),
            }),
          });
          if (res.status === 401 && attempt === 0) {
            const k = window.prompt("API key Salomón (X-Api-Key):");
            if (k) {
              localStorage.setItem("salomon_api_key_ui", k);
              keys[0] = k;
              continue;
            }
          }
          if (!res.ok) {
            // Fallback al endpoint clásico
            const res2 = await fetch("/api/media/generar_imagen", {
              method: "POST",
              headers: hh,
              body: JSON.stringify({
                prompt,
                session_id: sessionId(),
                usar_routing: true,
              }),
            });
            if (!res2.ok) throw new Error("HTTP " + res2.status);
            data = await res2.json();
            break;
          }
          data = await res.json();
          break;
        }
        if (!data) throw lastErr || new Error("sin datos");
        const motor =
          (data.routing && data.routing.motor) ||
          (data.resultado && data.resultado.motor) ||
          "?";
        const cal =
          (data.routing && data.routing.calidad) ||
          (data.resultado && data.resultado.calidad) ||
          "pro_ultra";
        setStatus(
          data.exito
            ? "Listo · " + motor + " · " + cal
            : data.error || "Falló"
        );
        const b64 = data.resultado && data.resultado.imagen_base64;
        const url = data.resultado && data.resultado.url_relativa;
        const img = document.getElementById("sm-preview");
        document.getElementById("sm-vprev").style.display = "none";
        if (b64) {
          img.src = "data:image/png;base64," + b64;
          img.style.display = "block";
        } else if (url) {
          img.src = url;
          img.style.display = "block";
        }
      } catch (e) {
        setStatus("Error: " + (e.message || e));
      }
    };

    document.getElementById("sm-edit").onclick = async () => {
      const file = document.getElementById("sm-file").files[0];
      if (!file) {
        setStatus("Selecciona un video");
        return;
      }
      setStatus("Procesando video…");
      document.getElementById("sm-vprev").style.display = "none";
      try {
        const fd = new FormData();
        fd.append("archivo", file);
        fd.append("operacion", document.getElementById("sm-op").value);
        fd.append("inicio", document.getElementById("sm-ini").value || "0");
        const fin = document.getElementById("sm-fin").value;
        if (fin) fd.append("fin", fin);
        fd.append("texto_overlay", document.getElementById("sm-ov").value || "");
        fd.append("via_grafo", "true");
        const sid = sessionId();
        if (sid) fd.append("session_id", sid);

        const hh = {};
        const k = localStorage.getItem("salomon_api_key_ui");
        if (k) hh["X-API-Key"] = k;

        let res = await fetch("/api/media/editar_video", { method: "POST", headers: hh, body: fd });
        if (res.status === 401) {
          const nk = window.prompt("API key Salomón (X-Api-Key):");
          if (nk) {
            localStorage.setItem("salomon_api_key_ui", nk);
            hh["X-API-Key"] = nk;
            res = await fetch("/api/media/editar_video", { method: "POST", headers: hh, body: fd });
          }
        }
        if (!res.ok) throw new Error("HTTP " + res.status);
        const data = await res.json();
        setStatus(data.exito ? "Video listo" : data.error || "Falló");
        const url = data.resultado && data.resultado.url_relativa;
        if (url) {
          const v = document.getElementById("sm-vprev");
          document.getElementById("sm-preview").style.display = "none";
          v.src = url;
          v.style.display = "block";
        }
      } catch (e) {
        setStatus("Error: " + (e.message || e));
      }
    };

    window.SalomonMedia = {
      open: () => modal.classList.add("open"),
      close: () => modal.classList.remove("open"),
    };
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
