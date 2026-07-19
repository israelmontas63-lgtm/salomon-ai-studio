# Kernel `/core` — mapa de reorganización

| Destino | Responsabilidad | Origen encapsulado |
|---------|-----------------|--------------------|
| `core/cortex/` | MainController, LogicEngine | `mente/conexion`, `config/memory_cortex`, `cerebro` |
| `core/peripherals/` | VoiceCore, VisionAgent, HomeGateway | `config/voice_parameters`, `config/vision_integration`, `studio` voz/cámara |
| `core/memory/` | HistoryBuffer, SemanticThreads | `mente/hilos`, `cognicion/memoria` |

Los paths históricos (`cerebro.py`, `mente/`, `cognicion/`) **siguen vivos** como implementación; `/core` es el hard-link de kernel que Israel ordenó. No se rompe SystemGuard moviendo `app.py` ni `camera-engine.js`.

## Orden de carga en `index.html` (obligatorio)

1. `/core/config.js`
2. `/boot/permissions_check.js`
3. `/core/core.js` (HistoryBuffer + SemanticThreads + LogicEngine + MainController)
4. `/core/peripherals/VoiceCore.js` + `VisionAgent.js`
5. `/core/peripherals/HomeGateway.js`
6. `/core/main.js` → permisos → `MainController.init()` → `VoiceCore.enableNoiseGate()` si mic OK

## Level 9 — Plug-and-Play (`plugins/`)

Habilidad 30-X #9: instalar periféricas sin apagar el núcleo.

| Plugin | Capa | Rol |
|--------|------|-----|
| `function_calling` | nucleo | Herramientas LLM |
| `voice_core` | periferica | Noise gate / audio port |
| `vision_agent` | periferica | Cámara / visión |
| `home_gateway` | periferica | Rutas canónicas |
| `audio_stack` | periferica | Deepgram + ElevenLabs |
| `media_stack` | periferica | Fal → Replicate |
| `reconexion_perifericos` | periferica | Reconexión emergencia |

API: `GET /api/level9` · `POST /api/level9/hot-plug` · `POST /api/level9/rescan`

## Carpetas anti-huérfanos (JS)

| Carpeta | Contenido |
|---------|-----------|
| `studio/dist/core/` | kernel |
| `studio/dist/boot/` | permissions, PWA, heal, update |
| `studio/dist/ui/` | drawers, overlays, indicadores |
| `studio/dist/` (raíz) | solo CRITICAL: camera-engine, camera-v13, security-kernel, SW |
