"""In-situ data reductions — one record (image / catalog row) -> one dimensionless J.

The bytes are fetched, reduced, and discarded (evaluate.py records an ACQUIRE
with retained=false so lineage survives without the bytes). This is what lets an
evaluation job walk 5 000 images at an API's rate limit without ever storing the
196 GB.

Image decode: Pillow if installed (JPEG / PNG / anything), else a pure-stdlib
decoder for the uncompressed formats (PGM/PPM P2·P3·P5·P6, 24-bit BMP). An
undecodable record returns (None, reason) and the row is counted as `undefined`
— never dropped.

Every reduction returns a positive float, or None. `fn_params` (from the
.ptorrent evaluation block) tunes: bins, edge_threshold, otsu_floor.
"""
from __future__ import annotations

import math
import struct

try:  # optional
    from PIL import Image as _PILImage  # type: ignore
    _HAVE_PIL = True
except Exception:  # noqa: BLE001
    _HAVE_PIL = False


# ── decode -> luminance ────────────────────────────────────────────────────

def load_luma(data: bytes) -> tuple[int, int, list[int]] | tuple[None, str]:
    """Return (width, height, luma[0..255]) or (None, reason)."""
    if _HAVE_PIL:
        try:
            import io
            im = _PILImage.open(io.BytesIO(data)).convert("L")
            w, h = im.size
            return w, h, list(im.getdata())
        except Exception as e:  # noqa: BLE001
            return None, f"pillow: {e}"
    head = data[:2]
    if head in (b"P2", b"P3", b"P5", b"P6"):
        return _decode_pnm(data)
    if head == b"BM":
        return _decode_bmp(data)
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return None, "PNG needs Pillow (pip install pillow) for the pure-stdlib build"
    return None, "unsupported image format (install pillow for JPEG/PNG/...)"


def _decode_pnm(data: bytes):
    toks: list[bytes] = []
    i, n = 0, len(data)
    while len(toks) < 4 and i < n:
        while i < n and data[i] in b" \t\r\n":
            i += 1
        if i < n and data[i:i + 1] == b"#":
            while i < n and data[i] not in b"\r\n":
                i += 1
            continue
        j = i
        while j < n and data[j] not in b" \t\r\n":
            j += 1
        toks.append(data[i:j])
        i = j
    if len(toks) < 4:
        return None, "truncated PNM header"
    magic = toks[0]
    w, h, maxv = int(toks[1]), int(toks[2]), int(toks[3])
    body = data[i + 1:]
    px = w * h
    if magic in (b"P5", b"P6"):
        chan = 3 if magic == b"P6" else 1
        need = px * chan * (2 if maxv > 255 else 1)
        if len(body) < need:
            return None, "truncated PNM body"
        step = 2 if maxv > 255 else 1
        vals = []
        for k in range(px):
            base = k * chan * step
            if chan == 1:
                v = body[base] if step == 1 else (body[base] << 8 | body[base + 1])
            else:
                r = body[base] if step == 1 else (body[base] << 8 | body[base + 1])
                g = body[base + step] if step == 1 else (body[base + step] << 8 | body[base + step + 1])
                b = body[base + 2 * step] if step == 1 else (body[base + 2 * step] << 8 | body[base + 2 * step + 1])
                v = int(0.299 * r + 0.587 * g + 0.114 * b)
            vals.append(min(255, int(v * 255 / maxv)) if maxv != 255 else v)
        return w, h, vals
    # P2 / P3 ascii
    nums = body.split()
    chan = 3 if magic == b"P3" else 1
    if len(nums) < px * chan:
        return None, "truncated ascii PNM"
    vals = []
    for k in range(px):
        if chan == 1:
            v = int(nums[k])
        else:
            r, g, b = (int(nums[k * 3 + t]) for t in range(3))
            v = int(0.299 * r + 0.587 * g + 0.114 * b)
        vals.append(min(255, int(v * 255 / maxv)) if maxv != 255 else v)
    return w, h, vals


def _decode_bmp(data: bytes):
    if len(data) < 54:
        return None, "truncated BMP"
    offset = struct.unpack_from("<I", data, 10)[0]
    w = struct.unpack_from("<i", data, 18)[0]
    h = struct.unpack_from("<i", data, 22)[0]
    bpp = struct.unpack_from("<H", data, 28)[0]
    if bpp != 24:
        return None, f"BMP {bpp}bpp unsupported (24-bit only in the stdlib build)"
    hh = abs(h)
    row_bytes = (w * 3 + 3) & ~3
    vals = [0] * (w * hh)
    for y in range(hh):
        src = offset + (hh - 1 - y) * row_bytes if h > 0 else offset + y * row_bytes
        for x in range(w):
            p = src + x * 3
            if p + 2 >= len(data):
                return None, "truncated BMP body"
            b, g, r = data[p], data[p + 1], data[p + 2]
            vals[y * w + x] = int(0.299 * r + 0.587 * g + 0.114 * b)
    return w, hh, vals


# ── helpers ────────────────────────────────────────────────────────────────

def _otsu(hist: list[int], total: int) -> int:
    sum_all = sum(i * hist[i] for i in range(256))
    w_b = s_b = 0
    best_t, best_var = 0, -1.0
    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        s_b += t * hist[t]
        m_b = s_b / w_b
        m_f = (sum_all - s_b) / w_f
        var = w_b * w_f * (m_b - m_f) ** 2
        if var > best_var:
            best_var, best_t = var, t
    return best_t


def _hist(luma: list[int]) -> list[int]:
    h = [0] * 256
    for v in luma:
        h[v & 255] += 1
    return h


# ── reductions ─────────────────────────────────────────────────────────────

def img_brightness_ratio(data: bytes, params: dict) -> tuple[float | None, str]:
    dec = load_luma(data)
    if dec[0] is None:
        return None, dec[1]
    w, h, luma = dec
    hist = _hist(luma)
    t = _otsu(hist, len(luma))
    fg = [v for v in luma if v > t]
    bg = [v for v in luma if v <= t]
    if not fg or not bg or sum(bg) == 0:
        return None, "degenerate fg/bg split"
    return (sum(fg) / len(fg)) / max(sum(bg) / len(bg), 1e-9), "ok"


def img_foreground_area_ratio(data: bytes, params: dict) -> tuple[float | None, str]:
    dec = load_luma(data)
    if dec[0] is None:
        return None, dec[1]
    _, _, luma = dec
    t = _otsu(_hist(luma), len(luma))
    fg = sum(1 for v in luma if v > t)
    bg = len(luma) - fg
    if bg == 0:
        return None, "no background"
    return fg / bg, "ok"


def img_entropy_ratio(data: bytes, params: dict) -> tuple[float | None, str]:
    dec = load_luma(data)
    if dec[0] is None:
        return None, dec[1]
    _, _, luma = dec
    bins = int(params.get("bins", 256))
    h = [0] * bins
    for v in luma:
        h[min(bins - 1, v * bins // 256)] += 1
    n = len(luma)
    ent = -sum((c / n) * math.log2(c / n) for c in h if c)
    return ent / math.log2(bins), "ok"     # in [0,1] -> mostly sigma inf/half


def img_edge_density_ratio(data: bytes, params: dict) -> tuple[float | None, str]:
    dec = load_luma(data)
    if dec[0] is None:
        return None, dec[1]
    w, h, luma = dec
    if w < 3 or h < 3:
        return None, "image too small for Sobel"
    thr = float(params.get("edge_threshold", 48))
    edges = 0
    total = (w - 2) * (h - 2)
    for y in range(1, h - 1):
        row0 = (y - 1) * w
        row1 = y * w
        row2 = (y + 1) * w
        for x in range(1, w - 1):
            gx = (luma[row0 + x + 1] + 2 * luma[row1 + x + 1] + luma[row2 + x + 1]
                  - luma[row0 + x - 1] - 2 * luma[row1 + x - 1] - luma[row2 + x - 1])
            gy = (luma[row2 + x - 1] + 2 * luma[row2 + x] + luma[row2 + x + 1]
                  - luma[row0 + x - 1] - 2 * luma[row0 + x] - luma[row0 + x + 1])
            if math.hypot(gx, gy) >= thr:
                edges += 1
    if edges == 0 or edges == total:
        return None, "degenerate edge map"
    return edges / (total - edges), "ok"


def img_gradient_energy_ratio(data: bytes, params: dict) -> tuple[float | None, str]:
    dec = load_luma(data)
    if dec[0] is None:
        return None, dec[1]
    w, h, luma = dec
    if w < 2 or h < 2:
        return None, "image too small"
    grad = 0.0
    tot = sum(luma) or 1.0
    for y in range(h - 1):
        for x in range(w - 1):
            i = y * w + x
            grad += abs(luma[i + 1] - luma[i]) + abs(luma[i + w] - luma[i])
    return grad / tot, "ok"


IMAGE_FN = {
    "img_brightness_ratio": img_brightness_ratio,
    "img_foreground_area_ratio": img_foreground_area_ratio,
    "img_entropy_ratio": img_entropy_ratio,
    "img_edge_density_ratio": img_edge_density_ratio,
    "img_gradient_energy_ratio": img_gradient_energy_ratio,
}

# short human descriptions for the wizard
IMAGE_FN_HELP = {
    "img_brightness_ratio":       "mean(foreground) / mean(background), Otsu split — bright subject on dark field ⇒ large J",
    "img_foreground_area_ratio":  "foreground px / background px — how much of the frame the subject fills",
    "img_entropy_ratio":          "Shannon entropy(histogram) / log2(bins) — texture / information density, in [0,1]",
    "img_edge_density_ratio":     "edge px / interior px (Sobel > threshold) — structural busyness",
    "img_gradient_energy_ratio":  "Σ|∇I| / Σ I — total local contrast normalised by brightness",
}


def reduce_image(fn: str, data: bytes, params: dict | None = None):
    f = IMAGE_FN.get(fn)
    if not f:
        return None, f"unknown image reduction {fn!r}"
    return f(data, params or {})
