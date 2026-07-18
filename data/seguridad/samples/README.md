# Samples SBI-PRO

Coloca aquí tu archivo de voz (WAV PCM 16-bit mono/stereo), por ejemplo:

`israel.wav`

Luego, con el servidor en marcha:

```bash
python api/sbi/setup_env.py
python api/sbi/enroll.py data/seguridad/samples/israel.wav --activar
python api/sbi/verify.py data/seguridad/samples/israel.wav
```

Frase recomendada al grabar (challenge):

> Salomon autentica a Israel
