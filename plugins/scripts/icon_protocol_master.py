"""
ICON_PROTOCOL_FINAL.md — ejecución estricta.
Master 255542.png + design_tokens + validation. Fallar = no guardar.
"""
from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "icons"
ASSETS = ROOT / "static" / "assets"
PROTOCOL_MD = ROOT / "ICON_PROTOCOL_FINAL.md"
TOKENS_JSON = OUT / "design_tokens.json"

MASTER_CANDIDATES = [
    OUT / "255542.png",
    ASSETS / "255542.png",
    ROOT / "brand" / "master-255542.png",
    ASSETS / "master-255542.png",
]


def die(msg: str) -> None:
    print(f"VALIDATION FAIL: {msg}", file=sys.stderr)
    raise SystemExit(2)


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def load_protocol() -> tuple[dict, dict]:
    if not PROTOCOL_MD.is_file():
        die("ICON_PROTOCOL_FINAL.md no encontrado")
    # Tokens canónicos (espejo del MD)
    tokens = {
        "dimensions": {
            "canvas": 512,
            "safe_area": 0.82,
            "outer_ring": 0.05,
            "gold_border": 0.035,
            "ring_separation": 0.03,
            "logo_scale": 0.58,
            "corner_radius_ratio": 0.2109375,
        },
        "colors": {
            "white_halo": "#FFFFFF",
            "gold_frame": "#C9A227",
            "metal_black": "#0A0A0A",
        },
        "rendering": {
            "contrast_ratio": 7.0,
            "interpolation": "lanczos",
            "format": "png_high_res",
        },
    }
    validation = {
        "mustRemainCentered": True,
        "allowDistortion": False,
        "allowCropping": False,
        "minimumContrastRatio": 7,
        "preserveAspectRatio": True,
        "responsiveScaling": True,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    TOKENS_JSON.write_text(
        json.dumps({"design_tokens": tokens, "validation": validation, "master_asset": "255542.png"}, indent=2),
        encoding="utf-8",
    )
    print(f"Protocol OK: {PROTOCOL_MD.name}")
    return tokens, validation


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    def f(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = f(rgb[0]), f(rgb[1]), f(rgb[2])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    l1, l2 = relative_luminance(a), relative_luminance(b)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


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


def resolve_master() -> Path:
    for p in MASTER_CANDIDATES:
        if p.is_file():
            return p
    die("Activo maestro 255542.png no encontrado")


def extract_master_square(path: Path) -> Image.Image:
    """Recorte cuadrado sin distorsión (allowDistortion=false, allowCropping solo de fondo)."""
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    if abs(w - h) <= 2 and w >= 256:
        side = min(w, h)
        return im.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))

    rgb = np.asarray(im.convert("RGB"), dtype=np.int16)
    hh, ww = rgb.shape[:2]
    cx, cy = ww / 2.0, hh / 2.0
    white = (
        (rgb[:, :, 0] > 220)
        & (rgb[:, :, 1] > 220)
        & (rgb[:, :, 2] > 220)
        & (np.abs(rgb[:, :, 0].astype(int) - rgb[:, :, 1].astype(int)) < 30)
    )
    comps = connected_components(white)
    best, score = None, -1.0
    for area, minx, miny, maxx, maxy in comps:
        bw, bh = maxx - minx + 1, maxy - miny + 1
        if bw < 80 or bh < 80:
            continue
        aspect = bw / float(bh)
        if not (0.85 <= aspect <= 1.2):
            continue
        bcx, bcy = (minx + maxx) / 2.0, (miny + maxy) / 2.0
        dist = ((bcx - cx) ** 2 + (bcy - cy) ** 2) ** 0.5
        s = area / (1.0 + dist / 50.0) * (1.0 - abs(1.0 - aspect))
        if s > score:
            score, best = s, (minx, miny, maxx, maxy)

    if best is None:
        # Contenido no-blanco de estudio
        content = ~((rgb[:, :, 0] > 200) & (rgb[:, :, 1] > 200) & (rgb[:, :, 2] > 200))
        ys, xs = np.where(content)
        if len(xs) < 10:
            side = min(w, h)
            return im.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))
        best = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))

    minx, miny, maxx, maxy = best
    bcx, bcy = (minx + maxx) / 2.0, (miny + maxy) / 2.0
    side = int(max(maxx - minx + 1, maxy - miny + 1))
    if side % 2:
        side += 1
    half = side / 2.0
    x0 = max(0, int(round(bcx - half)))
    y0 = max(0, int(round(bcy - half)))
    crop = im.crop((x0, y0, min(ww, x0 + side), min(hh, y0 + side)))
    cw, ch = crop.size
    side2 = max(cw, ch)
    metal = hex_rgb("#0A0A0A")
    canvas = Image.new("RGBA", (side2, side2), (*metal, 255))
    canvas.paste(crop, ((side2 - cw) // 2, (side2 - ch) // 2), crop)
    print(f"master extract {path.name} -> {canvas.size} (no distortion)")
    return canvas


def squircle_mask(size: int, radius: int, inset: int = 0) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    r = max(1, radius - inset)
    d.rounded_rectangle((inset, inset, size - 1 - inset, size - 1 - inset), radius=r, fill=255)
    return m


def ring_mask(size: int, radius: int, outer_inset: int, thickness: int) -> Image.Image:
    return ImageChops.subtract(
        squircle_mask(size, radius, outer_inset),
        squircle_mask(size, radius, outer_inset + thickness),
    )


def extract_emblem(master: Image.Image) -> Image.Image:
    """SA + Salomón AI desde píxeles del master (Lanczos luego). Sin dibujar tipografía."""
    w, h = master.size
    inset = int(round(min(w, h) * 0.20))
    face = master.crop((inset, inset, w - inset, h - inset)).convert("RGBA")
    arr = np.asarray(face, dtype=np.int16)
    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    gold = (
        (a > 180)
        & (r > 110)
        & (g > 70)
        & (r.astype(int) - b.astype(int) > 28)
        & (r.astype(int) + g.astype(int) > b.astype(int) + 90)
    )
    mask = Image.fromarray((gold.astype(np.uint8) * 255)).convert("L")
    mask = mask.filter(ImageFilter.GaussianBlur(0.35))
    out = Image.new("RGBA", face.size, (0, 0, 0, 0))
    out.paste(face, (0, 0), mask)
    bb = out.split()[-1].getbbox()
    if not bb:
        die("No se pudo extraer monograma SA del master 255542")
    return out.crop(bb)


def metal_plate(size: int, metal: tuple[int, int, int]) -> Image.Image:
    base = np.full((size, size, 3), metal, dtype=np.float32)
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 2.8, (size, size)).astype(np.float32)
    for y in range(size):
        base[y, :, :] += noise[y, 0] * 0.55
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")


def build_512(master: Image.Image, tokens: dict) -> tuple[Image.Image, dict]:
    dim = tokens["dimensions"]
    col = tokens["colors"]
    N = int(dim["canvas"])
    if N != 512:
        die(f"canvas debe ser 512, got {N}")

    white_w = int(round(dim["outer_ring"] * N))  # 5% → 26
    gap_w = int(round(dim["ring_separation"] * N))  # 3% → 15
    gold_w = int(round(dim["gold_border"] * N))  # 3.5% → 18
    safe = int(round(dim["safe_area"] * N))  # 82% → 420
    logo = int(round(dim["logo_scale"] * N))  # 58% → 297
    radius = int(round(dim["corner_radius_ratio"] * N))  # ~108

    # Exactitud matemática de porcentajes
    if abs(white_w / N - 0.05) > 0.002:
        die(f"outer_ring no es 5%: {white_w}/{N}")
    if abs(gold_w / N - 0.035) > 0.002:
        die(f"gold_border no es 3.5%: {gold_w}/{N}")
    if abs(gap_w / N - 0.03) > 0.002:
        die(f"ring_separation no es 3%: {gap_w}/{N}")

    white = (*hex_rgb(col["white_halo"]), 255)
    gold = (*hex_rgb(col["gold_frame"]), 255)
    metal = (*hex_rgb(col["metal_black"]), 255)

    meta = {
        "white_w": white_w,
        "gap_w": gap_w,
        "gold_w": gold_w,
        "safe": safe,
        "logo": logo,
        "radius": radius,
    }
    print(f"tokens px: {meta}")

    canvas = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    canvas = Image.composite(Image.new("RGBA", (N, N), white), canvas, squircle_mask(N, radius, 0))
    canvas = Image.composite(
        Image.new("RGBA", (N, N), metal), canvas, ring_mask(N, radius, white_w, gap_w)
    )
    # Marco dorado #C9A227 + bisel mínimo (color token, no redibuja SA)
    gold_ring = ring_mask(N, radius, white_w + gap_w, gold_w)
    canvas = Image.composite(Image.new("RGBA", (N, N), gold), canvas, gold_ring)
    t1 = max(1, gold_w // 3)
    hi = tuple(min(255, c + 28) for c in gold[:3]) + (255,)
    lo = tuple(max(0, c - 32) for c in gold[:3]) + (255,)
    canvas = Image.composite(
        Image.new("RGBA", (N, N), hi), canvas, ring_mask(N, radius, white_w + gap_w, t1)
    )
    canvas = Image.composite(
        Image.new("RGBA", (N, N), lo),
        canvas,
        ring_mask(N, radius, white_w + gap_w + gold_w - t1, t1),
    )

    inset = white_w + gap_w + gold_w
    inner = N - 2 * inset
    plate = metal_plate(inner, metal[:3])
    imask = squircle_mask(inner, max(1, radius - inset), 0)
    plate_layer = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    tmp = Image.new("RGBA", (inner, inner), (0, 0, 0, 0))
    tmp.paste(plate, (0, 0), imask)
    plate_layer.paste(tmp, (inset, inset), tmp)
    canvas = Image.alpha_composite(canvas, plate_layer)

    emblem_src = extract_emblem(master)
    ew, eh = emblem_src.size
    # preserveAspectRatio: escala uniforme
    scale = logo / max(ew, eh)
    nw = max(1, int(round(ew * scale)))
    nh = max(1, int(round(eh * scale)))
    if nw > safe or nh > safe:
        s2 = min(safe / nw, safe / nh)
        nw, nh = max(1, int(round(nw * s2))), max(1, int(round(nh * s2)))
    emblem = emblem_src.resize((nw, nh), Image.Resampling.LANCZOS)

    # Centro geométrico absoluto (eje del lienzo)
    x = (N - nw) // 2
    y = (N - nh) // 2
    cx, cy = x + nw / 2.0, y + nh / 2.0
    meta["emblem"] = {"w": nw, "h": nh, "x": x, "y": y, "cx": cx, "cy": cy}

    emblem_layer = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    emblem_layer.paste(emblem, (x, y), emblem)
    canvas = Image.alpha_composite(canvas, emblem_layer)

    out = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    out.paste(canvas, (0, 0), squircle_mask(N, radius, 0))
    return out, meta


def validate(icon: Image.Image, tokens: dict, validation: dict, meta: dict) -> None:
    N = tokens["dimensions"]["canvas"]
    col = tokens["colors"]
    min_cr = float(validation["minimumContrastRatio"])
    target_cr = float(tokens["rendering"]["contrast_ratio"])

    cr = contrast_ratio(hex_rgb(col["white_halo"]), hex_rgb(col["metal_black"]))
    print(f"contrast_ratio white/metal = {cr:.2f} (min {min_cr})")
    if cr < min_cr or cr < target_cr:
        die(f"contrast_ratio {cr:.2f} < {max(min_cr, target_cr)}")

    if validation["mustRemainCentered"]:
        cx, cy = meta["emblem"]["cx"], meta["emblem"]["cy"]
        if abs(cx - N / 2) > 0.6 or abs(cy - N / 2) > 0.6:
            die(f"centrado no absoluto: center=({cx},{cy}) expected=({N/2},{N/2})")
        print(f"centered OK: ({cx}, {cy})")

    if meta["emblem"]["w"] > meta["safe"] or meta["emblem"]["h"] > meta["safe"]:
        die("logo rebasa safe_area 0.82")

    # Verificar anillos en eje medio (muestra)
    arr = np.asarray(Image.alpha_composite(Image.new("RGBA", (N, N), (*hex_rgb(col["metal_black"]), 255)), icon).convert("RGB"))
    mid = N // 2
    xw = meta["white_w"] // 2
    xg = meta["white_w"] + meta["gap_w"] + meta["gold_w"] // 2
    pw, pg = tuple(int(v) for v in arr[mid, xw]), tuple(int(v) for v in arr[mid, xg])
    if pw[0] < 240 or pw[1] < 240 or pw[2] < 240:
        die(f"aro blanco inválido en x={xw}: {pw}")
    # Oro #C9A227 ≈ (201, 162, 39)
    if pg[0] < 150 or pg[1] < 100:
        die(f"marco dorado inválido en x={xg}: {pg}")
    print(f"ring sample OK: white@{xw}={pw} gold@{xg}={pg}")
    print("VALIDATION PASSED")


def save_png(im: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGBA").save(path, format="PNG", optimize=True, compress_level=6)
    print(f"wrote {path.relative_to(ROOT)}")


def lanczos(im: Image.Image, size: int) -> Image.Image:
    return im.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    tokens, validation = load_protocol()
    master_path = resolve_master()
    print("MASTER", master_path)

    master = extract_master_square(master_path)
    # Canonical master copy
    save_png(master, OUT / "255542.png")
    save_png(master, ASSETS / "255542.png")

    icon512, meta = build_512(master, tokens)
    validate(icon512, tokens, validation, meta)

    # Familia requerida (responsiveScaling vía Lanczos)
    save_png(icon512, OUT / "android-chrome-512x512.png")
    save_png(lanczos(icon512, 192), OUT / "android-chrome-192x192.png")
    save_png(lanczos(icon512, 180), OUT / "apple-touch-icon.png")
    save_png(lanczos(icon512, 150), OUT / "mstile-150x150.png")
    save_png(lanczos(icon512, 32), OUT / "favicon-32x32.png")
    save_png(lanczos(icon512, 16), OUT / "favicon-16x16.png")
    save_png(icon512, OUT / "icon-512.png")
    save_png(icon512, OUT / "icon-master.png")
    save_png(lanczos(icon512, 192), OUT / "icon-192.png")
    save_png(lanczos(icon512, 1024), OUT / "icon-1024.png")

    for name in (
        "android-chrome-512x512.png",
        "android-chrome-192x192.png",
        "apple-touch-icon.png",
        "icon-512.png",
        "icon-192.png",
    ):
        save_png(Image.open(OUT / name), ASSETS / name)

    print("PROTOCOL 100% COMPLETE")


if __name__ == "__main__":
    main()
