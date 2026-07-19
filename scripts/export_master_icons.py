"""Export PWA icons from Master Asset 255542 — resize only, no redesign of logo."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "static" / "assets" / "master-255542.png"
OUT_DIR = ROOT / "static" / "assets"
BLACK = (10, 10, 10, 255)


def is_studio_bg(p: tuple[int, int, int, int]) -> bool:
    r, g, b, a = p
    if a < 10:
        return True
    # Light gray / white studio backdrop (and soft shadows on gray)
    if r > 170 and g > 170 and b > 170 and abs(r - g) < 35 and abs(g - b) < 35:
        return True
    # Near-white sparkles / artifacts outside icon
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
    """Replace studio gray with black; never alter gold/black icon pixels."""
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


def export_size(src: Image.Image, size: int, path: Path) -> None:
    out = src.resize((size, size), Image.Resampling.LANCZOS)
    flat = Image.new("RGBA", (size, size), BLACK)
    flat.alpha_composite(out)
    flat.convert("RGB").save(path, format="PNG", optimize=True)
    print(f"wrote {path.name} {size}x{size}")


def main() -> None:
    if not MASTER.is_file():
        raise SystemExit(f"Missing master: {MASTER}")

    im = Image.open(MASTER).convert("RGBA")
    print("master", im.size)
    box = content_bbox(im)
    print("bbox", box)
    cropped = im.crop((box[0], box[1], box[2] + 1, box[3] + 1))
    cleaned = strip_studio_to_black(cropped)
    square = to_square_black(cleaned)

    square_path = OUT_DIR / "icon-master.png"
    square.save(square_path, format="PNG", optimize=True)
    print(f"wrote {square_path.name} {square.size}")

    for size, name in (
        (180, "apple-touch-icon.png"),
        (192, "icon-192.png"),
        (512, "icon-512.png"),
        (1024, "icon-1024.png"),
    ):
        export_size(square, size, OUT_DIR / name)


if __name__ == "__main__":
    main()
