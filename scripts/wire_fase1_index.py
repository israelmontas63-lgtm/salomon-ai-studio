# -*- coding: utf-8 -*-
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
src = ROOT / "studio" / "public" / "salomon-fase1.js"
dst = ROOT / "studio" / "dist" / "salomon-fase1.js"
shutil.copy2(src, dst)

snippet = '<script src="/salomon-fase1.js?v=1" defer></script>\n    '
pat = re.compile(r'(<script src="/salomon-update\.js\?[^"]+" defer></script>)')

for rel in ("studio/public/index.html", "studio/dist/index.html"):
    p = ROOT / rel
    t = p.read_text(encoding="utf-8")
    if "salomon-fase1.js" in t:
        print("already", rel)
        continue
    t2, n = pat.subn(snippet + r"\1", t, count=1)
    if n:
        p.write_text(t2, encoding="utf-8", newline="\n")
        print("wired", rel)
    else:
        print("FAIL", rel)
