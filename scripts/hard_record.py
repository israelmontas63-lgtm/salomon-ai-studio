import sounddevice as sd
import scipy.io.wavfile as wav
from pathlib import Path

OUT = Path("security/credentials/voice_signature.wav")
OUT.parent.mkdir(parents=True, exist_ok=True)
print("--- INICIANDO GRABACION EN 3 SEGUNDOS ---")
fs = 44100
record = sd.rec(int(5 * fs), samplerate=fs, channels=1)
sd.wait()
wav.write(str(OUT), fs, record)
print(f"--- GRABACION FINALIZADA Y GUARDADA EN {OUT.as_posix()} ---")
