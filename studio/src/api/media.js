/** Cliente media — rutas relativas (mismo origen en Render). */
const API_BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

function headers(json = true) {
  const h = {};
  if (json) h["Content-Type"] = "application/json";
  const key = import.meta.env.VITE_SALOMON_API_KEY || "";
  if (key) h["X-Api-Key"] = key;
  return h;
}

export async function estadoMedia() {
  const res = await fetch(`${API_BASE}/api/media/estado`, { headers: headers(false) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function generarImagen(payload, fetchOpts = {}) {
  const res = await fetch(`${API_BASE}/api/media/generar_imagen`, {
    method: "POST",
    headers: headers(true),
    body: JSON.stringify(payload),
    ...fetchOpts,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function editarVideo(formData) {
  const res = await fetch(`${API_BASE}/api/media/editar_video`, {
    method: "POST",
    headers: headers(false),
    body: formData,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
