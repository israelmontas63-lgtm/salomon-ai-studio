"""Parche puntual: texto inmediato, audio en segundo plano (dist en vivo)."""
from pathlib import Path

DIST = Path(__file__).resolve().parent.parent / "studio" / "dist" / "assets"
candidates = list(DIST.glob("index-*.js"))
if not candidates:
    raise SystemExit("No se encontró bundle index-*.js")

for p in candidates:
    js = p.read_text(encoding="utf-8")
    original = js

    # 1) Error de reproducción → UI ready (no quedar trabado)
    js = js.replace(
        "onError:()=>{Pe.current=!1}",
        "onError:()=>{Pe.current=!1,o(`ready`)}",
        1,
    )

    # 2) Chat: pintar texto YA; audio async (no await Re antes de ze)
    old_send = (
        "Be(e.session_id);let t=await Re(e);ze(e.texto,t.audioBase64,t.audioMime)"
    )
    new_send = (
        "Be(e.session_id);ze(e.texto||``);"
        "Re(e).then(t=>{t.audioBase64&&Le(t.audioBase64,t.audioMime)}).catch(()=>{})"
    )
    if old_send not in js:
        print(f"WARN send pattern missing in {p.name}")
    else:
        js = js.replace(old_send, new_send, 1)

    # 3) Boot bienvenida: mensaje primero, luego audio
    old_boot = (
        "let r=await Re({texto:t.mensaje,audio_base64:t.audio_base64,"
        "audio_mime:t.audio_mime,metadata:{}});n([{id:De(),role:`ai`,"
        "text:t.mensaje,typing:!0,saved:!1,audioBase64:r.audioBase64,"
        "audioMime:r.audioMime}]),r.audioBase64&&Le(r.audioBase64,r.audioMime)"
    )
    # Variante flexible: buscar tramo
    marker = "let r=await Re({texto:t.mensaje"
    if marker in js:
        start = js.index(marker)
        # hasta el siguiente ;window.setTimeout o ;}catch
        end_candidates = [
            js.find(",window.setTimeout", start),
            js.find(";window.setTimeout", start),
            js.find("}catch", start),
        ]
        end = min(c for c in end_candidates if c > start)
        chunk = js[start:end]
        new_boot = (
            "n([{id:De(),role:`ai`,text:t.mensaje||``,typing:!0,saved:!1,"
            "audioBase64:null,audioMime:`audio/wav`}]),o(`speaking`),"
            "Re({texto:t.mensaje,audio_base64:t.audio_base64,audio_mime:t.audio_mime,"
            "metadata:{}}).then(r=>{r.audioBase64&&Le(r.audioBase64,r.audioMime)})"
            ".catch(()=>{})"
        )
        js = js[:start] + new_boot + js[end:]
        print(f"boot patched ({len(chunk)} chars)")
    else:
        print("WARN boot pattern missing")

    if js == original:
        print(f"NO CHANGES {p.name}")
    else:
        p.write_text(js, encoding="utf-8")
        print(f"PATCHED {p.name} delta={len(js)-len(original)}")
