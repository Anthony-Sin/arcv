"""A curated library of reusable, deterministic HUD primitives.

These are the genuinely reusable vector/text building blocks distilled from five
recreated reference HUDs (``examples/refs/refN_layout.py``): warning/hazard
badges, barcodes and spectrum strips, radar gauges and sweep wedges, organic
contour maps, and wireframe spheres/terrain/face meshes.

Every function takes a **drawing surface** ``d`` as its FIRST argument — a
:class:`arcv.overlay.Draw` (or any duck-typed object exposing the same flat
interface: ``line / poly / rect / rrect / rrect_fill / ring / disc / tri /
tri_fill / text / text_width``). Colors are **RGBA floats in [0, 1]**;
coordinates are **pixels** with a top-left origin. All geometry is
deterministic (seeded/fixed formulas, no randomness).

Usage::

    from arcv.overlay import Overlay, Draw, hud_kit
    ov = Overlay(ctx, (1280, 720)); d = Draw(ov)
    ov.begin()
    hud_kit.radial_gauge(d, 200, 200, 90, 0.62, (0.9, 0.45, 0.15, 1), needle_deg=58)
    hud_kit.wireframe_sphere(d, 640, 360, 120, (0, 1, 1, 1), vortex=True)
    ov.render(0.0, target=fbo)
"""

from __future__ import annotations

import math

_TAU = math.pi * 2.0

__all__ = [
    # icons / badges
    "warning_triangle",
    "biohazard",
    "radiation_trefoil",
    "hexagon",
    "hex_badge",
    "crescent",
    # textures / strips
    "hazard_stripes",
    "barcode",
    "waveform",
    "spectrum_bar",
    "segmented_bar",
    # gauges / radar
    "tick_ring",
    "radial_gauge",
    "sweep_wedge",
    "contour_map",
    # wireframe
    "wireframe_sphere",
    "wireframe_terrain",
    "face_mesh",
]


# ---------------------------------------------------------------- helpers
def _fade(c, a):
    """Return `c` with its alpha multiplied by `a`."""
    return (c[0], c[1], c[2], c[3] * a)


def _clip_seg(x0, y0, x1, y1, cx0, cy0, cx1, cy1):
    """Liang-Barsky clip of a segment to an axis-aligned rect.

    Returns ``(ax, ay, bx, by)`` for the clipped segment, or ``None`` if the
    segment lies entirely outside the rect. (Ported from the ref layouts.)
    """
    dx = x1 - x0
    dy = y1 - y0
    p = [-dx, dx, -dy, dy]
    q = [x0 - cx0, cx1 - x0, y0 - cy0, cy1 - y0]
    u0, u1 = 0.0, 1.0
    for pi, qi in zip(p, q):
        if pi == 0:
            if qi < 0:
                return None
        else:
            r = qi / pi
            if pi < 0:
                if r > u1:
                    return None
                if r > u0:
                    u0 = r
            else:
                if r < u0:
                    return None
                if r < u1:
                    u1 = r
    return (x0 + u0 * dx, y0 + u0 * dy, x0 + u1 * dx, y0 + u1 * dy)


def _diamond(d, cx, cy, r, c, w=1.4, fill=False):
    """A small diamond (rotated square) outline or fill."""
    p = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    if fill:
        d.tri_fill(p[0], p[1], p[2], c)
        d.tri_fill(p[0], p[2], p[3], c)
    else:
        d.poly(p, c, w, closed=True)


# ============================================================ ICONS / BADGES
def warning_triangle(d, cx, cy, r, color, width=2.0):
    """Equilateral warning triangle with a ``!`` inside (ported from ref1)."""
    p0 = (cx, cy - r)
    p1 = (cx - r * 0.90, cy + r * 0.72)
    p2 = (cx + r * 0.90, cy + r * 0.72)
    d.tri(p0, p1, p2, color, width)
    # exclamation mark
    d.rect(cx, cy - r * 0.28, cx, cy + r * 0.28, color, max(2.0, r * 0.16))
    d.disc(cx, cy + r * 0.48, max(1.6, r * 0.10), color)


def biohazard(d, cx, cy, r, color):
    """Biohazard trefoil: three overlapping rings around a hub (ported from
    ref2 — the outline form works over the additive glow pipeline)."""
    w = max(1.2, r * 0.10)
    for k in range(3):
        a = -math.pi / 2 + k * (_TAU / 3)
        rx = cx + math.cos(a) * r * 0.62
        ry = cy + math.sin(a) * r * 0.62
        d.ring(rx, ry, r * 0.52, color, w)
    d.ring(cx, cy, r * 0.30, color, w)
    d.disc(cx, cy, r * 0.10, color)


def radiation_trefoil(d, cx, cy, r, color):
    """Radiation symbol: three filled wedges + a central hub (ported from
    ref2)."""
    d.disc(cx, cy, r * 0.22, color)
    for k in range(3):
        a0 = -math.pi / 2 + k * (_TAU / 3) - 0.55
        a1 = a0 + 1.10
        n = 6
        for i in range(n):
            b0 = a0 + (a1 - a0) * i / n
            b1 = a0 + (a1 - a0) * (i + 1) / n
            p0 = (cx + math.cos(b0) * r * 0.34, cy + math.sin(b0) * r * 0.34)
            p1 = (cx + math.cos(b0) * r, cy + math.sin(b0) * r)
            p2 = (cx + math.cos(b1) * r, cy + math.sin(b1) * r)
            p3 = (cx + math.cos(b1) * r * 0.34, cy + math.sin(b1) * r * 0.34)
            d.tri_fill(p0, p1, p2, color)
            d.tri_fill(p0, p2, p3, color)


def hexagon(d, cx, cy, r, color, width=2.0, flat_top=True, fill=None):
    """A hexagon outline (optionally filled). ``flat_top=True`` orients a flat
    edge at the top (ported from ref1). If ``fill`` is given, the interior is
    filled with that color via a triangle fan before the outline."""
    pts = []
    for k in range(6):
        a = math.pi / 6 + k * math.pi / 3 if flat_top else k * math.pi / 3
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    if fill is not None:
        for k in range(1, 5):
            d.tri_fill(pts[0], pts[k], pts[k + 1], fill)
    d.poly(pts, color, width, closed=True)
    return pts


def hex_badge(d, cx, cy, r, label, color, width=2.0):
    """A hexagon (flat-top) with a faint inner hex and a centered number/label
    inside (ported/generalized from ref5's ``hex_badge``)."""
    pts = []
    for k in range(6):
        a = math.pi / 6 + k * _TAU / 6.0
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    d.poly(pts, color, width, closed=True)
    # inner faint hex
    pts2 = [(cx + (p[0] - cx) * 0.8, cy + (p[1] - cy) * 0.8) for p in pts]
    d.poly(pts2, _fade(color, 0.4), max(1.0, width * 0.6), closed=True)
    d.text(str(label), cx, cy - r * 0.42, r * 0.85, color, align="center")


def crescent(d, cx, cy, r, color, width=2.0):
    """A gridded globe circle with a filled crescent moon inside (ported from
    ref1's ``crescent_globe``). The crescent is a solid disc minus an offset
    background disc — the "background" here is the interior fill color, so the
    knockout reads cleanly only over the disc; drawn as a single-color outline
    it still gives the classic gridded-globe-plus-crescent glyph."""
    d.ring(cx, cy, r, color, width)
    # latitude / longitude chords
    for k in (-0.6, -0.3, 0.0, 0.3, 0.6):
        yy = cy + k * r
        hw = math.sqrt(max(0.0, r * r - (k * r) ** 2))
        d.line(cx - hw, yy, cx + hw, yy, color, width * 0.55)
    for k in (-0.6, -0.3, 0.0, 0.3, 0.6):
        xx = cx + k * r
        hh = math.sqrt(max(0.0, r * r - (k * r) ** 2))
        d.line(xx, cy - hh, xx, cy + hh, color, width * 0.55)
    # filled crescent moon: a bright arc built from a stack of chords
    mr = r * 0.62
    mcx, mcy = cx - r * 0.10, cy
    ox = mr * 0.55  # x-offset of the knock-out disc
    steps = 26
    for i in range(steps + 1):
        yy = mcy - mr + (2 * mr) * i / steps
        dy = yy - mcy
        # left edge of the moon disc
        half = math.sqrt(max(0.0, mr * mr - dy * dy))
        xl = mcx - half
        # left edge of the offset knock-out disc
        dy2 = yy - mcy + mr * 0.08
        half2 = math.sqrt(max(0.0, (mr * 0.95) ** 2 - dy2 * dy2))
        xr = (mcx + ox) - half2
        if xr > xl:
            d.line(xl, yy, xr, yy, color, (2.0 * mr / steps) + 1.0)


# ============================================================ TEXTURES / STRIPS
def hazard_stripes(d, x0, y0, x1, y1, color, gap=14.0, width=6.0):
    """Diagonal caution stripes clipped to the rect ``[x0,y0]-[x1,y1]``.

    Stripes run up-right and are clipped with Liang-Barsky so nothing spills
    outside the box (ported from ref1/ref2). ``gap`` is the center-to-center
    spacing between stripes; ``width`` is stroke width.
    """
    bw = x1 - x0
    bh = y1 - y0
    step = gap
    off = -bh
    while off < bw + bh:
        ax, ay = x0 + off, y1
        bx, by = x0 + off + bh, y0
        seg = _clip_seg(ax, ay, bx, by, x0, y0, x1, y1)
        if seg:
            d.line(seg[0], seg[1], seg[2], seg[3], color, width)
        off += step


def barcode(d, x, y, w, h, color, seed=0, vertical=True):
    """A deterministic barcode of variable-width bars (ported from ref1/ref2).

    ``(x, y)`` is the top-left; ``w`` x ``h`` the extent. ``vertical=True``
    draws vertical bars marching left->right (the usual barcode look);
    ``vertical=False`` draws horizontal bars marching top->bottom.
    """
    r = (seed + 1) * 2654435761 & 0xFFFFFFFF
    if vertical:
        pos, end = x, x + w
        while pos < end:
            r = (1103515245 * r + 12345) & 0xFFFFFFFF
            bw = 1.0 + (r >> 16) % 4
            r = (1103515245 * r + 12345) & 0xFFFFFFFF
            g = 1.0 + (r >> 18) % 3
            if pos + bw > end:
                bw = end - pos
            if bw > 0:
                d.rect(pos + bw * 0.5, y, pos + bw * 0.5, y + h, color, bw)
            pos += bw + g
    else:
        pos, end = y, y + h
        while pos < end:
            r = (1103515245 * r + 12345) & 0xFFFFFFFF
            bh = 1.0 + (r >> 16) % 4
            r = (1103515245 * r + 12345) & 0xFFFFFFFF
            g = 1.0 + (r >> 18) % 3
            if pos + bh > end:
                bh = end - pos
            if bh > 0:
                d.rect(x, pos + bh * 0.5, x + w, pos + bh * 0.5, color, bh)
            pos += bh + g


def waveform(d, x, y, w, h, color, bars=48, seed=0):
    """Symmetric audio bars about the horizontal midline (ported from ref1).

    ``(x, y)`` top-left, ``w`` x ``h`` extent; ``bars`` mirrored vertical bars
    with a sine envelope taller in the middle.
    """
    cy = y + h * 0.5
    amp = h * 0.5
    dx = w / bars
    lw = max(1.0, dx * 0.55)
    r = (seed + 1) * 2246822519 & 0xFFFFFFFF
    for i in range(bars):
        r = (1103515245 * r + 12345) & 0xFFFFFFFF
        env = math.sin(i / bars * math.pi) ** 0.6
        bh = (0.15 + ((r >> 16) % 100) / 100.0) * amp * env
        bx = x + i * dx
        d.line(bx, cy - bh, bx, cy + bh, color, lw)


# full-saturation rainbow for the chromatic spectrum bar
_RAINBOW = [
    (1.0, 0.15, 0.15, 1.0),   # red
    (1.0, 0.5, 0.1, 1.0),     # orange
    (1.0, 0.9, 0.1, 1.0),     # yellow
    (0.3, 1.0, 0.2, 1.0),     # green
    (0.1, 1.0, 0.9, 1.0),     # cyan
    (0.2, 0.5, 1.0, 1.0),     # blue
    (0.7, 0.25, 1.0, 1.0),    # violet
]


def spectrum_bar(d, x, y, w, h, segments=8, vertical=True, color=None):
    """A chromatic (rainbow) bar of stacked segments cycling the spectrum
    (ported from ref5). ``vertical=True`` stacks segments top->bottom across
    ``h``; ``vertical=False`` marches them left->right across ``w``. If
    ``color`` is given, every segment uses it (a mono progress strip);
    otherwise the rainbow palette is cycled. ``(x, y)`` is the top-left."""
    for i in range(segments):
        col = color if color is not None else _RAINBOW[i % len(_RAINBOW)]
        if vertical:
            seg = h / segments
            yy0 = y + i * seg
            yy1 = yy0 + seg - max(1.0, seg * 0.12)
            d.line(x + w * 0.5, yy0, x + w * 0.5, yy1, col, w)
        else:
            seg = w / segments
            xx0 = x + i * seg
            xx1 = xx0 + seg - max(1.0, seg * 0.12)
            d.line(xx0, y + h * 0.5, xx1, y + h * 0.5, col, h)


def segmented_bar(d, x, y, w, h, count, color, filled=None):
    """A row of ``count`` segments across ``w`` (ported from ref3). Outlined
    segments by default; indices in the ``filled`` iterable are drawn as solid
    filled blocks. ``(x, y)`` is the top-left."""
    hot = frozenset(filled) if filled is not None else frozenset()
    gap = 2.0
    sw = (w - gap * (count - 1)) / count
    for i in range(count):
        x0 = x + i * (sw + gap)
        x1 = x0 + sw
        if i in hot:
            d.rrect_fill(x0, y, x1, y + h, 1.0, color)
        else:
            d.rect(x0, y, x1, y + h, color, 1.0)


# ============================================================ GAUGES / RADAR
def tick_ring(d, cx, cy, r, count, length, color, width=1.0,
              major_every=0, major_length=0.0):
    """Radial tick marks around a circle, pointing inward (ported from ref3).

    ``count`` ticks of ``length`` px. If ``major_every > 0``, every Nth tick is
    drawn ``major_length`` px long instead (major/minor tick scale).
    """
    for i in range(count):
        a = _TAU * (i / count)
        ca, sa = math.cos(a), math.sin(a)
        ln = length
        if major_every and (i % major_every == 0):
            ln = major_length or length * 2.0
        r0, r1 = r, r - ln
        d.line(cx + ca * r0, cy + sa * r0, cx + ca * r1, cy + sa * r1, color, width)


def radial_gauge(d, cx, cy, r, value, color, needle_deg=None, hub=True):
    """A circular status gauge (ported/generalized from ref3).

    Draws an outer boundary ring, an inner tick ring, a couple of faint
    concentric rings, and an ORANGE-style progress arc across the top spanning
    ``value`` (0..1) of a 240deg sweep. If ``needle_deg`` is given, a thin
    tapered needle points at that angle (degrees, screen coords: 0=right,
    90=down). ``hub=True`` draws a diamond hub at the center.
    """
    value = max(0.0, min(1.0, value))
    faint = _fade(color, 0.35)
    hair = _fade(color, 0.22)
    d.ring(cx, cy, r, faint, 1.3)
    tick_ring(d, cx, cy, r * 0.985, 90, r * 0.035, hair, 1.0)
    tick_ring(d, cx, cy, r * 0.985, 18, r * 0.07, faint, 1.2)
    for rr in (0.80, 0.60):
        d.ring(cx, cy, r * rr, hair, 1.0)
    # progress arc across the top: 240deg sweep from -150deg..+90deg of it
    a_start = math.radians(-150.0)
    a_end = a_start + math.radians(240.0) * value
    d.ring(cx, cy, r * 0.90, color, 2.4, a0=a_start, a1=a_end)
    # optional needle
    if needle_deg is not None:
        na = math.radians(needle_deg)
        ca, sa = math.cos(na), math.sin(na)
        perp = (-sa, ca)
        tip = (cx + ca * r * 0.80, cy + sa * r * 0.80)
        bw = r * 0.028
        b0 = (cx + perp[0] * bw, cy + perp[1] * bw)
        b1 = (cx - perp[0] * bw, cy - perp[1] * bw)
        d.tri_fill(b0, b1, tip, color)
        d.line(cx, cy, tip[0], tip[1], color, 1.6)
        tail = (cx - ca * r * 0.16, cy - sa * r * 0.16)
        d.tri_fill(b0, b1, tail, _fade(color, 0.9))
    if hub:
        hr = r * 0.075
        _diamond(d, cx, cy, hr * 1.7, faint, w=1.3)
        _diamond(d, cx, cy, hr, color, fill=True)


def sweep_wedge(d, cx, cy, r, a0, a1, color):
    """A filled translucent pie slice from angle ``a0`` to ``a1`` (radians),
    built as a triangle fan, with brighter leading/trailing edges (ported from
    ref3). Use a low-alpha ``color`` for the classic radar sweep look."""
    edge = _fade(color, min(1.0, color[3] * 3.5))
    n = 26
    prev = None
    for i in range(n + 1):
        a = a0 + (a1 - a0) * (i / n)
        p = (cx + math.cos(a) * r, cy + math.sin(a) * r)
        if prev is not None:
            d.tri_fill((cx, cy), prev, p, color)
        prev = p
    d.line(cx, cy, cx + math.cos(a0) * r, cy + math.sin(a0) * r, _fade(edge, 0.6), 1.4)
    d.line(cx, cy, cx + math.cos(a1) * r, cy + math.sin(a1) * r, edge, 1.8)


def contour_map(d, cx, cy, r, color, seed=0, systems=3):
    """Organic nested topographic contour loops, clipped to a disc of radius
    ``r`` (ported from the reworked ref3 ``contour_map``).

    Smooth low-frequency loops (harmonics 1..4, small amplitude) sampled at many
    angles so each reads as a gently meandering coastline — NOT a geodesic web.
    ``systems`` landmasses (each several nested elevation bands) plus small
    islands. ``seed`` deterministically rotates the phase table for variety.
    """
    N = 160
    ph0 = (seed % 8) * 0.5

    def loop(base_r, cxx, cyy, harmonics, col, w):
        pts = []
        for i in range(N):
            a = _TAU * (i / N)
            rad = base_r
            for (k, ph, af) in harmonics:
                rad += base_r * af * math.sin(a * k + ph + ph0)
            pts.append((cxx + math.cos(a) * rad, cyy + math.sin(a) * rad))
        d.poly(pts, col, w, closed=True)

    def landmass(cxx, cyy, r0, harm_base, levels, alpha0):
        for lvl in range(levels):
            frac = 1.0 - lvl / (levels + 0.6)
            harm = [(k, ph + lvl * 0.35, af) for (k, ph, af) in harm_base]
            a = alpha0 * (0.55 + 0.45 * (1.0 - lvl / levels))
            loop(r0 * frac, cxx, cyy, harm, _fade(color, a), 0.9)

    # deterministic per-system placement (upper-left heavy, like the reference)
    configs = [
        (-0.16, -0.14, 0.72, [(1, 0.5, 0.12), (2, 2.3, 0.09), (3, 4.1, 0.06), (4, 1.2, 0.04)], 11, 0.62),
        (0.34, 0.10, 0.40, [(1, 3.0, 0.14), (2, 0.8, 0.08), (3, 2.5, 0.05), (4, 5.0, 0.035)], 8, 0.5),
        (-0.40, 0.34, 0.34, [(1, 1.7, 0.13), (2, 4.4, 0.09), (3, 0.6, 0.055), (4, 2.9, 0.03)], 7, 0.46),
        (0.20, -0.36, 0.30, [(1, 2.4, 0.13), (2, 1.1, 0.08), (3, 3.3, 0.05), (4, 0.7, 0.03)], 6, 0.44),
        (0.46, -0.28, 0.24, [(1, 0.9, 0.14), (2, 3.7, 0.09), (3, 1.9, 0.05), (4, 4.4, 0.03)], 5, 0.42),
    ]
    for i in range(max(1, min(systems, len(configs)))):
        dx, dy, rr, harm, lv, a0 = configs[i]
        landmass(cx + r * dx, cy + r * dy, r * rr, harm, lv, a0)

    # small islands / atolls (2-3 bands each)
    harm_i = [(1, 2.0, 0.16), (2, 5.1, 0.10), (3, 1.4, 0.06)]
    for (dx, dy, rr, ph) in ((0.10, -0.42, 0.14, 0.0), (0.46, -0.30, 0.11, 1.3),
                             (-0.10, 0.44, 0.12, 2.6), (0.30, 0.42, 0.10, 3.9),
                             (-0.44, -0.06, 0.11, 5.2)):
        h = [(k, p + ph, af) for (k, p, af) in harm_i]
        landmass(cx + r * dx, cy + r * dy, r * rr, h, 3, 0.44)

    # tiny single-loop reef spots
    for (dx, dy, rr, ph) in ((-0.22, -0.30, 0.05, 0.7), (0.20, 0.20, 0.045, 2.1),
                             (0.42, 0.02, 0.04, 3.5), (-0.30, 0.12, 0.045, 4.8),
                             (0.06, -0.18, 0.04, 1.1)):
        h = [(1, ph, 0.18), (2, ph + 2.0, 0.10)]
        loop(r * rr, cx + r * dx, cy + r * dy, h, _fade(color, 0.34), 0.9)


# ============================================================ WIREFRAME
def wireframe_sphere(d, cx, cy, r, color, vortex=False, lat=8, lon=12):
    """A sphere drawn as a latitude/longitude grid (ported from ref2).

    ``vortex=False`` draws a plain tilted globe with ``lat`` latitude rings and
    ``lon`` meridians. ``vortex=True`` collapses the grid toward a small
    off-center throat and spirals the meridians inward (a swirling whirlpool /
    black-hole funnel), ignoring ``lat``/``lon`` in favor of a denser tuned mesh.
    """
    w = max(0.8, r * 0.009)
    if not vortex:
        _plain_sphere(d, cx, cy, r, color, w, lat, lon)
    else:
        _vortex_sphere(d, cx, cy, r, color, w)


def _plain_sphere(d, cx, cy, r, c, w, n_lat, n_lon):
    tilt = 0.34
    rings = []
    for li in range(1, n_lat):
        phi = math.pi * li / n_lat
        yy = cy - r * math.cos(phi)
        rw = r * math.sin(phi)
        rh = r * tilt * math.sin(phi)
        rings.append((cx, yy, rw, rh))
        d.poly([(cx + math.cos(a) * rw, yy + math.sin(a) * rh)
                for a in [_TAU * k / 48 for k in range(49)]], c, w)
    top = (cx, cy - r)
    bot = (cx, cy + r)
    for lo in range(n_lon):
        a = _TAU * lo / n_lon
        pts = [top] + [(ccx + math.cos(a) * rw, ccy + math.sin(a) * rh)
                       for (ccx, ccy, rw, rh) in rings] + [bot]
        d.poly(pts, c, w)


def _vortex_sphere(d, cx, cy, r, c, w):
    n_ring = 26
    n_spoke = 22
    tilt = 0.40
    tx, ty = cx - r * 0.16, cy - r * 0.20
    throat_rw = r * 0.08

    def ring_at(u):
        rw = throat_rw + (r - throat_rw) * (1.0 - u) ** 1.35
        rh = rw * tilt
        rim_cx = cx + r * 0.02
        rim_cy = cy + r * 0.16
        ccx = rim_cx + (tx - rim_cx) * (u ** 1.15)
        ccy = rim_cy + (ty - rim_cy) * (u ** 0.9)
        spin = (u ** 1.35) * 6.8
        return ccx, ccy, rw, rh, spin

    rings = []
    for li in range(n_ring + 1):
        u = li / n_ring
        ccx, ccy, rw, rh, spin = ring_at(u)
        rings.append((ccx, ccy, rw, rh, spin))
        pts = [(ccx + math.cos(a + spin) * rw, ccy + math.sin(a + spin) * rh)
               for a in [_TAU * k / 72 for k in range(73)]]
        d.poly(pts, _fade(c, 1.0 - 0.25 * u), w)

    for lo in range(n_spoke):
        a0 = _TAU * lo / n_spoke
        pts = [(ccx + math.cos(a0 + spin) * rw, ccy + math.sin(a0 + spin) * rh)
               for (ccx, ccy, rw, rh, spin) in rings]
        d.poly(pts, c, w * 0.8)

    d.poly([(cx + math.cos(a) * r, cy + math.sin(a) * r)
            for a in [_TAU * k / 80 for k in range(81)]], c, w)
    for yy in (cy - r * 0.5, cy + r * 0.35):
        rw = math.sqrt(max(0.0, r * r - (yy - cy) ** 2))
        d.poly([(cx + math.cos(a) * rw, yy + math.sin(a) * rw * tilt)
                for a in [_TAU * k / 60 for k in range(61)]], _fade(c, 0.5), w)


def _terrain_height(i, j):
    """Deterministic pseudo-height field: a broad mountain range (ported from
    ref2). i=across(0..1), j=depth(0..1, 1=far)."""
    peak = math.exp(-(((i - 0.44) * 3.8) ** 2 + ((j - 0.64) * 2.8) ** 2)) * 1.35
    peaks = [
        (0.16, 0.42, 3.6, 3.4, 0.55),
        (0.30, 0.55, 4.0, 3.2, 0.62),
        (0.60, 0.50, 3.8, 3.2, 0.68),
        (0.74, 0.62, 3.6, 2.8, 0.60),
        (0.88, 0.45, 4.2, 3.6, 0.50),
    ]
    acc = peak
    for (pi, pj, wi, wj, amp) in peaks:
        acc += math.exp(-(((i - pi) * wi) ** 2 + ((j - pj) * wj) ** 2)) * amp
    ripple = (math.sin(i * 9.0 + 0.5) * math.sin(j * 8.0 + 1.3) * 0.55
              + math.sin(i * 15.0 + 1.1) * math.sin(j * 13.0 + 2.1) * 0.35
              + math.sin(i * 27.0 + j * 8.0) * 0.18)
    base = 0.30 + 0.16 * math.sin(i * 6.0 + 0.7) + 0.10 * math.sin(i * 11.0 + j * 4.0)
    foot = 0.14 * (1.0 - j) * (0.5 + 0.5 * math.sin(i * 17.0 + 1.0))
    return acc + 0.16 * ripple + base + foot


def wireframe_terrain(d, x, y, w, h, color, cols=48, rows=32, seed=0):
    """A tilted 3D mountain/terrain mesh drawn as row + column polylines in
    perspective (ported from ref2). ``(x, y)`` is the top-left of the footprint,
    ``w`` x ``h`` its extent. ``seed`` shifts the height field phase for
    variety; ``cols``/``rows`` control the mesh density."""
    NX = max(2, cols)
    NY = max(2, rows)
    depth_dx = w * 0.07
    depth_dy = h * 0.40
    amp = h * 0.34
    z0 = 0.30
    phase = (seed % 8) * 0.13

    def proj(i, j):
        u = i / (NX - 1)
        v = j / (NY - 1)
        conv = 1.0 - v * 0.12
        px = x + w * 0.03 + (u - 0.5) * w * conv + 0.5 * w + v * depth_dx
        base_y = y + h - v * depth_dy
        height = _terrain_height(u + phase * 0.0, v) - z0 + math.sin(u * 5.0 + phase) * 0.05 * phase
        py = base_y - height * amp
        return (px, py)

    grid = [[proj(i, j) for i in range(NX)] for j in range(NY)]
    for j in range(NY - 1, -1, -1):
        d.poly(grid[j], color, 1.0)
    for i in range(NX):
        d.poly([grid[j][i] for j in range(NY)], color, 1.0)


def face_mesh(d, cx, cy, w, h, color, markers=True):
    """A triangulated FACE MESH that reads unmistakably as a face (ported from
    the reworked ref5 ``face_mesh``).

    An oval face contour + symmetric eye/brow/nose/mouth clusters wired into a
    triangle web, with node dots at every anchor. ``(cx, cy)`` is the face
    center, ``w`` x ``h`` its extent. ``markers=True`` overlays small square
    feature markers over the eyes/nose/mouth.
    """
    hw, hh = w * 0.5, h * 0.5

    def P(nx, ny):
        return (cx + nx * hw, cy + ny * hh)

    # oval face contour (14 pts, tapered to a chin)
    oval = []
    n_oval = 14
    for i in range(n_oval):
        a = -math.pi / 2 + i * _TAU / n_oval
        ox = math.cos(a) * 0.78
        oy = math.sin(a)
        if oy > 0:
            ox *= (1.0 - 0.28 * oy)
            oy = oy * 1.02
        else:
            ox *= (1.0 + 0.04 * oy)
            oy = oy * 0.88
        oval.append(P(ox, oy))
    chin = P(0.0, 0.98)

    brow_l = P(-0.36, -0.34)
    brow_c = P(0.0, -0.40)
    brow_r = P(0.36, -0.34)
    eye_l = P(-0.32, -0.18)
    eye_r = P(0.32, -0.18)
    eye_li = P(-0.14, -0.16)
    eye_ri = P(0.14, -0.16)
    nose_top = P(0.0, -0.10)
    nose_mid = P(0.0, 0.10)
    nose_tip = P(0.0, 0.26)
    nose_l = P(-0.10, 0.24)
    nose_r = P(0.10, 0.24)
    cheek_l = P(-0.44, 0.14)
    cheek_r = P(0.44, 0.14)
    mouth_l = P(-0.22, 0.48)
    mouth_c = P(0.0, 0.50)
    mouth_r = P(0.22, 0.48)
    jaw_l = P(-0.40, 0.52)
    jaw_r = P(0.40, 0.52)

    d.poly(oval, _fade(color, 0.65), 1.2, closed=True)

    edges = [
        (brow_l, brow_c), (brow_c, brow_r),
        (brow_l, eye_l), (brow_r, eye_r), (brow_c, eye_li), (brow_c, eye_ri),
        (eye_l, eye_li), (eye_r, eye_ri), (eye_li, eye_ri),
        (eye_l, cheek_l), (eye_r, cheek_r),
        (eye_li, nose_top), (eye_ri, nose_top),
        (nose_top, nose_mid), (nose_mid, nose_tip),
        (nose_tip, nose_l), (nose_tip, nose_r), (nose_l, nose_r),
        (nose_mid, cheek_l), (nose_mid, cheek_r),
        (cheek_l, nose_l), (cheek_r, nose_r),
        (cheek_l, mouth_l), (cheek_r, mouth_r),
        (mouth_l, mouth_c), (mouth_c, mouth_r),
        (nose_l, mouth_l), (nose_r, mouth_r), (nose_tip, mouth_c),
        (mouth_l, jaw_l), (mouth_r, jaw_r),
        (jaw_l, chin), (jaw_r, chin), (mouth_c, chin),
        (mouth_l, chin), (mouth_r, chin),
        (cheek_l, jaw_l), (cheek_r, jaw_r),
    ]
    for (a, b) in edges:
        d.line(a[0], a[1], b[0], b[1], _fade(color, 0.62), 1.0)

    spokes = [brow_l, brow_r, eye_l, eye_r, cheek_l, cheek_r, jaw_l, jaw_r,
              nose_top, brow_c]
    for (ax, ay) in spokes:
        nearest = min(oval, key=lambda p: (p[0] - ax) ** 2 + (p[1] - ay) ** 2)
        d.line(ax, ay, nearest[0], nearest[1], _fade(color, 0.45), 1.0)

    nodes = [brow_l, brow_c, brow_r, eye_l, eye_r, eye_li, eye_ri, nose_top,
             nose_mid, nose_tip, nose_l, nose_r, cheek_l, cheek_r, mouth_l,
             mouth_c, mouth_r, jaw_l, jaw_r, chin]
    node_r = max(1.2, min(w, h) * 0.006)
    for (px, py) in nodes + oval:
        d.disc(px, py, node_r, _fade(color, 0.95))

    if markers:
        def marker(pt, half):
            d.rect(pt[0] - half, pt[1] - half, pt[0] + half, pt[1] + half, color, 1.3)
        mk = max(4.0, min(w, h) * 0.022)
        marker(eye_l, mk)
        marker(eye_r, mk)
        marker(nose_tip, mk * 0.75)
        marker(mouth_c, mk * 0.85)
