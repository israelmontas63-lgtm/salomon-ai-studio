"""
Icono Adaptativo de Alto Contraste — geometría exacta píxel a píxel.
512: white 16 + gold 12 + face 456 | radius 108 | safe 350
192: white 6 + gold 4 | radius ~40.5→41
Sin push — validación humana primero.
"""
from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "static" / "icons" / "_ref-master.png"
OUT = ROOT / "static" / "icons"
ASSETS = ROOT / "static" / "assets"

SIZE_512, RADIUS_512 = 512, 108
WHITE_512, GOLD_512 = 16, 12
INNER_512 = SIZE_512 - 2 * (WHITE_512 + GOLD_512)  # 456
SAFE_512 = 350

SIZE_192 = 192
WHITE_192, GOLD_192 = 6, 4
RADIUS_192 = int(RADIUS_512 * SIZE_192 / SIZE_512 + 0.5)  # 41 (evitar banker's round)
SAFE_192 = int(round(SAFE_512 * SIZE_192 / SIZE_512))  # 131

WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)


def connected_components(mask: np.ndarray):
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    comps = []
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
                minx, maxx = min(minx, cx), max(maxx, cx)
                miny, maxy = min(miny, cy), max(maxy, cy)
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((nx, ny))
            comps.append((area, minx, miny, maxx, maxy))
    return comps


def extract_ref_icon(path: Path) -> Image.Image:
    im = Image.open(path).convert("RGB")
    rgb = np.asarray(im, dtype=np.int16)
    h, w = rgb.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    white = (
        (rgb[:, :, 0] > 220)
        & (rgb[:, :, 1] > 220)
        & (rgb[:, :, 2] > 220)
        & (np.abs(rgb[:, :, 0].astype(int) - rgb[:, :, 1].astype(int)) < 30)
    )
    best, score = None, -1.0
    for area, minx, miny, maxx, maxy in connected_components(white):
        bw, bh = maxx - minx + 1, maxy - miny + 1
        if bw < 90 or bh < 90:
            continue
        aspect = bw / float(bh)
        if not (0.85 <= aspect <= 1.18):
            continue
        bcx, bcy = (minx + maxx) / 2.0, (miny + maxy) / 2.0
        dist = ((bcx - cx) ** 2 + (bcy - cy) ** 2) ** 0.5
        s = area / (1.0 + dist / 40.0) * (1.0 - abs(1.0 - aspect) * 2)
        if s > score:
            score, best = s, (minx, miny, maxx, maxy)
    if not best:
        raise SystemExit("No se encontró el icono en la referencia")
    minx, miny, maxx, maxy = best
    bcx, bcy = (minx + maxx) / 2.0, (miny + maxy) / 2.0
    side = int(max(maxx - minx + 1, maxy - miny + 1) * 0.99)
    if side % 2:
        side += 1
    half = side / 2.0
    x0, y0 = int(round(bcx - half)), int(round(bcy - half))
    crop = im.crop((x0, y0, x0 + side, y0 + side)).convert("RGBA")
    print(f"ref icon {crop.size} score={score:.1f}")
    return crop


def squircle_mask(size: int, radius: int, inset: int = 0) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    r = max(1, radius - inset)
    d.rounded_rectangle((inset, inset, size - 1 - inset, size - 1 - inset), radius=r, fill=255)
    return m


def sample_gold(ref: Image.Image):
    arr = np.asarray(ref.convert("RGB"), dtype=np.int16)
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    nx = np.maximum(np.abs(xx - cx) / (w / 2.0), np.abs(yy - cy) / (h / 2.0))
    ring = (nx > 0.78) & (nx < 0.96)
    goldish = ring & (arr[:, :, 0] > 120) & (arr[:, :, 1] > 70) & (arr[:, :, 0] > arr[:, :, 2] + 30)
    if goldish.sum() < 30:
        return (232, 196, 90), (196, 155, 55), (120, 88, 30)
    samples = arr[goldish]
    hi = tuple(int(x) for x in np.percentile(samples, 85, axis=0))
    mid = tuple(int(x) for x in np.median(samples, axis=0))
    lo = tuple(int(x) for x in np.percentile(samples, 20, axis=0))
    return hi, mid, lo


def make_gold_ring(size, radius, outer_inset, thickness, hi, mid, lo) -> Image.Image:
    """Anillo dorado continuo (sin hueco negro) con bisel hi/mid/lo.
    outer_inset puede ser white_w-1 para solapar 1px con el aro blanco.
    """
    outer = squircle_mask(size, radius, max(0, outer_inset))
    inner = squircle_mask(size, radius, outer_inset + thickness)
    ring = ImageChops.subtract(outer, inner)

    t_hi = max(1, int(round(thickness * 0.34)))
    t_lo = max(1, int(round(thickness * 0.33)))
    # mid occupies the rest

    band_hi = ImageChops.subtract(
        squircle_mask(size, radius, outer_inset),
        squircle_mask(size, radius, outer_inset + t_hi),
    )
    band_lo = ImageChops.subtract(
        squircle_mask(size, radius, outer_inset + thickness - t_lo),
        inner,
    )
    band_mid = ImageChops.subtract(ring, ImageChops.lighter(band_hi, band_lo))

    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for band, color in ((ring, mid), (band_hi, hi), (band_mid, mid), (band_lo, lo)):
        fill = Image.new("RGBA", (size, size), (*color, 255))
        layer = Image.composite(fill, layer, band)
    return layer


def extract_face_square(ref_icon: Image.Image) -> Image.Image:
    w, h = ref_icon.size
    inset = int(round(min(w, h) * 0.115))
    face = ref_icon.crop((inset, inset, w - inset, h - inset)).convert("RGBA")
    side = max(face.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(face, ((side - face.size[0]) // 2, (side - face.size[1]) // 2), face)
    mask = squircle_mask(side, int(side * 0.22), 0)
    out = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    out.paste(canvas, (0, 0), mask)
    return out


def extract_metal(face: Image.Image) -> Image.Image:
    arr = np.asarray(face.convert("RGBA"), dtype=np.float32)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    gold = (r > 140) & (g > 90) & (r > b + 25)
    for c, v in enumerate((18.0, 18.0, 20.0)):
        ch = arr[:, :, c]
        ch[gold] = v
        arr[:, :, c] = ch
    out = Image.fromarray(arr.astype(np.uint8))
    if out.mode != "RGBA":
        out = out.convert("RGBA")
    return out.filter(ImageFilter.GaussianBlur(0.7))


def extract_emblem(face: Image.Image) -> Image.Image:
    arr = np.asarray(face.convert("RGBA"), dtype=np.int16)
    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    emblem = (a > 200) & (r > 100) & (g > 60) & (r + g > b + 80) & ((r.astype(int) - b.astype(int)) > 25)
    mask_img = Image.fromarray((emblem.astype(np.uint8) * 255), mode="L")
    mask_img = mask_img.filter(ImageFilter.MaxFilter(1))
    mask_img = mask_img.filter(ImageFilter.GaussianBlur(0.35))
    out = Image.new("RGBA", face.size, (0, 0, 0, 0))
    out.paste(face, (0, 0), mask_img)
    bb = out.split()[-1].getbbox()
    if bb:
        out = out.crop(bb)
    return out


def fit_safe(content: Image.Image, canvas_size: int, safe: int) -> Image.Image:
    bb = content.split()[-1].getbbox()
    if bb:
        content = content.crop(bb)
    cw, ch = content.size
    scale = min(safe / cw, safe / ch)
    nw = max(1, min(safe, int(round(cw * scale))))
    nh = max(1, min(safe, int(round(ch * scale))))
    scaled = content.resize((nw, nh), Image.Resampling.LANCZOS)
    layer = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    x = (canvas_size - nw) // 2
    y = (canvas_size - nh) // 2
    layer.paste(scaled, (x, y), scaled)
    print(f"emblem {nw}x{nh} center=({x + nw/2:.1f},{y + nh/2:.1f}) safe={safe}")
    assert nw <= safe and nh <= safe
    return layer


def build_icon(size, radius, white_w, gold_w, safe, emblem, metal, hi, mid, lo) -> Image.Image:
    inner = size - 2 * (white_w + gold_w)
    assert inner == (456 if size == 512 else 172) or size not in (512, 192)

    # Capa blanca
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas = Image.composite(Image.new("RGBA", (size, size), WHITE), canvas, squircle_mask(size, radius, 0))

    # Capa dorada inmediata (solape 2px bajo el blanco → cero filete negro)
    gold = make_gold_ring(size, radius, max(0, white_w - 2), gold_w + 2, hi, mid, lo)
    canvas = Image.alpha_composite(canvas, gold)

    # Fondo metálico interno
    face_box = white_w + gold_w
    metal_r = metal.resize((inner, inner), Image.Resampling.LANCZOS).convert("RGBA")
    metal_bg = Image.new("RGBA", (inner, inner), (12, 12, 12, 255))
    metal_bg = Image.alpha_composite(metal_bg, metal_r)
    imask = squircle_mask(inner, max(1, radius - face_box), 0)
    face_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    tmp = Image.new("RGBA", (inner, inner), (0, 0, 0, 0))
    tmp.paste(metal_bg, (0, 0), imask)
    face_layer.paste(tmp, (face_box, face_box), tmp)
    canvas = Image.alpha_composite(canvas, face_layer)

    # Emblema centrado en safe zone
    canvas = Image.alpha_composite(canvas, fit_safe(emblem, size, safe))

    # Fuera del squircle: transparente (sin esquinas negras en fondos claros)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(canvas, (0, 0), squircle_mask(size, radius, 0))
    print(f"OK {size}px R={radius} white={white_w} gold={gold_w} inner={inner} safe={safe}")
    return out


def verify_rings(icon: Image.Image, white_w: int, gold_w: int) -> None:
    """Comprueba muestreo en el eje medio horizontal."""
    arr = np.asarray(icon.convert("RGB"))
    mid = arr.shape[0] // 2
    # Píxel en el aro blanco (centro del grosor blanco)
    xw = white_w // 2
    xg = white_w + gold_w // 2
    xi = white_w + gold_w + 8
    pw, pg, pi = arr[mid, xw], arr[mid, xg], arr[mid, xi]
    print(f"verify mid-row: white@{xw}={tuple(pw)} gold@{xg}={tuple(pg)} inner@{xi}={tuple(pi)}")


def split_mockup(icon512: Image.Image, path: Path) -> None:
    W, H = 1024, 640
    bg = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(bg)
    d.rectangle((0, 0, W // 2 - 1, H - 1), fill=(0, 0, 0))
    ico = icon512.resize((420, 420), Image.Resampling.LANCZOS).convert("RGBA")
    y = (H - 420) // 2
    bg.paste(ico, (W // 4 - 210, y), ico)
    bg.paste(ico, (3 * W // 4 - 210, y), ico)
    d.text((W // 4 - 36, 28), "NEGRO", fill=(200, 200, 200))
    d.text((3 * W // 4 - 40, 28), "BLANCO", fill=(30, 30, 30))
    bg.save(path, format="PNG", optimize=True)
    print(f"wrote {path.name}")


def save_png(im: Image.Image, path: Path, opaque_black: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if opaque_black:
        bg = Image.new("RGBA", im.size, BLACK)
        bg = Image.alpha_composite(bg, im.convert("RGBA"))
        bg.convert("RGB").save(path, format="PNG", optimize=True)
    else:
        im.convert("RGBA").save(path, format="PNG", optimize=True)
    try:
        print(f"wrote {path.relative_to(ROOT)}")
    except ValueError:
        print(f"wrote {path}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    assert INNER_512 == 456
    assert SIZE_192 - 2 * (WHITE_192 + GOLD_192) == 172

    ref = extract_ref_icon(REF)
    ref.save(OUT / "_ref-icon-crop.png")
    hi, mid, lo = sample_gold(ref)
    print("gold", hi, mid, lo)

    face = extract_face_square(ref)
    metal = extract_metal(face)
    emblem = extract_emblem(face)

    icon512 = build_icon(SIZE_512, RADIUS_512, WHITE_512, GOLD_512, SAFE_512, emblem, metal, hi, mid, lo)
    verify_rings(icon512, WHITE_512, GOLD_512)
    save_png(icon512, OUT / "icon-512.png")
    save_png(icon512, OUT / "icon-master.png")

    icon192 = build_icon(SIZE_192, RADIUS_192, WHITE_192, GOLD_192, SAFE_192, emblem, metal, hi, mid, lo)
    verify_rings(icon192, WHITE_192, GOLD_192)
    save_png(icon192, OUT / "icon-192.png")

    save_png(icon512.resize((180, 180), Image.Resampling.LANCZOS), OUT / "apple-touch-icon.png")
    save_png(icon512.resize((1024, 1024), Image.Resampling.LANCZOS), OUT / "icon-1024.png")

    mock = OUT / "maqueta-split-contraste.png"
    split_mockup(icon512, mock)

    for name in ("icon-192.png", "icon-512.png", "apple-touch-icon.png", "icon-1024.png"):
        save_png(Image.open(OUT / name), ASSETS / name)

    ws = ROOT.parent
    Image.open(mock).save(ws / "VER-ICONO-SPLIT-CONTRASTE.png")
    save_png(icon512, ws / "VER-ICONO-512-ADAPTATIVO.png")
    print("LISTO — sin push. Confirma simetria para desplegar.")


if __name__ == "__main__":
    main()
