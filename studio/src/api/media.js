const API_BASE = import.meta.env.VITE_API_URL || "";
const API_KEY = import.meta.env.VITE_SALOMON_API_KEY || "";

function headers(extra = {}) {
  const h = { ...extra };
  if (API_KEY) h["X-API-Key"] = API_KEY;
  return h;
}

export async function estadoMedia() {
  const res = await fetch(`${API_BASE}/api/media/estado`, {
    headers: headers(),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export async function generarImagen(prompt, opts = {}) {
  const res = await fetch(`${API_BASE}/api/media/generar_imagen`, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      prompt,
      session_id: opts.sessionId || null,
      size: opts.size || "1024x1024",
      quality: opts.quality || "standard",
      via_grafo: opts.viaGrafo !== false,
    }),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export async function editarVideo(file, opts = {}) {
  const fd = new FormData();
  fd.append("archivo", file);
  fd.append("operacion", opts.operacion || "cortar");
  fd.append("inicio", String(opts.inicio ?? 0));
  if (opts.fin != null && opts.fin !== "") fd.append("fin", String(opts.fin));
  fd.append("texto_overlay", opts.textoOverlay || "");
  fd.append("brillo", String(opts.brillo ?? 1.2));
  if (opts.sessionId) fd.append("session_id", opts.sessionId);
  fd.append("via_grafo", String(opts.viaGrafo !== false));

  const res = await fetch(`${API_BASE}/api/media/editar_video`, {
    method: "POST",
    headers: headers(),
    body: fd,
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}
