# Identidad visual oficial — Salomón AI (integración segura)

**Master:** `sa-official-1024.png`

## Arquitectura detectada

- Backend: FastAPI (`app.py`)
- Frontend servido: `studio/dist` (PWA)
- UI: React + Vite (no regenerar `vite build` a ciegas: el layout estable está en dist)
- Sin Capacitor / Electron / Tauri activos en el repo

## Modo seguro

1. Genera packs en `brand/icons/` (Android, iOS, Windows, macOS, Linux, PWA).
2. Actualiza **píxeles** en `studio/dist` y `studio/public`.
3. Conserva rutas existentes (`/icon-*-v2.png`, `/favicon-v2.ico`, etc.).
4. No modifica APIs, lógica, ni CSS de layout (`index-CJUgt2ya.css`).

```bash
python scripts/generate_official_icons.py
```

El único cambio de runtime permitido para refrescar caché PWA: nombre de caché en `sw.js` (`salomon-v7-icon-official`).
