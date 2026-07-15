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
    throw err;
  }
  return res.json();
}

export function checkSalud() {
  return api("/api/salud");
}

export function iniciarSesion(sessionId) {
  return api("/api/sesion", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId || null }),
  });
}

export function obtenerHistorial(sessionId) {
  return api(`/api/sesion/${encodeURIComponent(sessionId)}/mensajes`);
}

export function enviarMensaje(mensaje, sessionId, meta = {}) {
  return api("/api/chat", {
    method: "POST",
    body: JSON.stringify({
      mensaje,
      session_id: sessionId || null,
      ...meta,
    }),
  });
}

export function sintetizarVoz(texto, sessionId) {
  return api("/api/tts", {
    method: "POST",
    body: JSON.stringify({ texto, session_id: sessionId || null }),
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
