#!/usr/bin/env python3
"""
Salomón AI — generador oficial de identidad visual (íconos).

Fuente: brand/sa-emblem.png (diseño oficial, sin rediseño).
Genera escalado inteligente + packs Android / iOS / Windows / macOS / Linux / PWA.
"""
from __future__ import annotations

import base64
import io
import json
import shutil
import struct
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SRC_CANDIDATES = [
    ROOT / "studio" / "dist" / "brand" / "sa-emblem.png",
    ROOT / "studio" / "public" / "brand" / "sa-emblem.png",
    ROOT / "studio" / "dist" / "brand" / "sa-master.png",
]
DEPLOY_ROOTS = [
    ROOT / "studio" / "dist",
    ROOT / "studio" / "public",
]
BRAND_PACK = ROOT / "brand" / "icons"
SIZES = [1024, 768, 512, 384, 256, 192, 180, 152, 144, 128, 96, 72, 64, 48, 32, 24, 16]
BG = (10, 10, 10, 255)  # negro profundo de marca
# Alias de compatibilidad: mismas rutas que ya usa PWA/HTML/app.py (NO borrar).
V2_ALIASES = {
    "icon-192.png": "icon-192-v2.png",
    "icon-512.png": "icon-512-v2.png",
    "icon-192-maskable.png": "icon-192-maskable-v2.png",
    "icon-512-maskable.png": "icon-512-maskable-v2.png",
    "apple-touch-icon.png": "apple-touch-icon-v2.png",
    "favicon.ico": "favicon-v2.ico",
    "favicon.png": "favicon-v2.png",
    "favicon.svg": "favicon-v2.svg",
    "icon.svg": "icon-v2.svg",
    "favicon-32.png": "favicon-32-v2.png",
    "favicon-64.png": "favicon-64-v2.png",
}


def load_source() -> Image.Image:
    for p in SRC_CANDIDATES:
        if p.is_file():
            im = Image.open(p).convert("RGBA")
            # Si es el master con fondo gris de mockup, recortar emblema
            if "sa-master" in p.name:
                im = extract_from_mockup(im)
            return square_pad(im)
    raise FileNotFoundError("No se encontró sa-emblem.png / sa-master.png")


def extract_from_mockup(img: Image.Image) -> Image.Image:
    """Recorta el squircle del mockup gris sin alterar el diseño."""
    w, h = img.size
    px = img.load()

    def is_backdrop(r, g, b, a):
        if a < 10:
            return True
        # gris claro del mockup
        if min(r, g, b) > 150 and abs(r - g) < 25 and abs(g - b) < 25:
            return True
        return False

    from collections import deque

    visited = bytearray(w * h)
    q = deque()
    for seed in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1)]:
        q.append(seed)
    while q:
        x, y = q.popleft()
        i = y * w + x
        if visited[i]:
            continue
        r, g, b, a = px[x, y]
        if not is_backdrop(r, g, b, a):
            continue
        visited[i] = 1
        px[x, y] = (0, 0, 0, 0)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not visited[ny * w + nx]:
                q.append((nx, ny))

    bbox = img.getbbox()
    if not bbox:
        return img
    return img.crop(bbox)


def square_pad(im: Image.Image) -> Image.Image:
    w, h = im.size
    side = max(w, h)
    canvas = Image.new("RGBA", (side, side), BG)
    canvas.paste(im, ((side - w) // 2, (side - h) // 2), im)
    return canvas


def resize_hq(im: Image.Image, size: int) -> Image.Image:
    out = im.resize((size, size), Image.Resampling.LANCZOS)
    if size <= 64:
        out = out.filter(ImageFilter.UnsharpMask(radius=0.6, percent=120, threshold=2))
        out = ImageEnhance.Contrast(out).enhance(1.06)
    elif size <= 128:
        out = out.filter(ImageFilter.UnsharpMask(radius=0.8, percent=90, threshold=2))
    return out


def smart_scale(master: Image.Image, size: int) -> Image.Image:
    """
    Grandes: diseño completo.
    Pequeños (<=48): encuadre al monograma SA (misma identidad, mejor lectura).
    """
    w, h = master.size
    if size <= 48:
        # Encuadre superior-centro: SA + marco; omite wordmark ilegible
        left = int(w * 0.10)
        top = int(h * 0.06)
        right = int(w * 0.90)
        bottom = int(h * 0.72)
        crop = master.crop((left, top, right, bottom))
        crop = square_pad(crop)
        return resize_hq(crop, size)
    if size <= 72:
        # Ligero zoom: wordmark aún presente pero más grande
        left = int(w * 0.04)
        top = int(h * 0.02)
        right = int(w * 0.96)
        bottom = int(h * 0.92)
        crop = master.crop((left, top, right, bottom))
        crop = square_pad(crop)
        return resize_hq(crop, size)
    return resize_hq(master, size)


def make_maskable(im: Image.Image, size: int, safe: float = 0.80) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), BG)
    content = max(1, int(size * safe))
    logo = resize_hq(im, content)
    offset = (size - content) // 2
    canvas.paste(logo, (offset, offset), logo)
    return canvas


def make_monochrome(im: Image.Image, size: int) -> Image.Image:
    """Silueta blanca sobre transparente (Android monochrome / notificaciones)."""
    base = resize_hq(im, size).convert("RGBA")
    r, g, b, a = base.split()
    # Dorado/brillo → alfa; fondo negro → transparente
    lum = Image.merge("RGB", (r, g, b)).convert("L")
    # Umbral suave: pixeles más claros que el negro mate
    mask = lum.point(lambda p: 255 if p > 45 else 0)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    white = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    out.paste(white, (0, 0), mask)
    return out


def make_adaptive_layers(master: Image.Image, size: int = 432) -> tuple[Image.Image, Image.Image]:
    """Foreground (contenido) + background sólido negro."""
    bg = Image.new("RGBA", (size, size), BG)
    # Safe zone ~66% del lienzo adaptativo
    content = int(size * 0.66)
    logo = resize_hq(master, content)
    fg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    off = (size - content) // 2
    fg.paste(logo, (off, off), logo)
    return fg, bg


def save_png(im: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, format="PNG", optimize=True)


def save_webp(im: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, format="WEBP", quality=92, method=6)


def png_to_svg(im: Image.Image, path: Path) -> None:
    """SVG oficial: PNG embebido (preserva metal/3D sin vectorizar/rediseñar)."""
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    w, h = im.size
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<image width="{w}" height="{h}" href="data:image/png;base64,{b64}"/>'
        f"</svg>\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")


def save_ico(images: list[Image.Image], path: Path) -> None:
    """ICO multi-tamaño con PNG embebido (Windows Vista+ / navegadores)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rgba = sorted((im.convert("RGBA") for im in images), key=lambda im: im.width)
    entries = []
    payloads = []
    for im in rgba:
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
        data = buf.getvalue()
        w = 0 if im.width >= 256 else im.width
        h = 0 if im.height >= 256 else im.height
        entries.append((w, h, len(data)))
        payloads.append(data)
    # ICONDIR + ICONDIRENTRY*n + payloads
    offset = 6 + 16 * len(entries)
    out = bytearray()
    out += struct.pack("<HHH", 0, 1, len(entries))
    for (w, h, size), _ in zip(entries, payloads):
        out += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, size, offset)
        offset += size
    for data in payloads:
        out += data
    path.write_bytes(out)


def write_icns(images_by_size: dict[int, Image.Image], path: Path) -> None:
    """ICNS mínimo (iconos PNG embebidos) compatible con macOS modernos."""
    # Tipos ICNS para PNG
    type_map = {
        16: b"icp4",
        32: b"icp5",
        64: b"icp6",
        128: b"ic07",
        256: b"ic08",
        512: b"ic09",
        1024: b"ic10",
    }
    chunks = []
    for size, tag in type_map.items():
        im = images_by_size.get(size)
        if im is None:
            continue
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        data = buf.getvalue()
        chunks.append(tag + struct.pack(">I", 8 + len(data)) + data)
    body = b"".join(chunks)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"icns" + struct.pack(">I", 8 + len(body)) + body)


def sync_v2_aliases(root: Path) -> None:
    """Mantiene archivos *-v2 existentes como copias del ícono oficial (aditivo)."""
    for src_name, alias_name in V2_ALIASES.items():
        src = root / src_name
        if src.is_file():
            shutil.copyfile(src, root / alias_name)


def write_ios_contents(appiconset: Path) -> None:
    images = []
    # Conjunto App Store / iPhone / iPad habitual
    specs = [
        ("iphone", "20x20", "2x", 40),
        ("iphone", "20x20", "3x", 60),
        ("iphone", "29x29", "2x", 58),
        ("iphone", "29x29", "3x", 87),
        ("iphone", "40x40", "2x", 80),
        ("iphone", "40x40", "3x", 120),
        ("iphone", "60x60", "2x", 120),
        ("iphone", "60x60", "3x", 180),
        ("ipad", "20x20", "1x", 20),
        ("ipad", "20x20", "2x", 40),
        ("ipad", "29x29", "1x", 29),
        ("ipad", "29x29", "2x", 58),
        ("ipad", "40x40", "1x", 40),
        ("ipad", "40x40", "2x", 80),
        ("ipad", "76x76", "1x", 76),
        ("ipad", "76x76", "2x", 152),
        ("ipad", "83.5x83.5", "2x", 167),
        ("ios-marketing", "1024x1024", "1x", 1024),
    ]
    for idiom, size, scale, px in specs:
        fname = f"icon-{px}.png"
        images.append(
            {
                "size": size,
                "idiom": idiom,
                "filename": fname,
                "scale": scale,
            }
        )
    (appiconset / "Contents.json").write_text(
        json.dumps({"images": images, "info": {"version": 1, "author": "salomon-ai"}}, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    master512 = load_source()
    master = resize_hq(master512, 1024)

    # Master oficial en brand/
    brand_dir = ROOT / "brand"
    brand_dir.mkdir(parents=True, exist_ok=True)
    save_png(master, brand_dir / "sa-official-1024.png")
    save_png(master, brand_dir / "sa-master.png")
    save_webp(master, brand_dir / "sa-official-1024.webp")

    pack = BRAND_PACK
    if pack.exists():
        shutil.rmtree(pack)
    pack.mkdir(parents=True)

    sized: dict[int, Image.Image] = {s: smart_scale(master, s) for s in SIZES}

    # --- Universal PNG / WebP ---
    for s, im in sized.items():
        save_png(im, pack / "png" / f"{s}.png")
        save_webp(im, pack / "webp" / f"{s}.webp")

    png_to_svg(sized[512], pack / "svg" / "icon.svg")
    png_to_svg(sized[512], pack / "svg" / "favicon.svg")

    ico_sizes = [16, 24, 32, 48, 64, 128, 256]
    save_ico([sized[s] for s in ico_sizes], pack / "windows" / "salomon-ai.ico")
    save_ico([sized[s] for s in [16, 32, 48]], pack / "favicon.ico")

    write_icns({s: sized[s] for s in [16, 32, 64, 128, 256, 512, 1024]}, pack / "macos" / "AppIcon.icns")

    # --- Android ---
    android = pack / "android"
    dens = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }
    for folder, px in dens.items():
        save_png(sized[px], android / folder / "ic_launcher.png")
        save_png(make_maskable(master, px), android / folder / "ic_launcher_round.png")
        save_png(make_monochrome(master, px), android / folder / "ic_launcher_monochrome.png")

    fg, bg = make_adaptive_layers(master, 432)
    save_png(fg, android / "adaptive" / "ic_launcher_foreground.png")
    save_png(bg, android / "adaptive" / "ic_launcher_background.png")
    save_png(make_monochrome(master, 432), android / "adaptive" / "ic_launcher_monochrome.png")
    save_png(sized[512], android / "playstore-512.png")
    save_png(make_maskable(master, 512), android / "playstore-512-maskable.png")
    (android / "AndroidManifest.icon-snippet.xml").write_text(
        """<!-- Fragmento para AndroidManifest.xml -->
<application
    android:icon="@mipmap/ic_launcher"
    android:roundIcon="@mipmap/ic_launcher_round"
    android:label="Salomón AI">
</application>
""",
        encoding="utf-8",
    )

    # --- iOS ---
    ios = pack / "ios" / "AppIcon.appiconset"
    ios.mkdir(parents=True)
    needed_ios = {20, 29, 40, 58, 60, 76, 80, 87, 120, 152, 167, 180, 1024}
    for px in needed_ios:
        save_png(smart_scale(master, px), ios / f"icon-{px}.png")
    write_ios_contents(ios)

    # --- Windows tiles ---
    win = pack / "windows"
    win_map = {
        "Square44x44Logo.png": 44,
        "Square71x71Logo.png": 71,
        "Square150x150Logo.png": 150,
        "Square310x310Logo.png": 310,
        "StoreLogo.png": 50,
        "SplashScreen.png": 620,  # se recorta luego
    }
    for name, px in win_map.items():
        if name == "SplashScreen.png":
            # Tile ancho: icono centrado en negro
            canvas = Image.new("RGBA", (620, 300), BG)
            logo = smart_scale(master, 220)
            canvas.paste(logo, ((620 - 220) // 2, (300 - 220) // 2), logo)
            save_png(canvas, win / name)
        else:
            save_png(smart_scale(master, px), win / name)
    # Wide tile
    wide = Image.new("RGBA", (310, 150), BG)
    logo = smart_scale(master, 110)
    wide.paste(logo, ((310 - 110) // 2, (150 - 110) // 2), logo)
    save_png(wide, win / "Wide310x150Logo.png")

    # --- macOS iconset ---
    mac = pack / "macos" / "AppIcon.iconset"
    mac.mkdir(parents=True)
    for s in (16, 32, 128, 256, 512):
        save_png(sized[s], mac / f"icon_{s}x{s}.png")
        hi = s * 2
        save_png(sized[hi] if hi in sized else resize_hq(master, hi), mac / f"icon_{s}x{s}@2x.png")
    save_png(sized[1024], mac / "icon_512x512@2x.png")

    # --- Linux hicolor ---
    linux = pack / "linux" / "hicolor"
    for s in (16, 24, 32, 48, 64, 128, 256, 512):
        save_png(sized[s], linux / f"{s}x{s}" / "apps" / "salomon-ai.png")
    save_png(sized[512], pack / "linux" / "salomon-ai.png")
    (pack / "linux" / "salomon-ai.desktop").write_text(
        """[Desktop Entry]
Name=Salomón AI
Comment=Asistente de inteligencia artificial
Exec=salomon-ai
Icon=salomon-ai
Terminal=false
Type=Application
Categories=Utility;Office;
""",
        encoding="utf-8",
    )

    # --- Notification / shortcut / dock / taskbar aliases ---
    extras = pack / "aliases"
    save_png(sized[192], extras / "launcher-192.png")
    save_png(sized[512], extras / "splash-512.png")
    save_png(sized[256], extras / "dock-256.png")
    save_png(sized[48], extras / "taskbar-48.png")
    save_png(sized[32], extras / "shortcut-32.png")
    save_png(make_monochrome(master, 96), extras / "notification-96.png")

    # Capacitor stub (proyecto aún sin capacitor nativo)
    cap = pack / "capacitor"
    save_png(sized[192], cap / "icon-192.png")
    save_png(sized[512], cap / "icon-512.png")
    (cap / "capacitor.config.icons.json").write_text(
        json.dumps(
            {
                "appName": "Salomón AI",
                "appId": "ai.salomon.studio",
                "plugins": {"SplashScreen": {"backgroundColor": "#0A0A0A"}},
                "icon": "brand/icons/capacitor/icon-512.png",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    # --- Deploy aditivo a studio/dist + studio/public (no borra, no cambia rutas) ---
    for root in DEPLOY_ROOTS:
        brand = root / "brand"
        brand.mkdir(parents=True, exist_ok=True)
        save_png(master, brand / "sa-official-1024.png")
        save_png(master, brand / "sa-master.png")
        save_png(sized[512], brand / "sa-emblem.png")

        # PWA / web root (sobrescribe píxeles; conserva nombres)
        save_png(sized[192], root / "icon-192.png")
        save_png(sized[512], root / "icon-512.png")
        save_png(sized[1024], root / "icon-1024.png")
        save_png(make_maskable(master, 192), root / "icon-192-maskable.png")
        save_png(make_maskable(master, 512), root / "icon-512-maskable.png")
        save_png(sized[180], root / "apple-touch-icon.png")
        save_png(sized[180], root / "apple-touch-icon-180.png")
        save_png(sized[152], root / "apple-touch-icon-152.png")
        save_png(sized[32], root / "favicon-32.png")
        save_png(sized[64], root / "favicon-64.png")
        save_png(sized[16], root / "favicon-16.png")
        save_png(sized[192], root / "favicon.png")
        shutil.copyfile(pack / "favicon.ico", root / "favicon.ico")
        shutil.copyfile(pack / "svg" / "icon.svg", root / "icon.svg")
        shutil.copyfile(pack / "svg" / "favicon.svg", root / "favicon.svg")
        save_webp(sized[192], root / "icon-192.webp")
        save_webp(sized[512], root / "icon-512.webp")
        sync_v2_aliases(root)

    (pack / "README.md").write_text(
        """# Salomón AI — Icon System (oficial, modo seguro)

Fuente: `brand/sa-official-1024.png`.

- No rediseña el emblema.
- No elimina archivos del proyecto.
- Mantiene alias `*-v2` para compatibilidad con HTML/PWA/app.py existentes.

```bash
python scripts/generate_official_icons.py
```
""",
        encoding="utf-8",
    )

    print("OK master 1024 + pack en", pack)
    print("Deployed to:", ", ".join(str(r) for r in DEPLOY_ROOTS))


if __name__ == "__main__":
    main()
