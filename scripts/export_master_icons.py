"""
Export PWA icons from Master Asset 255542.
Preserves SA / gold / metal; optional white contrast halo outside gold bezel.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "static" / "assets" / "master-255542.png"
OUT_DIR = ROOT / "static" / "assets"
BLACK = (10, 10, 10, 255)
WHITE = (255, 255, 255, 255)

# Halo fino (~2.2% del lado) — contraste en modo noche sin romper elegancia
HALO_RATIO = 0.022
# El icono maestro ocupa el interior; el resto es el halo blanco
INNER_RATIO = 1.0 - (HALO_RATIO * 2.15)
CORNER_RATIO = 0.225  # squircle / iOS-like roundness


def is_studio_bg(p: tuple[int, int, int, int]) -> bool:
    r, g, b, a = p
    if a < 10:
        return True
    if r > 170 and g > 170 and b > 170 and abs(r - g) < 35 and abs(g - b) < 35:
        return True
    if r > 220 and g > 220 and b > 220:
        return True
    return False


def content_bbox(im: Image.Image) -> tuple[int, int, int, int]:
    pixels = im.load()
    w, h = im.size
    minx, miny, maxx, maxy = w, h, 0, 0
    found = False
    for y in range(h):
        for x in range(w):
            if not is_studio_bg(pixels[x, y]):
                found = True
                if x < minx:
                    minx = x
                if y < miny:
                    miny = y
                if x > maxx:
                    maxx = x
                if y > maxy:
                    maxy = y
    if not found:
        return (0, 0, w - 1, h - 1)
    pad = max(2, min(w, h) // 200)
    return (
        max(0, minx - pad),
        max(0, miny - pad),
        min(w - 1, maxx + pad),
        min(h - 1, maxy + pad),
    )


def strip_studio_to_black(im: Image.Image) -> Image.Image:
    out = im.copy()
    px = out.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            if is_studio_bg(px[x, y]):
                px[x, y] = BLACK
    return out


def to_square_black(im: Image.Image) -> Image.Image:
    w, h = im.size
    side = max(w, h)
    canvas = Image.new("RGBA", (side, side), BLACK)
    canvas.paste(im, ((side - w) // 2, (side - h) // 2), im)
    return canvas


def extract_master_face() -> Image.Image:
    im = Image.open(MASTER).convert("RGBA")
    box = content_bbox(im)
    cropped = im.crop((box[0], box[1], box[2] + 1, box[3] + 1))
    cleaned = strip_studio_to_black(cropped)
    return to_square_black(cleaned)


def apply_white_halo(face: Image.Image, size: int) -> Image.Image:
    """
    Outer white rim (halo) → original master icon inset (gold bezel intact).
    No redesign of SA / metal / wordmark — only geometry padding.
    """
    # Lienzo negro (modo noche / fondo de launcher)
    out = Image.new("RGBA", (size, size), BLACK)
    draw = ImageDraw.Draw(out)
    radius = max(8, int(size * CORNER_RATIO))

    # Halo blanco nítido (squircle completo)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=WHITE)

    # Icono maestro intacto, inset → deja ver el marco blanco fino
    inner = max(8, int(size * INNER_RATIO))
    if inner % 2:
        inner -= 1
    master = face.resize((inner, inner), Image.Resampling.LANCZOS)
    offset = (size - inner) // 2

    mask = Image.new("L", (inner, inner), 0)
    mdraw = ImageDraw.Draw(mask)
    ir = max(6, int(inner * CORNER_RATIO))
    mdraw.rounded_rectangle((0, 0, inner - 1, inner - 1), radius=ir, fill=255)
    # Antialiasing leve solo en la unión halo↔oro (no texturiza el blanco)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=0.35))

    out.paste(master, (offset, offset), mask)
    return out


def export_size(face: Image.Image, size: int, path: Path) -> None:
    out = apply_white_halo(face, size)
    out.convert("RGB").save(path, format="PNG", optimize=True)
    print(f"wrote {path.name} {size}x{size} halo={HALO_RATIO:.1%}")


def main() -> None:
    if not MASTER.is_file():
        raise SystemExit(f"Missing master: {MASTER}")

    face = extract_master_face()
    face_path = OUT_DIR / "icon-master.png"
    face.save(face_path, format="PNG", optimize=True)
    print(f"master face {face.size} -> {face_path.name}")

    for size, name in (
        (180, "apple-touch-icon.png"),
        (192, "icon-192.png"),
        (512, "icon-512.png"),
        (1024, "icon-1024.png"),
    ):
        export_size(face, size, OUT_DIR / name)

    # Preview grande para maqueta / verificación
    preview = apply_white_halo(face, 1024)
    preview_path = OUT_DIR / "icon-halo-preview.png"
    preview.convert("RGB").save(preview_path, format="PNG", optimize=True)
    print(f"wrote {preview_path.name}")


if __name__ == "__main__":
    main()
