# Capa 2: Memoria persistente e historial de chats

Fuente de verdad: SQLite (`persistencia/sesiones.py`) con `journal_mode=WAL`,
`busy_timeout` y transacciones `BEGIN IMMEDIATE`.

Controlador de capa: `cognicion/capas_inteligencia/layer_02_memory/__init__.py`

- `save_message` / `load_messages` / `load_recent` — API tipada (`session_id: str | None`)
- Caché RAM por sesión (anti cross-chat) si SQLite falla o hay latencia
- `seal_boundaries()` / `layer_two_status()` — contratos de aislamiento

No controla cámara, TTS ni enjambres L3/L6.
