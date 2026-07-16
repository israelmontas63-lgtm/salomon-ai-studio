# Log de Auditoría — Despliegue Salomón AI (Neural Sync)

**Fecha:** 2026-07-16  
**Auditor:** Arquitecto / Security review (pre-Render)  
**Estado:** LISTO PARA VISTO BUENO (sin push ejecutado)

## 1. Variables de voz

| Check | Resultado |
|-------|-----------|
| ¿Existe `config.js`? | No. Gestor real: `settings.py` |
| `ELEVENLABS_API_KEY` | `os.getenv("ELEVENLABS_API_KEY")` — sin valor estático en código |
| Uso en TTS | `cerebro.py` → header `xi-api-key` desde settings |
| Hardcode en dist/public JS | No encontrado |
| `render.yaml` | Declara `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` (`sync: false`) + `TTS_ASYNC=false` |
| Secreto en git | `.env` gitignored — no incluir en commit |

**Acción Render (manual):** confirmar valores reales de `ELEVENLABS_API_KEY` y `ELEVENLABS_VOICE_ID` en el Dashboard antes/después del deploy.

## 2. Integración neuronal (visión)

| Check | Resultado |
|-------|-----------|
| Overlay táctil ULL | `salomon-ui-shield.js`: `touchstart` + `capture:true` |
| Hub visión | `vision-overlay.js` escucha `salomon:ui-photo` (capture phase) |
| Orden de carga | bridge → **shield** → vision (evita race) |
| Conflicto `main.js` | No hay `main.js`; bundle estable `index-BdcDx9nN.js` |
| Voz UI | `salomon-orchestrator-bridge.js` `ensureVoiceOut` / `/api/tts` intacto |

## 3. Consistencia caché PWA

| Artefacto | Versión |
|-----------|---------|
| `index.html` CSS shield | `?v=sync1` |
| `salomon-ui-shield.js` | `?v=sync1` |
| `vision-overlay.js` | `?v=sync1` |
| Registro SW | `/sw.js?v=7` |
| `CACHE` en `sw.js` | `salomon-v10-neural-sync` |
| dist ≡ public | Verificado (index/sw/vision) |

SW bypasa red para: `/api/*`, `index.html`, shield, vision, bridge (sin bloquear touch/cámara).

## 4. Archivos a incluir en el commit (tras OK)

1. `studio/dist/index.html`
2. `studio/dist/salomon-ui-shield.css`
3. `studio/dist/salomon-ui-shield.js`
4. `studio/dist/sw.js`
5. `studio/dist/vision-overlay.js`
6. `studio/public/index.html`
7. `studio/public/salomon-ui-shield.css`
8. `studio/public/salomon-ui-shield.js`
9. `studio/public/sw.js`
10. `studio/public/vision-overlay.js`
11. `render.yaml`
12. `docs/AUDIT_DEPLOY_NEURAL_SYNC.md` (este log)

## 5. Excluir del commit

- `data/memoria_personal.json`
- `_integrity_backup_dist/`
- `node_modules/`
- `index.html` (raíz suelta)
- Cualquier `.env` / secretos

## 6. Mensaje de commit sugerido

`Salomón AI: Integración neuronal de visión y lógica unificada de cámara`

## 7. Veredicto

**GO condicionado:** código y caché alineados; voz depende de env en Render (no del repo).  
**No push** hasta visto bueno explícito del operador.
