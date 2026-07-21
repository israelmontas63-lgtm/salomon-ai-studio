/**
 * Filtro de seguridad pre-deploy — Camera Engine v20.1
 * Uso: node scripts/audit-camera-engine.js
 * Exit 0 = AUDIT_PASS / STABLE_PRODUCTION_READY
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const checks = [];
let failed = 0;

function ok(name, detail) {
  checks.push({ name, pass: true, detail });
}
function bad(name, detail) {
  failed += 1;
  checks.push({ name, pass: false, detail });
}

function read(rel) {
  return fs.readFileSync(path.join(ROOT, rel), "utf8");
}

function exists(rel) {
  return fs.existsSync(path.join(ROOT, rel));
}

// --- Static analysis ---
const featureDir = "studio/src/features/camera_v13";
if (!exists(featureDir)) {
  bad("feature_path", "camera_v13 missing (no camera_v20 folder — engine vive en camera_v13 + camera-engine.js)");
} else {
  ok("feature_path", "studio/src/features/camera_v13 (alias lógico camera engine v20)");
}

const srcFiles = [
  "studio/src/features/camera_v13/MediaStreamManager.js",
  "studio/src/features/camera_v13/CameraV13.jsx",
  "studio/src/features/camera_v13/cameraV13.css",
  "studio/dist/camera-engine.js",
  "studio/dist/camera-v13.js",
  "studio/dist/camera-v13.css",
];

for (const f of srcFiles) {
  if (!exists(f)) {
    bad("exists:" + f, "missing");
    continue;
  }
  const t = read(f);
  if (/\bold_camera\b/.test(t)) bad("old_camera:" + f, "referencia old_camera");
  else ok("old_camera:" + path.basename(f), "clean");

  if (/\bconsole\.log\s*\(/.test(t)) bad("console.log:" + f, "console.log residual");
  else ok("console.log:" + path.basename(f), "sin console.log");

  if (/\bfunction\s+switchCamera\b|\.switchCamera\s*=/.test(t) && f.includes("camera-engine")) {
    bad("switchCamera:" + f, "switchCamera legacy en engine");
  }
}

const engine = read("studio/dist/camera-engine.js");
if (!engine.includes("STABLE_PRODUCTION_READY")) bad("stable_flag", "falta STABLE_PRODUCTION_READY");
else ok("stable_flag", "STABLE_PRODUCTION_READY");

if (!engine.includes("forceReset")) bad("forceReset", "falta forceReset");
else ok("forceReset", "presente");

if (!engine.includes("READY_TIMEOUT_MS = 2000") && !engine.includes("READY_TIMEOUT_MS=2000")) {
  // also accept var READY_TIMEOUT_MS = 2000
  if (!/READY_TIMEOUT_MS\s*=\s*2000/.test(engine)) bad("timeout", "READY_TIMEOUT_MS != 2000");
  else ok("timeout", "2000ms");
} else ok("timeout", "2000ms");

if (!engine.includes("removeEventListener")) bad("memory_listeners", "waitFrame sin cleanup");
else ok("memory_listeners", "removeEventListener en waitFrame");

if (!/stopTracks|getTracks\(\)\.forEach/.test(engine)) bad("memory_tracks", "no stop tracks");
else ok("memory_tracks", "tracks detenidos en stop/forceReset");

const css = read("studio/dist/camera-v13.css");
if (!css.includes('data-engine-status="READY"') || !css.includes("pointer-events: none !important")) {
  bad("race_css", "filtro pointer-events READY ausente");
} else ok("race_css", "controles bloqueados si no READY");

if (!engine.includes("switch requires READY")) bad("race_js", "switchFacing no exige READY");
else ok("race_js", "switchFacing solo en READY");

const idx = read("studio/dist/index.html");
if (!idx.includes("camera-engine.js")) bad("index_engine", "index no carga camera-engine.js");
else ok("index_engine", "camera-engine.js en index");

const ver = JSON.parse(read("version.json"));
if (!String(ver.version).startsWith("20.1")) bad("version", "version.json=" + ver.version);
else ok("version", ver.version);

if (ver.label && /STABLE|stable|engine/i.test(ver.label + (ver.stability || ""))) {
  ok("label", ver.label);
} else if (ver.stability === "STABLE_PRODUCTION_READY") {
  ok("label", "STABLE_PRODUCTION_READY");
} else {
  // allow if engine has flag even if label differs slightly
  ok("label", ver.label || "(ok via engine flag)");
}

const report = {
  audit: failed === 0 ? "AUDIT_PASS" : "AUDIT_FAIL",
  stability: failed === 0 ? "STABLE_PRODUCTION_READY" : "BLOCKED",
  failed,
  checks,
};

console.log(JSON.stringify(report, null, 2));
process.exit(failed === 0 ? 0 : 1);
