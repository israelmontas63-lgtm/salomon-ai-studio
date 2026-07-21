"""
Clonación por píxeles desde Master Definitivo.
Extrae SOLO el squircle (halo blanco) — escala LANCZOS — sin rediseñar.
"""
from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "static" / "assets" / "master-definitivo.png"
OUT_DIR = ROOT / "static" / "assets"
BLACK = (0, 0, 0, 255)


def connected_components(mask: np.ndarray) -> list[tuple[int, int, int, int, int]]:
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    comps: list[tuple[int, int, int, int, int]] = []
    for y in range(h):
        for x in range(w):
            if not mask[y, x] or seen[y, x]:
                continue
            q = deque([(x, y)])
            seen[y, x] = True
            minx = maxx = x
            miny = maxy = y
            area = 0
            while q:
                cx, cy = q.popleft()
                area += 1
                minx = min(minx, cx)
                maxx = max(maxx, cx)
                miny = min(miny, cy)
                maxy = max(maxy, cy)
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((nx, ny))
            comps.append((area, minx, miny, maxx, maxy))
    return comps


def extract_raw_square(im: Image.Image) -> Image.Image:
    rgb = np.asarray(im.convert("RGB"), dtype=np.int16)
    h, w = rgb.shape[:2]
    cx, cy = w / 2.0, h / 2.0

    white = (
        (rgb[:, :, 0] > 225)
        & (rgb[:, :, 1] > 225)
        & (rgb[:, :, 2] > 225)
        & (np.abs(rgb[:, :, 0].astype(int) - rgb[:, :, 1].astype(int)) < 25)
        & (np.abs(rgb[:, :, 1].astype(int) - rgb[:, :, 2].astype(int)) < 25)
    )

    comps = connected_components(white)
    best = None
    best_score = -1.0
    for area, minx, miny, maxx, maxy in comps:
        bw = maxx - minx + 1
        bh = maxy - miny + 1
        if bw < 80 or bh < 80:
            continue
        aspect = bw / float(bh)
        if aspect < 0.85 or aspect > 1.18:
            continue
        bcx = (minx + maxx) / 2.0
        bcy = (miny + maxy) / 2.0
        dist = ((bcx - cx) ** 2 + (bcy - cy) ** 2) ** 0.5
        score = area * (1.0 / (1.0 + dist / 40.0)) * (1.0 - abs(1.0 - aspect) * 2)
        if score > best_score:
            best_score = score
            best = (minx, miny, maxx, maxy, bw, bh)

    if best is None:
        raise SystemExit("No se detectó squircle con halo blanco")

    minx, miny, maxx, maxy, bw, bh = best
    bcx = (minx + maxx) / 2.0
    bcy = (miny + maxy) / 2.0
    # Ligeramente más apretado para excluir labels del launcher
    side = int(max(bw, bh) * 0.985)
    if side % 2:
        side += 1
    half = side / 2.0
    x0 = int(round(bcx - half))
    y0 = int(round(bcy - half))
    x1 = x0 + side
    y1 = y0 + side
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    crop = im.crop((x0, y0, x1, y1)).convert("RGBA")
    print(f"raw extract ({x0},{y0},{x1},{y1}) size={crop.size} score={best_score:.1f}")
    return crop


def mask_to_squircle(crop: Image.Image) -> Image.Image:
    """Enmascara a squircle: elimina UI de fondo fuera del icono; preserva píxeles del asset."""
    w, h = crop.size
    side = max(w, h)
    canvas = Image.new("RGBA", (side, side), BLACK)
    canvas.paste(crop, ((side - w) // 2, (side - h) // 2), crop)

    # Máscara squircle que llega al borde (halo blanco incluido)
    mask = Image.new("L", (side, side), 0)
    draw = ImageDraw.Draw(mask)
    # Radio tipo Android/iOS (~22.5%)
    r = int(side * 0.225)
    inset = 1
    draw.rounded_rectangle(
        (inset, inset, side - 1 - inset, side - 1 - inset),
        radius=r,
        fill=255,
    )
    mask = mask.filter(ImageFilter.GaussianBlur(0.4))

    out = Image.new("RGBA", (side, side), BLACK)
    out.paste(canvas, (0, 0), mask)
    return out


def export_size(face: Image.Image, size: int, path: Path) -> None:
    out = face.resize((size, size), Image.Resampling.LANCZOS)
    out.convert("RGB").save(path, format="PNG", optimize=True)
    print(f"wrote {path.name} {size}x{size}")


def build_phone_mockup(icon: Image.Image, path: Path) -> None:
    """Maqueta fotorrealista simple: icono EXACTO (píxeles) sobre rejilla oscura."""
    W, H = 720, 1280
    bg = Image.new("RGB", (W, H), (8, 8, 10))
    draw = ImageDraw.Draw(bg)
    # Wallpaper sutil
    for y in range(H):
        v = 8 + int(6 * (y / H))
        draw.line([(0, y), (W, y)], fill=(v, v, v + 2))

    # Rejilla de placeholders (difuminados)
    cell = 132
    gap = 28
    start_x = 48
    start_y = 160
    for row in range(5):
        for col in range(4):
            x = start_x + col * (cell + gap)
            y = start_y + row * (cell + gap + 28)
            if row == 2 and col == 1:
                continue  # hueco para Salomón
            c = 28 + (row * 3 + col) % 5 * 4
            draw.rounded_rectangle(
                (x, y, x + cell, y + cell),
                radius=30,
                fill=(c, c, c + 4),
            )

    # Icono maestro EXACTO en el centro visual
    icon_size = 280
    ico = icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS).convert("RGBA")
    ix = (W - icon_size) // 2
    iy = (H - icon_size) // 2 - 40
    # Sombra suave
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        (ix + 6, iy + 10, ix + icon_size + 6, iy + icon_size + 10),
        radius=64,
        fill=(0, 0, 0, 140),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    bg = Image.alpha_composite(bg.convert("RGBA"), shadow)
    bg.paste(ico, (ix, iy), ico)

    # Label
    d = ImageDraw.Draw(bg)
    d.text((W // 2 - 40, iy + icon_size + 16), "Salomón", fill=(220, 220, 220))

    bg.convert("RGB").save(path, format="PNG", optimize=True)
    print(f"wrote mockup {path.name}")


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"Missing master: {SOURCE}")

    src = Image.open(SOURCE)
    print("source", src.size, src.mode)
    raw = extract_raw_square(src)
    face = mask_to_squircle(raw)

    face.convert("RGB").save(OUT_DIR / "icon-master.png", format="PNG", optimize=True)
    face.convert("RGB").save(OUT_DIR / "master-255542.png", format="PNG", optimize=True)
    print(f"wrote icon-master.png {face.size}")

    for size, name in (
        (180, "apple-touch-icon.png"),
        (192, "icon-192.png"),
        (512, "icon-512.png"),
        (1024, "icon-1024.png"),
    ):
        export_size(face, size, OUT_DIR / name)

    preview = face.resize((1024, 1024), Image.Resampling.LANCZOS)
    preview.convert("RGB").save(OUT_DIR / "icon-halo-preview.png", format="PNG", optimize=True)

    mock_path = OUT_DIR / "maqueta-icono-definitivo.png"
    build_phone_mockup(face, mock_path)
    # Copias visibles
    root_ws = ROOT.parent
    preview.convert("RGB").save(root_ws / "VER-ICONO-MAESTRO-DEFINITIVO.png", format="PNG")
    Image.open(mock_path).save(root_ws / "VER-MAQUETA-DEFINITIVA.png", format="PNG")
    print("copied previews to workspace root")


if __name__ == "__main__":
    main()
