"""REF3 — wide dark tactical "RADARSCAN" console (Starfield-style, matte amber).

Recreates C:/Users/antho/Downloads/ref_img/image-1782883970657.webp:
a three-zone tactical radar HUD rendered at 1265x652.

  LEFT   : SCAN_MODE header, MAIN// scale panel, TWO-WAY SCAN keypad matrix,
           the big STATUS radial gauge (tick ring + needle + "62"), knob dials,
           SYS/2 segmented buttons, MAINFRAME DATA table, DATA FLOW 67.2 cluster.
  CENTER : RADARSCAN top bar, numbered slot boxes, the hero RADAR CIRCLE with
           dashed range rings, a topographic CONTOUR map, SECTOR_203 diamond
           markers, a translucent RED SWEEP WEDGE, crosshair, bearing ticks.
  RIGHT  : //PRECOG SET, four "SECTR SCN FILD TABLE" panels (D.2/X.7/A.9/S.3)
           each with one ORANGE-highlighted row + a small SECTOR tick-ring dial.

All geometry is deterministic (no random). Drawn through the ARCV adapter `d`.
"""

from __future__ import annotations

import math

_TAU = math.pi * 2.0

# ------------------------------------------------------------------ palette
# muted Starfield orange on near-black; own constants (don't rely on theme).
ORANGE      = (0.90, 0.42, 0.14, 1.00)   # primary accent
ORANGE_BR   = (0.98, 0.52, 0.18, 1.00)   # brighter accent / needle
ORANGE_DIM  = (0.78, 0.38, 0.14, 0.72)
ORANGE_FILL = (0.86, 0.40, 0.13, 1.00)   # solid highlight bar behind text
WHITE       = (0.86, 0.86, 0.88, 1.00)
WHITE_SOFT  = (0.74, 0.74, 0.78, 0.95)
GRAY        = (0.50, 0.50, 0.55, 0.70)
GRAY_DIM    = (0.42, 0.42, 0.47, 0.55)
GRAY_FAINT  = (0.36, 0.36, 0.41, 0.42)
LINE_FAINT  = (0.32, 0.33, 0.37, 0.40)
LINE_HAIR   = (0.26, 0.27, 0.31, 0.32)
SWEEP_FILL  = (0.85, 0.18, 0.12, 0.24)   # translucent red pie
SWEEP_EDGE  = (0.92, 0.26, 0.18, 0.85)


def _fade(c, a):
    return (c[0], c[1], c[2], c[3] * a)


# ============================================================ LOCAL HELPERS
def tick_ring(d, cx, cy, r, n, length, c, w=1.0, a0=0.0, a1=_TAU, inward=True):
    """Radial tick marks around a circle."""
    for i in range(n):
        a = a0 + (a1 - a0) * (i / n)
        ca, sa = math.cos(a), math.sin(a)
        if inward:
            r0, r1 = r, r - length
        else:
            r0, r1 = r, r + length
        d.line(cx + ca * r0, cy + sa * r0, cx + ca * r1, cy + sa * r1, c, w)


def radial_gauge(d, cx, cy, r, value, s):
    """Circular STATUS dial: outer tick ring, faint concentric rings, diamond
    hub, and a wide ORANGE NEEDLE beam pointing DOWN (as in the reference)."""
    # outer faint boundary ring + inner tick ring band
    d.ring(cx, cy, r, GRAY_DIM, 1.3 * s)
    tick_ring(d, cx, cy, r * 0.985, 90, r * 0.035, GRAY_FAINT, 1.0 * s)
    tick_ring(d, cx, cy, r * 0.985, 18, r * 0.07, GRAY, 1.2 * s)
    # a couple of faint concentric rings inside
    for rr in (0.80, 0.60):
        d.ring(cx, cy, r * rr, LINE_HAIR, 1.0 * s)
    # dashed mid ring (faint gray, a few dots)
    for i in range(48):
        if i % 2 == 0:
            a0 = _TAU * i / 48
            d.ring(cx, cy, r * 0.72, GRAY_FAINT, 1.0 * s, a0=a0, a1=a0 + _TAU / 48 * 0.5)
    # partial ORANGE progress arc across the TOP (upper band)
    d.ring(cx, cy, r * 0.90, ORANGE, 2.4 * s,
           a0=math.radians(-150.0), a1=math.radians(-30.0))
    # two short bright orange spoke ticks at ~9 and ~3 o'clock
    for a in (math.radians(180.0), math.radians(0.0)):
        ca, sa = math.cos(a), math.sin(a)
        d.line(cx + ca * r * 0.60, cy + sa * r * 0.60,
               cx + ca * r * 0.74, cy + sa * r * 0.74, ORANGE_BR, 2.2 * s)
    # faint fine cross through center (the X guides)
    for a in (math.radians(35.0), math.radians(145.0)):
        ca, sa = math.cos(a), math.sin(a)
        d.line(cx - ca * r * 0.78, cy - sa * r * 0.78,
               cx + ca * r * 0.78, cy + sa * r * 0.78, LINE_HAIR, 1.0 * s)
    # soft NEEDLE beam: a widening cone pointing straight DOWN from the hub,
    # fading toward the tip (flashlight look, as in the reference).
    # THIN tapered NEEDLE angled toward the lower-right (~4-5 o'clock).
    na = math.radians(58.0)   # screen coords (y down): 0=right, 90=down
    ca, sa = math.cos(na), math.sin(na)
    perp = (-sa, ca)
    tip = (cx + ca * r * 0.80, cy + sa * r * 0.80)
    # slim needle: a narrow triangle from a small base at the hub to the tip,
    # plus a short tail on the opposite side (balanced pointer look).
    bw = r * 0.028                      # half-width at the hub
    b0 = (cx + perp[0] * bw, cy + perp[1] * bw)
    b1 = (cx - perp[0] * bw, cy - perp[1] * bw)
    d.tri_fill(b0, b1, tip, ORANGE_BR)
    # crisp centre line to keep it sharp against the dark dial
    d.line(cx, cy, tip[0], tip[1], ORANGE_BR, 1.6 * s)
    # small counterweight tail
    tail = (cx - ca * r * 0.16, cy - sa * r * 0.16)
    d.tri_fill(b0, b1, tail, _fade(ORANGE, 0.9))
    # diamond hub at center
    hr = r * 0.075
    _diamond(d, cx, cy, hr * 1.7, GRAY, w=1.3 * s)
    _diamond(d, cx, cy, hr, ORANGE_BR, fill=True)


def _diamond(d, cx, cy, r, c, w=1.4, fill=False):
    p = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    if fill:
        d.tri_fill(p[0], p[1], p[2], c)
        d.tri_fill(p[0], p[2], p[3], c)
    else:
        d.poly(p, c, w, closed=True)


def range_rings(d, cx, cy, r, levels, c, s, dash=42):
    """Several concentric DASHED circles drawn as many short arc segments."""
    for k, frac in enumerate(levels):
        rr = r * frac
        col = c if k % 2 == 0 else _fade(c, 0.7)
        # dashed: draw `dash` short arcs with gaps
        seg = _TAU / dash
        for i in range(dash):
            if i % 2 == 0:
                a0 = i * seg
                d.ring(cx, cy, rr, col, 1.1 * s, a0=a0, a1=a0 + seg * 0.62)


def contour_map(d, cx, cy, r, s):
    """SOFT ORGANIC topographic map: smooth closed contour LOOPS like a coastline
    / elevation map. Each loop = base radius + a sum of ONLY low-frequency sines
    (harmonics 1..4, small amplitude), sampled at many angles so it reads as a
    gently meandering curve (no straight chords, no high-frequency jitter). A few
    landmass systems, each with several nested elevation bands (a slight per-level
    phase drift so bands nest like real contours). Terrain sits upper-left heavy.
    Deterministic (no random)."""
    N = 160
    pale = lambda a: (0.72, 0.72, 0.75, a)

    def loop(base_r, cxx, cyy, harmonics, col, w):
        """One smooth closed contour. harmonics: list of (k, phase, amp_frac).
        amp_frac is a fraction of base_r; keep small so the loop stays smooth
        and never self-intersects into chords."""
        pts = []
        for i in range(N):
            a = _TAU * (i / N)
            rad = base_r
            for (k, ph, af) in harmonics:
                rad += base_r * af * math.sin(a * k + ph)
            pts.append((cxx + math.cos(a) * rad, cyy + math.sin(a) * rad))
        d.poly(pts, col, w, closed=True)

    def landmass(cxx, cyy, r0, harm_base, levels, alpha0):
        """Several nested elevation bands sharing a shape, each with its own tiny
        phase drift so the bands nest like a topographic map."""
        for lvl in range(levels):
            frac = 1.0 - lvl / (levels + 0.6)
            # per-level phase drift: shifts each band slightly -> nested contours
            harm = [(k, ph + lvl * 0.35, af) for (k, ph, af) in harm_base]
            a = alpha0 * (0.55 + 0.45 * (1.0 - lvl / levels))
            loop(r0 * frac, cxx, cyy, harm, pale(a), 0.9 * s)

    # --- MAIN landmass (big, upper-left heavy). Low harmonics only (1..4).
    mx, my = cx - r * 0.16, cy - r * 0.14
    harm_main = [(1, 0.5, 0.12), (2, 2.3, 0.09), (3, 4.1, 0.06), (4, 1.2, 0.04)]
    landmass(mx, my, r * 0.72, harm_main, 11, 0.62)

    # --- second landmass, mid-right, its own smooth shape
    harm_b = [(1, 3.0, 0.14), (2, 0.8, 0.08), (3, 2.5, 0.05), (4, 5.0, 0.035)]
    landmass(cx + r * 0.34, cy + r * 0.10, r * 0.40, harm_b, 8, 0.5)

    # --- third landmass, lower-left
    harm_c = [(1, 1.7, 0.13), (2, 4.4, 0.09), (3, 0.6, 0.055), (4, 2.9, 0.03)]
    landmass(cx - r * 0.40, cy + r * 0.34, r * 0.34, harm_c, 7, 0.46)

    # --- small islands / atolls (2-3 bands each)
    harm_i = [(1, 2.0, 0.16), (2, 5.1, 0.10), (3, 1.4, 0.06)]
    for (dx, dy, rr, ph) in ((0.10, -0.42, 0.14, 0.0), (0.46, -0.30, 0.11, 1.3),
                             (-0.10, 0.44, 0.12, 2.6), (0.30, 0.42, 0.10, 3.9),
                             (-0.44, -0.06, 0.11, 5.2)):
        h = [(k, p + ph, af) for (k, p, af) in harm_i]
        landmass(cx + r * dx, cy + r * dy, r * rr, h, 3, 0.44)

    # --- tiny single-loop reef spots
    for (dx, dy, rr, ph) in ((-0.22, -0.30, 0.05, 0.7), (0.20, 0.20, 0.045, 2.1),
                             (0.42, 0.02, 0.04, 3.5), (-0.30, 0.12, 0.045, 4.8),
                             (0.06, -0.18, 0.04, 1.1)):
        h = [(1, ph, 0.18), (2, ph + 2.0, 0.10)]
        loop(r * rr, cx + r * dx, cy + r * dy, h, pale(0.34), 0.9 * s)


def sweep_wedge(d, cx, cy, r, a0, a1, s):
    """Translucent RED filled pie-slice (tri_fan) = active radar sweep sector."""
    n = 26
    prev = None
    for i in range(n + 1):
        a = a0 + (a1 - a0) * (i / n)
        p = (cx + math.cos(a) * r, cy + math.sin(a) * r)
        if prev is not None:
            d.tri_fill((cx, cy), prev, p, SWEEP_FILL)
        prev = p
    # bright leading + trailing edges
    d.line(cx, cy, cx + math.cos(a0) * r, cy + math.sin(a0) * r, _fade(SWEEP_EDGE, 0.6), 1.4 * s)
    d.line(cx, cy, cx + math.cos(a1) * r, cy + math.sin(a1) * r, SWEEP_EDGE, 1.8 * s)


def sector_marker(d, x, y, label, s, sub="", flip=False):
    """Small diamond outline + text label + a tiny lat/long tick line."""
    r = 7 * s
    _diamond(d, x, y, r, ORANGE, w=1.6 * s)
    d.disc(x, y, 1.6 * s, ORANGE_BR)
    lx = x + (r + 6 * s if not flip else -(r + 6 * s))
    align = "left" if not flip else "right"
    d.text(label, lx, y - 8 * s, 9 * s, ORANGE, align=align)
    if sub:
        d.text(sub, lx, y + 3 * s, 7 * s, GRAY, align=align)


def data_table(d, x, y, rows, s, hl=-1, col_w=(0, 46, 78, 112), row_h=11.5, kw=9.0):
    """Tiny monospaced rows/columns of numbers; row `hl` gets a solid orange bar."""
    for i, row in enumerate(rows):
        ry = y + i * row_h * s
        if i == hl:
            d.rrect_fill(x - 3 * s, ry - 1.5 * s, x + col_w[-1] + 22 * s, ry + (row_h - 2.0) * s,
                         1.5 * s, ORANGE_FILL)
            tc = WHITE
        else:
            tc = WHITE_SOFT if i % 2 == 0 else GRAY
        for j, cell in enumerate(row):
            cx = x + col_w[min(j, len(col_w) - 1)] * s
            c = tc if (i == hl) else (WHITE_SOFT if j == 0 else (ORANGE if j == len(row) - 1 and i != hl else GRAY))
            if i == hl:
                c = WHITE
            d.text(str(cell), cx, ry, kw * s, c)


def small_dial(d, cx, cy, r, value, s, label=""):
    """Little knob/gauge: tick ring + a pointer."""
    d.ring(cx, cy, r, GRAY, 1.2 * s)
    tick_ring(d, cx, cy, r, 12, r * 0.22, GRAY_FAINT, 1.0 * s)
    a = math.radians(130.0) + math.radians(280.0) * value
    d.line(cx, cy, cx + math.cos(a) * r * 0.72, cy + math.sin(a) * r * 0.72, ORANGE, 1.6 * s)
    d.disc(cx, cy, r * 0.14, ORANGE)
    if label:
        d.text(label, cx, cy + r + 4 * s, 7.5 * s, GRAY, align="center")


def keypad_matrix(d, x, y, cols, rows, cell, s, filled=frozenset(), gap=2.0):
    """Grid of small squares; some filled (the scan matrix)."""
    for r in range(rows):
        for c in range(cols):
            x0 = x + c * (cell + gap) * s
            y0 = y + r * (cell + gap) * s
            x1, y1 = x0 + cell * s, y0 + cell * s
            if (c, r) in filled:
                d.rrect_fill(x0, y0, x1, y1, 1.0 * s, ORANGE)
            else:
                d.rect(x0, y0, x1, y1, GRAY_DIM, 1.0 * s)


def segmented_bar(d, x, y, w, h, n, s, hot=frozenset(), gap=2.0, base=GRAY_DIM):
    """Horizontal row of segments, some highlighted orange."""
    sw = (w - gap * s * (n - 1)) / n
    for i in range(n):
        x0 = x + i * (sw + gap * s)
        x1 = x0 + sw
        if i in hot:
            d.rrect_fill(x0, y, x1, y + h, 1.0 * s, ORANGE)
        else:
            d.rect(x0, y, x1, y + h, base, 1.0 * s)


def _hazard_box(d, x0, y0, x1, y1, s):
    """Diagonal hazard stripes clipped to a box (drawn as short diagonal lines)."""
    d.rect(x0, y0, x1, y1, GRAY, 1.0 * s)
    step = 7 * s
    x = x0 - (y1 - y0)
    while x < x1:
        xa, ya = max(x, x0), y1 - (max(x, x0) - x)
        xb = min(x + (y1 - y0), x1)
        yb = y1 - (xb - x)
        # clamp within box
        if ya > y1:
            ya = y1
        d.line(max(x, x0), min(max(y1 - (max(x, x0) - x), y0), y1),
               min(x + (y1 - y0), x1), max(y1 - (min(x + (y1 - y0), x1) - x), y0),
               GRAY_FAINT, 1.4 * s)
        x += step


def _dashed_line(d, x0, y0, x1, y1, c, w, dash, gap):
    """A straight dashed line from (x0,y0) to (x1,y1)."""
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    if L < 1e-6:
        return
    ux, uy = dx / L, dy / L
    pos = 0.0
    while pos < L:
        a = pos
        b = min(pos + dash, L)
        d.line(x0 + ux * a, y0 + uy * a, x0 + ux * b, y0 + uy * b, c, w)
        pos += dash + gap


def _bracket_panel(d, x0, y0, x1, y1, c, s, w=1.2):
    """A faint frame with corner ticks (the recurring panel look)."""
    cl = 8 * s
    for (ox, sx) in ((x0, 1), (x1, -1)):
        for (oy, sy) in ((y0, 1), (y1, -1)):
            d.line(ox, oy, ox + sx * cl, oy, c, w * s)
            d.line(ox, oy, ox, oy + sy * cl, c, w * s)


# ==================================================================== BUILD
def build(d, W, H, t=0.0):
    s = H / 652.0

    def X(f):
        return f * W

    def Y(f):
        return f * H

    _left_column(d, W, H, s, X, Y)
    _center_zone(d, W, H, s, X, Y, t)
    _right_column(d, W, H, s, X, Y)
    _bottom_strip(d, W, H, s, X, Y)
    _frame(d, W, H, s, X, Y)


# ----------------------------------------------------------------- outer frame
def _frame(d, W, H, s, X, Y):
    # vertical zone dividers
    d.line(X(0.232), Y(0.03), X(0.232), Y(0.965), LINE_FAINT, 1.2 * s)
    d.line(X(0.742), Y(0.03), X(0.742), Y(0.965), LINE_FAINT, 1.2 * s)
    # thin outer corner brackets
    _bracket_panel(d, X(0.006), Y(0.02), X(0.994), Y(0.975), GRAY_DIM, s, w=1.4)


# ------------------------------------------------------------------ LEFT COLUMN
def _left_column(d, W, H, s, X, Y):
    lx = X(0.014)
    rx = X(0.222)

    # --- header: SCAN_MODE + value + top segmented bar
    d.text("SCAN_MODE", lx, Y(0.028), 11 * s, WHITE)
    d.text("1830.2173  88", X(0.075), Y(0.028), 10 * s, GRAY)
    segmented_bar(d, X(0.125), Y(0.030), X(0.095), 7 * s, 10, s, hot={0}, base=GRAY_FAINT)
    d.line(lx, Y(0.052), rx, Y(0.052), LINE_FAINT, 1.0 * s)

    # --- MAIN // mini panel with 0..8 scale rows
    d.text("MAIN //", lx, Y(0.068), 9 * s, GRAY)
    d.text("2.5", X(0.207), Y(0.068), 8 * s, ORANGE, align="right")
    for r in range(2):
        ry = Y(0.088) + r * 0.024 * H
        # tick scale 0..8
        d.line(lx, ry, X(0.13), ry, GRAY_DIM, 1.4 * s)
        for k in range(9):
            tx = lx + (X(0.13) - lx) * (k / 8.0)
            d.line(tx, ry - 3 * s, tx, ry + 3 * s, GRAY_FAINT, 1.0 * s)
        # small readouts to the right
        d.text("00 12 78", X(0.145), ry - 4 * s, 8 * s, GRAY)
    for k in range(9):
        tx = lx + (X(0.13) - lx) * (k / 8.0)
        d.text(str(k), tx, Y(0.122), 7 * s, GRAY_FAINT, align="center")

    # --- TWO-WAY SCAN ANOTHER keypad matrix
    d.text("TWO-WAY SCAN  ANOTHER", X(0.145), Y(0.058), 7.5 * s, GRAY)
    filled = {(1, 0), (3, 1), (0, 2), (4, 2), (2, 3), (5, 1), (3, 3), (1, 4), (4, 4)}
    keypad_matrix(d, X(0.145), Y(0.070), 6, 5, 8.5, s, filled=filled)
    d.text("87A LEFT  SCAN", X(0.145), Y(0.165), 7 * s, GRAY)

    d.line(lx, Y(0.185), rx, Y(0.185), LINE_HAIR, 1.0 * s)

    # --- big STATUS radial gauge
    gx, gy, gr = X(0.115), Y(0.315), 0.072 * W
    radial_gauge(d, gx, gy, gr, 62.0, s)
    d.text("STATUS", lx + 2 * s, Y(0.278), 10 * s, WHITE)
    d.text("62", lx + 2 * s, Y(0.292), 46 * s, WHITE)
    d.text("STG x 29", lx + 2 * s, Y(0.372), 8 * s, ORANGE)
    d.text("ONE-WAY SCAN", X(0.16), Y(0.212), 7 * s, GRAY)

    # --- three small knob dials (RUN 1 / ACTIVE B / ...)
    ky = Y(0.462)
    labels = [("RUN 1", 0.30), ("ACTIVE B", 0.62), ("SET 4", 0.48)]
    for i, (lbl, v) in enumerate(labels):
        kx = X(0.038) + i * 0.062 * W
        small_dial(d, kx, ky, 15 * s, v, s, label=lbl)

    d.line(lx, Y(0.512), rx, Y(0.512), LINE_HAIR, 1.0 * s)

    # --- SYS /2 with SET / GET / RGT segmented buttons + MAINFRAME DATA
    d.text("SYS /2", lx, Y(0.542), 13 * s, WHITE)
    btns = ["SET", "GET", "RGT"]
    bw_btn = 0.024 * W
    for i, b in enumerate(btns):
        bx = X(0.066) + i * 0.027 * W
        hot = (i == 0)
        if hot:
            d.rrect_fill(bx, Y(0.536), bx + bw_btn, Y(0.556), 2 * s, ORANGE)
            d.text(b, bx + bw_btn * 0.5, Y(0.539), 7.5 * s, WHITE, align="center")
        else:
            d.rrect(bx, Y(0.536), bx + bw_btn, Y(0.556), 2 * s, GRAY, 1.1 * s)
            d.text(b, bx + bw_btn * 0.5, Y(0.539), 7.5 * s, GRAY, align="center")
        d.text("+8" if i == 0 else "+4", bx + bw_btn * 0.5, Y(0.560), 6.5 * s, GRAY, align="center")
    # MAINFRAME DATA starts clear of the buttons (last button ends ~X(0.156))
    d.text("MAINFRAME DATA", X(0.160), Y(0.540), 7.0 * s, WHITE)
    d.text("TG5233", X(0.160), Y(0.552), 7.0 * s, GRAY)

    # --- dense DATA TABLE of numbers
    tbl_y = Y(0.585)
    d.line(lx, tbl_y - 4 * s, rx, tbl_y - 4 * s, LINE_HAIR, 1.0 * s)
    rows = [
        ("NODE", "0393", "2288", "0071"),
        ("DAT7", "6612", "0349", "1140"),
        ("BUS3", "8871", "4402", "9930"),
        ("MEM9", "0053", "7781", "2214"),
        ("SYN2", "4471", "0090", "5567"),
    ]
    data_table(d, lx + 2 * s, tbl_y, rows, s, hl=-1,
               col_w=(0, 42, 78, 114), row_h=11.0, kw=8.0)
    # a column of vertical labels to the right
    for i, lbl in enumerate(("0197", "0071", "0053", "0217")):
        d.text(lbl, X(0.207), tbl_y + i * 11.5 * s, 7 * s, GRAY, align="right")

    # --- DATA FLOW 67.2 cluster with orange highlighted cells + mini dials/bars
    fy = Y(0.795)
    d.line(lx, fy - 8 * s, rx, fy - 8 * s, LINE_FAINT, 1.0 * s)
    # left mini dial cluster (MACRO / ZONING)
    small_dial(d, X(0.045), fy + 0.02 * H, 13 * s, 0.4, s, label="MACRO")
    small_dial(d, X(0.045), fy + 0.075 * H, 12 * s, 0.7, s, label="ZONING")
    # DATA FLOW big number
    d.text("DATA FLOW", X(0.098), fy - 2 * s, 8 * s, GRAY)
    d.text("67.2", X(0.098), fy + 8 * s, 30 * s, WHITE)
    d.text("+433", X(0.098), fy + 0.058 * H, 8 * s, ORANGE)
    # orange-highlighted cells grid
    cells = [("A9", True), ("13", False), ("70", True), ("55", True), ("00", False)]
    cxs = X(0.160)
    for i, (v, hot) in enumerate(cells):
        cy0 = fy - 4 * s + i * 10 * s
        if hot:
            d.rrect_fill(cxs, cy0, cxs + 0.024 * W, cy0 + 8 * s, 1 * s, ORANGE)
            d.text(v, cxs + 0.003 * W, cy0, 7 * s, WHITE)
        else:
            d.rect(cxs, cy0, cxs + 0.024 * W, cy0 + 8 * s, GRAY_DIM, 1.0 * s)
            d.text(v, cxs + 0.003 * W, cy0, 7 * s, GRAY)
        d.text(("114", "158", "83", "164", "00")[i], X(0.196), cy0, 7 * s, GRAY)


# ------------------------------------------------------------------ CENTER ZONE
def _center_zone(d, W, H, s, X, Y, t):
    cx0, cx1 = X(0.244), X(0.732)

    # --- top bar
    d.text("RADARSCAN", cx0, Y(0.028), 12 * s, WHITE)
    d.text("/SYSTEM ACTIVE", X(0.325), Y(0.030), 9 * s, GRAY)
    d.text("DATA INPUT MOD 72.77", X(0.415), Y(0.030), 9 * s, GRAY)
    d.line(cx0, Y(0.050), cx1, Y(0.050), LINE_FAINT, 1.0 * s)

    # --- row of 7 numbered slot boxes + hazard box
    by0, by1 = Y(0.058), Y(0.088)
    slot_w = (X(0.640) - cx0) / 7.0
    for i in range(7):
        x0 = cx0 + i * slot_w
        x1 = x0 + slot_w - 4 * s
        d.rect(x0, by0, x1, by1, GRAY_DIM, 1.1 * s)
        d.text(str(i + 1), (x0 + x1) / 2, by0 + 8 * s, 9 * s, GRAY, align="center")
    _hazard_box(d, X(0.645), by0, X(0.700), by1, s)

    # --- little left readouts under the bar
    d.text("TL/44 11-L73", cx0, Y(0.108), 7 * s, GRAY)
    d.text("330E7", cx0, Y(0.122), 7 * s, GRAY_FAINT)
    d.text("100T13108", X(0.278), Y(0.122), 7 * s, GRAY_FAINT)
    d.text("ACTIVE TRUE MOD 088", cx0, Y(0.140), 7.5 * s, ORANGE_DIM)

    # left vertical scale labels down the divider inner edge
    for i, lbl in enumerate(("/32", "1901", "0087", "2467", "1902", "4998",
                             "01178", "9902", "2G", "3040", "2777", "9SG",
                             "2338", "3017", "14GE", "3000")):
        d.text(lbl, X(0.246), Y(0.19) + i * 0.045 * H, 6.5 * s, GRAY_FAINT)

    # --- BIG RADAR CIRCLE (hero)
    rcx, rcy = X(0.485), Y(0.52)
    rr = 0.235 * H * (H / H)  # radius in px
    rr = 0.28 * W * 0.5
    rr = 173 * s
    # contour topographic map inside (drawn first, under the rings/markers)
    contour_map(d, rcx, rcy, rr * 0.98, s)

    # range rings (dashed concentric, light gray)
    range_rings(d, rcx, rcy, rr, (1.0, 0.82, 0.64, 0.46, 0.28), (0.6, 0.6, 0.65, 0.55), s, dash=58)
    # two bright orange dashed rings (outer + mid)
    for ringf, dn in ((0.90, 64), (0.73, 60)):
        seg = _TAU / dn
        for i in range(dn):
            if i % 2 == 0:
                a0 = i * seg
                d.ring(rcx, rcy, rr * ringf, ORANGE_DIM, 1.2 * s, a0=a0, a1=a0 + seg * 0.6)

    # white dashed radial crosslines (diagonal grid through the disc)
    for a in (math.radians(30.0), math.radians(75.0), math.radians(120.0),
              math.radians(160.0), math.radians(210.0), math.radians(300.0)):
        ca, sa = math.cos(a), math.sin(a)
        _dashed_line(d, rcx, rcy, rcx + ca * rr, rcy + sa * rr, (0.7, 0.7, 0.74, 0.4), 1.0 * s, 8, 6)

    # translucent RED sweep wedge (lower-right sector)
    sweep_wedge(d, rcx, rcy, rr * 0.98, math.radians(18.0), math.radians(88.0), s)

    # crosshair center + fine cross lines
    d.line(rcx - rr, rcy, rcx + rr, rcy, (0.6, 0.6, 0.64, 0.35), 1.0 * s)
    d.line(rcx, rcy - rr, rcx, rcy + rr, (0.6, 0.6, 0.64, 0.35), 1.0 * s)
    _diamond(d, rcx, rcy, 5 * s, ORANGE, w=1.4 * s)
    d.disc(rcx, rcy, 1.6 * s, ORANGE_BR)

    # bearing tick numbers around rim
    for k in range(24):
        a = _TAU * (k / 24.0) - math.pi / 2
        ca, sa = math.cos(a), math.sin(a)
        d.line(rcx + ca * rr, rcy + sa * rr, rcx + ca * (rr - 6 * s), rcy + sa * (rr - 6 * s),
               GRAY_FAINT, 1.0 * s)
        if k % 3 == 0:
            lbl = "%03d" % (k * 15)
            d.text(lbl, rcx + ca * (rr + 12 * s), rcy + sa * (rr + 12 * s), 6.5 * s,
                   GRAY, align="center")

    # SECTOR_203 diamond markers
    markers = [
        (rcx + rr * 0.10, rcy - rr * 0.52, False),
        (rcx - rr * 0.30, rcy + rr * 0.02, True),
        (rcx + rr * 0.62, rcy + rr * 0.01, False),
        (rcx - rr * 0.02, rcy + rr * 0.36, False),
        (rcx + rr * 0.18, rcy + rr * 0.66, False),
    ]
    for (mx, my, flip) in markers:
        sector_marker(d, mx, my, "SECTOR_203", s,
                      sub="42 40 41.2771N", flip=flip)

    # scattered orange caret / arrow glyphs
    carets = [(-0.42, -0.18), (-0.10, 0.14), (0.30, -0.30), (0.24, 0.30),
              (-0.24, 0.44), (0.02, -0.10), (0.40, 0.44)]
    for (dx, dy) in carets:
        gx, gy = rcx + rr * dx, rcy + rr * dy
        d.poly([(gx, gy + 5 * s), (gx + 4 * s, gy - 4 * s), (gx + 8 * s, gy + 5 * s)],
               ORANGE, 1.4 * s)

    # two small concentric-circle target icons top-right of radar
    for (tx, ty) in ((X(0.712), Y(0.13)), (X(0.712), Y(0.175))):
        d.ring(tx, ty, 9 * s, GRAY, 1.2 * s)
        d.ring(tx, ty, 4 * s, ORANGE, 1.4 * s)
        d.line(tx - 12 * s, ty, tx + 12 * s, ty, GRAY_FAINT, 1.0 * s)
        d.line(tx, ty - 12 * s, tx, ty + 12 * s, GRAY_FAINT, 1.0 * s)

    # bottom scale bar with orange segments
    sby = Y(0.955)
    d.line(cx0, sby - 6 * s, cx1, sby - 6 * s, LINE_HAIR, 1.0 * s)
    segmented_bar(d, cx0, sby, X(0.48), 6 * s, 40, s,
                  hot={5, 6, 12, 20, 21, 31}, gap=1.5, base=GRAY_FAINT)


# ------------------------------------------------------------------ RIGHT COLUMN
def _right_column(d, W, H, s, X, Y):
    px = X(0.752)
    d.text("//", px, Y(0.030), 10 * s, GRAY)
    d.text("PRECOG SET", X(0.855), Y(0.030), 10 * s, GRAY)
    d.line(px, Y(0.052), X(0.99), Y(0.052), LINE_FAINT, 1.0 * s)

    panels = [
        ("D.2", 0.088, [("BRINTH WHI-2", "16", "409", "465", False),
                        ("MENIA", "41", "419", "429", False),
                        ("JERS", "27", "600", "500", False),
                        ("PBGGRP", "72", "007", "445", False),
                        ("CN 62MTY", "56", "690", "301", True),
                        ("DYNE.A", "N3", "500", "500", False),
                        ("AUG DAP", "T3", "600", "231", False)]),
        ("X.7", 0.320, [("MENIA", "15", "710", "281", False),
                        ("BRINTH WHI-2", "40", "444", "603", True),
                        ("JERS", "27", "490", "622", False),
                        ("PBGGRP", "72", "007", "245", False),
                        ("CN 62MTY", "56", "500", "554", False),
                        ("DYNE.A", "N3", "530", "377", False),
                        ("AUG DAP", "T3", "600", "236", False)]),
        ("A.9", 0.552, [("BRINTH WHI-2", "16", "409", "467", True),
                        ("MENIA", "41", "419", "603", False),
                        ("JERS", "27", "490", "355", False),
                        ("PBGGRP", "72", "600", "301", False),
                        ("CN 62MTY", "94", "664", "554", False),
                        ("DYNE.A", "N3", "500", "677", True),
                        ("AUG DAP", "T3", "600", "295", False)]),
        ("S.3", 0.784, [("BRINTH WHI-2", "16", "409", "467", True),
                        ("MENIA", "41", "419", "603", False),
                        ("JERS", "27", "490", "355", False),
                        ("PBGGRP", "72", "600", "544", False),
                        ("CN 62MTY", "94", "500", "500", False),
                        ("DYNE.A", "N3", "500", "677", False),
                        ("AUG DAP", "T3", "600", "295", False)]),
    ]

    for (code, ytop, rows) in panels:
        _sector_panel(d, W, H, s, X, Y, px, ytop, code, rows)

    # far-right vertical edge labels
    for i, lbl in enumerate(("SGSDRDDGG", "SDGDR2G", "GSDDRDDR", "SDGDR2G",
                             "SGSDRDDGG", "SDDR2G", "SDGDR2G", "SGSDR")):
        # draw rotated-looking by stacking single chars? keep tiny horizontal
        d.text(lbl, X(0.995), Y(0.12) + i * 0.10 * H, 5.5 * s, GRAY_FAINT, align="right")


def _sector_panel(d, W, H, s, X, Y, px, ytop, code, rows):
    y0 = Y(ytop)
    # big sector code on the left
    d.text("SECTOR", px, y0, 7 * s, GRAY)
    d.text(code, px, y0 + 10 * s, 30 * s, ORANGE)

    # title
    tx = X(0.792)
    d.text("SECTR SCN FILD TABLE", tx, y0, 8.5 * s, WHITE)
    # data table with one highlighted row
    ty = y0 + 14 * s
    row_h = 10.5
    tw_code = X(0.982)
    for i, (name, a, b, c, hot) in enumerate(rows):
        ry = ty + i * row_h * s
        if hot:
            d.rrect_fill(tx - 3 * s, ry - 1 * s, tw_code, ry + (row_h - 2) * s, 1.5 * s, ORANGE_FILL)
            nc = WHITE
            vc = WHITE
        else:
            nc = WHITE_SOFT if i % 2 == 0 else GRAY
            vc = GRAY
        d.text(name, tx, ry, 7 * s, nc)
        d.text(a, X(0.905), ry, 7 * s, ORANGE if not hot else WHITE)
        d.text(b, X(0.938), ry, 7 * s, vc)
        d.text(c, X(0.980), ry, 7 * s, ORANGE if not hot else WHITE, align="right")

    # small SECTOR tick-ring dial beside/below
    dcx, dcy = X(0.905), y0 + 0.115 * H
    small_dial(d, dcx, dcy, 16 * s, 0.55, s, label="SECTOR")


# ------------------------------------------------------------------ BOTTOM STRIP
def _bottom_strip(d, W, H, s, X, Y):
    y = Y(0.985)
    d.line(X(0.01), y - 8 * s, X(0.99), y - 8 * s, LINE_HAIR, 1.0 * s)
    # a horizontal strip of small numbers + orange segment blocks
    x = X(0.02)
    for i in range(26):
        val = "%03d" % ((i * 37 + 11) % 1000)
        d.text(val, x, y, 6.5 * s, GRAY if i % 4 else ORANGE, align="left")
        x += 0.036 * W
        if i in (3, 7, 12, 18, 22):
            d.rrect_fill(x - 0.008 * W, y - 1 * s, x - 0.001 * W, y + 6 * s, 1 * s, ORANGE)


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _ref_render import render_png, save_compare
    from arcv.theme import make_theme
    REF = "C:/Users/antho/Downloads/arcv/examples/refs/gallery/ref3_reference.webp"
    _HERE = os.path.dirname(os.path.abspath(__file__))
    OUT = os.path.join(_HERE, "gallery", "ref3.png")
    CMP = os.path.join(_HERE, "gallery", "ref3_compare.png")
    theme = make_theme("amber", bloom_intensity=0.5, bloom_threshold=0.6, exposure=1.15,
                       scanline_strength=0.0, sweep_strength=0.0)
    render_png(build, OUT, size=(1265, 652), mode="glow",
               theme=theme, base_color=(0.03, 0.03, 0.035, 1.0))
    save_compare(REF, OUT, CMP, "REF3")
    print("done")
