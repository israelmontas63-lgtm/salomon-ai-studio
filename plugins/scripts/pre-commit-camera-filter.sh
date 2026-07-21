#!/bin/sh
# Pre-commit filtro cámara — bloquea commit si AUDIT_FAIL
node scripts/audit-camera-engine.js || {
  echo "[CameraFilter] AUDIT_FAIL — commit bloqueado"
  exit 1
}
