/**
 * Verifica firmas SHA256 del Golden State (Inmortal).
 * Uso: node scripts/verify-golden-state.js
 * Exit 1 si hay drift → bloqueo de integridad.
 */
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const ROOT = path.resolve(__dirname, "..");
const ledger = JSON.parse(
  fs.readFileSync(path.join(ROOT, "salomon_integrity_ledger.json"), "utf8")
);

const attemptsPath = path.join(ROOT, "salomon_integrity_attempts.jsonl");

function logAttempt(component, detail) {
  const line =
    JSON.stringify({
      at: new Date().toISOString(),
      component,
      detail,
      protocol: ledger.protocol,
    }) + "\n";
  fs.appendFileSync(attemptsPath, line);
  console.warn(
    `[SalomonInmortal] Intento de modificación no autorizado detectado en ${component}. Acceso denegado. (${detail})`
  );
}

function sha256(fileRel) {
  const buf = fs.readFileSync(path.join(ROOT, fileRel));
  return crypto.createHash("sha256").update(buf).digest("hex");
}

let drift = 0;
const sigs = ledger.file_signatures_sha256 || {};
for (const [file, expected] of Object.entries(sigs)) {
  const full = path.join(ROOT, file);
  if (!fs.existsSync(full)) {
    console.error("MISSING", file);
    logAttempt(file, "MISSING");
    drift += 1;
    continue;
  }
  const actual = sha256(file);
  if (actual !== expected) {
    console.error("DRIFT", file);
    console.error("  expected", expected);
    console.error("  actual  ", actual);
    logAttempt(file, "SIGNATURE_DRIFT");
    drift += 1;
  } else {
    console.info("OK", file);
  }
}

if (drift) {
  console.error(
    `\n[SalomonInmortal] Golden State DRIFT x${drift} — escritura/deploy bloqueados sin AUTORIZADO`
  );
  process.exit(1);
}

console.info(
  `\n[SalomonInmortal] Golden State INTACTO — ${ledger.golden_state.version} (${ledger.protocol} ${ledger.protocol_version})`
);
process.exit(0);
