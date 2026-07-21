"""Script de demostración del agente autónomo."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app import app

PRUEBA = ROOT / "scripts" / "prueba_agente.py"

ERROR = """Traceback (most recent call last):
  File "scripts/prueba_agente.py", line 6, in <module>
    saludar_israel()
  File "scripts/prueba_agente.py", line 4, in saludar_israel
    pritn(mensaje)
NameError: name 'pritn' is not defined. Did you mean: 'print'?
"""

TAREA = (
    "Corrige automáticamente el error en scripts/prueba_agente.py. "
    "Reemplaza pritn por print."
)

client = TestClient(app)

print("=== ANTES ===")
print(PRUEBA.read_text(encoding="utf-8"))

print("\n=== LLAMANDO AGENTE ===")
res = client.post(
    "/api/cognicion/agente",
    json={"tarea": TAREA, "error": ERROR},
)
data = res.json()
print(f"HTTP {res.status_code}")
print(json.dumps(data.get("metadata", {}).get("cognicion", {}), indent=2, ensure_ascii=False))
print("\n=== RESPUESTA SALOMON ===")
print(data.get("texto", "")[:1200])

contenido = PRUEBA.read_text(encoding="utf-8")
print("\n=== DESPUES ===")
print(contenido)

sys.exit(0 if "print(mensaje)" in contenido else 1)
