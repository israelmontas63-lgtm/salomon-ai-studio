# Protocolo CI/CD — Salomón AI ↔ Render

## Flujo

1. Push a `main` en GitHub → Render despliega automáticamente.
2. La app consulta `/api/version` (usa `RENDER_GIT_COMMIT`).
3. Si el build cambió → limpia caches del Service Worker → recarga dura.
4. Icono `↻` (esquina superior derecha) fuerza la misma actualización manualmente.

## Voz tras actualizar

- `ELEVENLABS_API_KEY` / `ELEVENLABS_VOICE_ID` viven solo en el Dashboard de Render.
- `/api/*` nunca se cachea en el SW.
- Un reload no borra esas variables ni `localStorage` de sesión.

## Validación local

```bash
python scripts/validate_render_env.py
```

## API

- `GET /api/version` — build corto/completo + `tts_configurado` (bool).
- `GET /api/salud` — incluye `build`.
