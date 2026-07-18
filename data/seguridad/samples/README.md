# Samples SBI-PRO

## Opción A — Captura por micrófono

```bash
pip install sounddevice
python api/sbi/capturar.py
```

Lee en voz alta: **Salomon autentica a Israel**

## Opción B — Colocar WAV manualmente

Guarda tu grabación como:

`data/seguridad/samples/israel.wav`

(PCM 16-bit; mono preferido)

## Enrolamiento (sin activar aún)

```bash
python api/sbi/setup_env.py
python api/sbi/enroll.py data/seguridad/samples/israel.wav
```

Solo tras éxito y tu frase:

`APROBADO: Activar SBI_ENABLED=true`

…ejecutamos activación (`SBI_ENABLED=true` local + Render).

**No uses** los MP3 de `data/audio/salomon_*.mp3` (son voz TTS de Salomón, no la tuya).
