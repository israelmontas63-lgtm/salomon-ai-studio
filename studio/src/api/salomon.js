/**
 * Cliente API Salomón — rutas relativas para producción (Render).
 * No usar localhost: el mismo origen sirve UI + API.
 */
const API_BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

function headers(extra = {}) {
  const h = { "Content-Type": "application/json", ...extra };
  const key = import.meta.env.VITE_SALOMON_API_KEY || "";
  if (key) h["X-Api-Key"] = key;
  return h;
}

async function api(path, options = {}) {
  const url = `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
  console.log("[Salomón API] fetch →", url, options.method || "GET");
  const res = await fetch(url, {
    ...options,
    headers: { ...headers(), ...(options.headers || {}) },
  });
  if (!res.ok) {
    const err = new Error(`HTTP ${res.status}`);
    err.status = res.status;
    try {
      err.body = await res.json();
    } catch {
      err.body = null;
    }
    console.error("[Salomón API] error", url, err.status, err.body);
    throw err;
  }
  const data = await res.json();
  console.log("[Salomón API] ok", url, data && typeof data === "object" ? Object.keys(data) : typeof data);
  return data;
}

export function checkSalud(fetchOpts = {}) {
  return api("/api/salud", fetchOpts);
}

export function iniciarSesion(sessionId, fetchOpts = {}) {
  return api("/api/sesion", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId || null }),
    ...fetchOpts,
  });
}

export function obtenerHistorial(sessionId, fetchOpts = {}) {
  return api(`/api/sesion/${encodeURIComponent(sessionId)}/mensajes`, fetchOpts);
}

export function enviarMensaje(mensaje, sessionId, meta = {}, fetchOpts = {}) {
  return api("/api/chat", {
    method: "POST",
    body: JSON.stringify({
      mensaje,
      session_id: sessionId || null,
      ...meta,
    }),
    ...fetchOpts,
  });
}

export function sintetizarVoz(texto, sessionId, fetchOpts = {}) {
  return api("/api/tts", {
    method: "POST",
    body: JSON.stringify({ texto, session_id: sessionId || null }),
    ...fetchOpts,
  });
}

async function herramienta(path, body = {}) {
  return api(path, { method: "POST", body: JSON.stringify(body) });
}

export const herramientaAyuda = () => api("/api/herramientas/ayuda");
export const herramientaAnaliticas = () => api("/api/herramientas/analiticas");
export const herramientaPlanes = (body) => herramienta("/api/herramientas/planes", body);
export const herramientaSolar = (body) => herramienta("/api/herramientas/solar", body);
export const herramientaOptimizar = (body) => herramienta("/api/herramientas/optimizar", body);
export const herramientaSeguridad = (body) => herramienta("/api/herramientas/seguridad", body);
export const herramientaCorregir = (body) => herramienta("/api/herramientas/corregir", body);
export const herramientaTraducir = (body) => herramienta("/api/herramientas/traducir", body);
export const herramientaCli = (body) => herramienta("/api/herramientas/cli", body);
export const herramientaBackupExport = (body) =>
  herramienta("/api/herramientas/backup/export", body);
