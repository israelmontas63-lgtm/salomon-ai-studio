# -*- coding: utf-8 -*-
"""
Web Architect Engine v96 — diseño web bajo Render Free Tier (logic-first).

HTML5 · CSS3 responsivo · JavaScript · Flask/React (estructura).
Sin librerías pesadas: solo plantillas y guías de despliegue.
"""

from __future__ import annotations

from typing import Any

from cognicion.identidad import FIRMA_OWNERSHIP

_MARCAS_WEB = (
    "página web", "pagina web", "sitio web", "landing", "html", "css",
    "diseña una web", "disena una web", "diseñar web", "disenar web",
    "frontend", "react", "flask", "wireframe", "maqueta web",
    "despliega una página", "despliega una pagina", "crea una página",
    "crea una pagina", "website", "responsive",
)


def es_peticion_web(texto: str) -> bool:
    t = (texto or "").lower()
    return any(m in t for m in _MARCAS_WEB)


def firmar_codigo(codigo: str, *, lenguaje: str = "html") -> str:
    """Inyecta firma de ownership de Israel Monta (v102)."""
    from cognicion.identidad import (
        FIRMA_COMENTARIO_HTML,
        FIRMA_COMENTARIO_JS,
        FIRMA_COMENTARIO_PY,
        FIRMA_OWNERSHIP,
        firma_comentario,
    )

    firma = FIRMA_OWNERSHIP
    c = (codigo or "").strip()
    if firma in c or "Created by Israel Monta" in c:
        return c
    if lenguaje in {"html", "htm"}:
        meta = f"  {FIRMA_COMENTARIO_HTML}\n"
        if "<head>" in c.lower():
            import re

            return re.sub(
                r"(?i)(<head[^>]*>)",
                r"\1\n" + meta.rstrip(),
                c,
                count=1,
            )
        return f"{FIRMA_COMENTARIO_HTML}\n{c}"
    if lenguaje in {"css"}:
        return f"/* {firma} */\n{c}"
    if lenguaje in {"js", "javascript", "jsx", "ts", "tsx"}:
        return f"{FIRMA_COMENTARIO_JS}\n{c}"
    if lenguaje in {"py", "python", "flask"}:
        return f"{FIRMA_COMENTARIO_PY}\n{c}"
    return f"{firma_comentario(lenguaje)}\n{c}"


def plantilla_landing(titulo: str = "Salomón AI Studio") -> dict[str, str]:
    """Landing minimalista responsive (negro/oro) lista para servir estática."""
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="author" content="Israel Monta - Salomón AI Studio" />
  <title>{titulo}</title>
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <main class="hero">
    <p class="brand">Salomón AI Studio</p>
    <h1>{titulo}</h1>
    <p class="lead">Diseño e ingeniería por Israel Monta.</p>
    <a class="cta" href="#contacto">Contactar</a>
  </main>
  <section id="contacto" class="contact">
    <h2>Contacto</h2>
    <p>Proyecto vivo bajo la visión de Israel Monta.</p>
  </section>
  <script src="app.js"></script>
</body>
</html>"""
    css = """:root {
  --bg: #0a0a0b;
  --gold: #c9a962;
  --text: #f2f0ea;
  --muted: #9a958c;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  min-height: 100dvh;
  font-family: "Segoe UI", system-ui, sans-serif;
  background: radial-gradient(ellipse at top, #1a1814 0%, var(--bg) 55%);
  color: var(--text);
}
.hero {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  padding: 2rem clamp(1.25rem, 5vw, 4rem);
  gap: 1rem;
}
.brand {
  letter-spacing: 0.22em;
  text-transform: uppercase;
  font-size: 0.75rem;
  color: var(--gold);
}
h1 {
  font-size: clamp(2rem, 6vw, 3.4rem);
  max-width: 12ch;
  line-height: 1.1;
}
.lead { color: var(--muted); max-width: 36ch; }
.cta {
  margin-top: 0.75rem;
  display: inline-flex;
  padding: 0.85rem 1.4rem;
  border: 1px solid var(--gold);
  color: var(--gold);
  text-decoration: none;
  border-radius: 999px;
}
.contact { padding: 4rem clamp(1.25rem, 5vw, 4rem); }
@media (max-width: 640px) {
  .hero { align-items: stretch; }
}
"""
    js = """document.querySelectorAll('a[href^="#"]').forEach((a) => {
  a.addEventListener('click', (e) => {
    const id = a.getAttribute('href');
    const el = id && document.querySelector(id);
    if (el) {
      e.preventDefault();
      el.scrollIntoView({ behavior: 'smooth' });
    }
  });
});
"""
    return {
        "index.html": firmar_codigo(html, lenguaje="html"),
        "styles.css": firmar_codigo(css, lenguaje="css"),
        "app.js": firmar_codigo(js, lenguaje="js"),
    }


def guia_despliegue() -> str:
    return (
        "Despliegue ligero (Render Free / estático):\n"
        "1) Guarda index.html, styles.css y app.js en una carpeta.\n"
        "2) Opción A — Render Static Site: conecta el repo y publica la carpeta.\n"
        "3) Opción B — FastAPI: sirve la carpeta con StaticFiles (como studio/dist).\n"
        "4) Opción C — Flask: app = Flask(__name__); @app.route('/') return send_from_directory.\n"
        "5) No uses builds pesados de Node en Free Tier salvo que sea imprescindible.\n"
        f"6) Firma obligatoria: {FIRMA_OWNERSHIP}"
    )


def ejecutar_arquitecto_web(peticion: str) -> dict[str, Any]:
    """
    Pipeline: wireframe lógico → código firmado → guía de deploy.
    Logic-first: no importa frameworks pesados.
    """
    titulo = "Salomón AI Studio"
    lower = (peticion or "").lower()
    if "landing" in lower:
        titulo = "Landing · Salomón AI Studio"
    archivos = plantilla_landing(titulo)
    wireframe = [
        "1. Hero full-bleed: marca + título + CTA",
        "2. Sección contacto / siguiente paso",
        "3. Responsive mobile-first (CSS clamp + media query)",
        "4. Sin dependencias npm (Free Tier safe)",
    ]
    return {
        "exito": True,
        "agente": "Web_Architect",
        "protocolo": "IDENTIDAD_ARQUITECTURA_WEB",
        "version": "96.0.0",
        "wireframe": wireframe,
        "habilidades": ["HTML5", "CSS3 responsive", "JavaScript", "Flask structure", "React structure"],
        "archivos": archivos,
        "firma": FIRMA_OWNERSHIP,
        "despliegue": guia_despliegue(),
        "peticion": (peticion or "")[:300],
        "free_tier_safe": True,
    }


def bloque_contexto_web(peticion: str) -> str:
    pack = ejecutar_arquitecto_web(peticion)
    partes = [
        "[Web Architect Engine v96]",
        "Modo: Wireframe → Código limpio → Guía de despliegue.",
        "Wireframe:",
        *[f"- {w}" for w in pack["wireframe"]],
        f"Firma ownership obligatoria: {FIRMA_OWNERSHIP}",
        "Entrega index.html / styles.css / app.js firmados.",
        pack["despliegue"],
        "Si entregas React o Flask, mantén estructura mínima y la misma firma en comentarios.",
    ]
    # Incluir HTML firmado como referencia (recortado si hace falta)
    html = pack["archivos"].get("index.html", "")
    partes.append("\n--- index.html (referencia firmada) ---\n```html\n" + html[:3500] + "\n```")
    return "\n".join(partes)


def estado_web_architect() -> dict[str, Any]:
    return {
        "protocol": "IDENTIDAD_ARQUITECTURA_WEB",
        "version": "96.0.0",
        "module": "Web_Architect_Engine",
        "active": True,
        "skills": ["HTML5", "CSS3", "JavaScript", "Flask", "React"],
        "ownership_enforcement": True,
        "firma": FIRMA_OWNERSHIP,
        "free_tier_safe": True,
        "logic_first": True,
    }
