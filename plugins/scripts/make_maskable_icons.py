"""Genera iconos maskable opacos (sin alpha) para criterio PWA Chrome."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ICONS = ROOT / "static" / "icons"
BG = (10, 10, 10, 255)  # #0A0A0A


def to_maskable(src: Path, dst: Path, size: int) -> None:
    im = Image.open(src).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), BG)
    canvas.alpha_composite(im)
    canvas.convert("RGB").save(dst, format="PNG", optimize=True)
    print(f"wrote {dst.name} {size}x{size} opaque")


def main() -> None:
    to_maskable(ICONS / "android-chrome-192x192.png", ICONS / "android-chrome-192x192-maskable.png", 192)
    to_maskable(ICONS / "android-chrome-512x512.png", ICONS / "android-chrome-512x512-maskable.png", 512)


if __name__ == "__main__":
    main()
