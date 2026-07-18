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

## Carpetas anti-huérfanos (JS)

| Carpeta | Contenido |
|---------|-----------|
| `studio/dist/core/` | kernel |
| `studio/dist/boot/` | permissions, PWA, heal, update |
| `studio/dist/ui/` | drawers, overlays, indicadores |
| `studio/dist/` (raíz) | solo CRITICAL: camera-engine, camera-v13, security-kernel, SW |
