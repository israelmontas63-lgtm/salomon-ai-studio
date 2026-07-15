/**
 * Clasificador de intención local (rápido, sin red).
 * Devuelve { kind, prompt, confidence }.
 */
const IMAGE_RE =
  /\b(imagen|im[aá]genes|dibuja|dibujar|ilustra|ilustraci[oó]n|genera(r)?\s+(una\s+)?(foto|imagen|picture)|crea(r)?\s+(una\s+)?(imagen|ilustraci[oó]n)|photo|picture|png|jpg)\b/i;

const VIDEO_RE =
  /\b(v[ií]deo|video|clip|pel[ií]cula|animaci[oó]n|edita(r)?\s+(el\s+)?v[ií]deo|genera(r)?\s+(un\s+)?v[ií]deo)\b/i;

const CHAT_FORCE_RE =
  /\b(explica|cu[eé]ntame|responde|chat|pregunta|qu[eé]\s+es|c[oó]mo\s+funciona|ayuda\s+con\s+texto)\b/i;

export function classifyIntent(rawText) {
  const text = (rawText || "").trim();
  if (!text) {
    return { kind: "chat", prompt: "", confidence: 0 };
  }

  if (CHAT_FORCE_RE.test(text) && !IMAGE_RE.test(text) && !VIDEO_RE.test(text)) {
    return { kind: "chat", prompt: text, confidence: 0.85 };
  }

  if (VIDEO_RE.test(text)) {
    return {
      kind: "video",
      prompt: text,
      confidence: 0.9,
    };
  }

  if (IMAGE_RE.test(text)) {
    return {
      kind: "image",
      prompt: stripMediaPrefix(text),
      confidence: 0.9,
    };
  }

  return { kind: "chat", prompt: text, confidence: 0.7 };
}

function stripMediaPrefix(text) {
  return text
    .replace(
      /^(por\s+favor[, ]*)?(puedes\s+)?(genera(r)?|crea(r)?|dibuja(r)?|hazme)\s+(una?\s+)?(imagen|ilustraci[oó]n|foto)\s+(de\s+|del?\s+|con\s+)?/i,
      ""
    )
    .trim() || text;
}
