"""REF1 — Four yellow-on-black cyberpunk WARNING panels on light-gray (2x2).

Flat vector art recreation of the reference image. All content is authored as
local helper primitives composed from the ARCV adapter `d`, so nothing under
arcv/ or any shared file is touched.

Palette: bright cadmium yellow fills, near-black content/outlines/hazard
stripes, darker charcoal for the A1..A4 mode cells and small screens.
"""

from __future__ import annotations

import math

# ------------------------------------------------------------------ palette
YEL = (0.94, 0.90, 0.02, 1.0)     # bright cadmium yellow fill
YEL_D = (0.80, 0.77, 0.02, 1.0)   # slightly darker yellow (shading)
BLK = (0.06, 0.06, 0.05, 1.0)     # near-black content / outline
CHAR = (0.16, 0.16, 0.14, 1.0)    # charcoal (A1..A4 cells, small screens)
CHAR_HI = (0.42, 0.40, 0.10, 1.0)  # highlighted mode cell (brighter olive)
GRAY = (0.82, 0.82, 0.82, 1.0)    # background gray (for knockouts)


def _f(c, a):
    return (c[0], c[1], c[2], c[3] * a)


# =====================================================================
#  GENERIC HELPER PRIMITIVES
# =====================================================================
def notched_panel(d, x0, y0, x1, y1, cut, c, w, fill=None):
    """Rectangle outline with the two RIGHT corners cut at 45deg (notched)."""
    pts = [
        (x0, y0),
        (x1 - cut, y0),
        (x1, y0 + cut),
        (x1, y1 - cut),
        (x1 - cut, y1),
        (x0, y1),
    ]
    if fill is not None:
        # emulate fill with a stack of horizontal lines (cheap polygon fill)
        _poly_fill(d, pts, fill)
    d.poly(pts, c, w, closed=True)
    return pts


def _poly_fill(d, pts, c):
    """Scanline fill of a polygon using overlapping horizontal lines. Uses a
    sub-pixel step with a line width > step so coverage is fully opaque (no
    background bleed between scanlines)."""
    ys = [p[1] for p in pts]
    y0, y1 = min(ys), max(ys)
    n = len(pts)
    step = 0.6
    lw = 1.8  # >> step, guarantees overlap -> solid fill
    y = y0
    while y <= y1 + step:
        xs = []
        for i in range(n):
            ax, ay = pts[i]
            bx, by = pts[(i + 1) % n]
            if (ay <= y < by) or (by <= y < ay):
                tt = (y - ay) / (by - ay)
                xs.append(ax + tt * (bx - ax))
        if len(xs) >= 2:
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                d.line(xs[k] - 0.5, y, xs[k + 1] + 0.5, y, c, lw)
        y += step


def hazard_stripes(d, x0, y0, x1, y1, c, sw=9.0, gap=9.0, w=6.0, up=True):
    """Diagonal hazard stripes clipped to the box [x0,y0,x1,y1]."""
    bw = x1 - x0
    bh = y1 - y0
    x = x0 - bh
    slope = 1.0 if up else -1.0
    while x < x1 + bh:
        # a diagonal segment; clip crudely by bounding to the box
        ax, ay = x, y1
        bx, by = x + bh, y0
        # clip x to [x0, x1]
        pts = _clip_seg(ax, ay, bx, by, x0, y0, x1, y1)
        if pts:
            (cx0, cy0), (cx1, cy1) = pts
            d.line(cx0, cy0, cx1, cy1, c, w)
        x += sw + gap


def _clip_seg(x0, y0, x1, y1, cx0, cy0, cx1, cy1):
    """Liang-Barsky clip of segment to rect. Returns [(x0,y0),(x1,y1)] or None."""
    dx = x1 - x0
    dy = y1 - y0
    p = [-dx, dx, -dy, dy]
    q = [x0 - cx0, cx1 - x0, y0 - cy0, cy1 - y0]
    u1, u2 = 0.0, 1.0
    for i in range(4):
        if p[i] == 0:
            if q[i] < 0:
                return None
        else:
            r = q[i] / p[i]
            if p[i] < 0:
                u1 = max(u1, r)
            else:
                u2 = min(u2, r)
    if u1 > u2:
        return None
    return [(x0 + u1 * dx, y0 + u1 * dy), (x0 + u2 * dx, y0 + u2 * dy)]


def barcode(d, x0, y0, x1, y1, c, seed=1):
    """A vertical-bar barcode filling [x0,y0]-[x1,y1]."""
    x = x0
    r = seed * 2654435761 & 0xFFFFFFFF
    while x < x1:
        r = (1103515245 * r + 12345) & 0xFFFFFFFF
        bw = 1.0 + (r >> 16) % 4
        r = (1103515245 * r + 12345) & 0xFFFFFFFF
        gap = 1.0 + (r >> 18) % 3
        if x + bw > x1:
            bw = x1 - x
        d.rect(x + bw * 0.5, y0, x + bw * 0.5, y1, c, bw)
        x += bw + gap


def warning_triangle(d, cx, cy, r, c, w=2.0, fill=None):
    """Equilateral warning triangle with a '!' inside."""
    p0 = (cx, cy - r)
    p1 = (cx - r * 0.90, cy + r * 0.72)
    p2 = (cx + r * 0.90, cy + r * 0.72)
    if fill is not None:
        d.tri_fill(p0, p1, p2, fill)
    d.tri(p0, p1, p2, c, w)
    # exclamation
    d.rect(cx, cy - r * 0.28, cx, cy + r * 0.28, c, max(2.0, r * 0.16))
    d.disc(cx, cy + r * 0.48, max(1.6, r * 0.10), c)


def biohazard(d, cx, cy, r, c, w=2.0, bg=YEL):
    """Real biohazard trefoil (black on yellow), classic orientation with one
    blade UP and two lower. Construction (draw order matters):
      1. three broad SOLID blade discs at 120deg,
      2. carve a bg CRESCENT on the inner side of each blade (a bg disc pushed
         toward the center) -> leaves a curved blade with a crescent gap,
      3. carve bg wedges in the gaps BETWEEN blades to pinch them to points,
      4. draw a small SOLID center circle ON TOP.
    No eye-dots -> reads instantly as biohazard."""
    # Construction = three INTERLOCKING RINGS (annuli) sharing a solid hub, the
    # canonical biohazard read. Draw order matters (flat mode = opaque over):
    #   1. three solid lobe discs at 120deg that overlap at the center,
    #   2. carve a bg hole in each lobe -> each becomes a black RING,
    #   3. re-solidify the very center as a hub, carve a bg gap ring,
    #   4. small solid center dot on top.
    ang0 = -math.pi / 2                 # first lobe points UP
    d_lobe = r * 0.50                   # lobe-center distance (they overlap at center)
    Ro = r * 0.58                       # lobe outer radius (bolder trefoil)
    Ri = r * 0.22                       # lobe hole radius (thicker ring bands)
    # 1. solid lobes (overlap -> interlocked black mass at center)
    for k in range(3):
        a = ang0 + k * (2 * math.pi / 3)
        d.disc(cx + math.cos(a) * d_lobe, cy + math.sin(a) * d_lobe, Ro, c)
    # 2. bg hole in each lobe -> three interlocking rings
    for k in range(3):
        a = ang0 + k * (2 * math.pi / 3)
        d.disc(cx + math.cos(a) * d_lobe, cy + math.sin(a) * d_lobe, Ri, bg)
    # 3. hub: re-fill center, then a bg gap ring so the dot reads separately
    d.disc(cx, cy, r * 0.28, c)
    d.disc(cx, cy, r * 0.20, bg)
    # 4. solid center dot
    d.disc(cx, cy, r * 0.12, c)


def hexagon(d, cx, cy, r, c, w=2.0, flat=True):
    pts = []
    for k in range(6):
        a = math.pi / 6 + k * math.pi / 3 if flat else k * math.pi / 3
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    d.poly(pts, c, w, closed=True)


def corner_ticks(d, x0, y0, x1, y1, c, ln=12.0, inset=8.0, w=1.6):
    """Short right-angle accent marks just inside each of the 4 corners."""
    for (cx, sx) in ((x0 + inset, 1), (x1 - inset, -1)):
        for (cy, sy) in ((y0 + inset, 1), (y1 - inset, -1)):
            d.line(cx, cy, cx + sx * ln, cy, c, w)
            d.line(cx, cy, cx, cy + sy * ln, c, w)


def stepped_edge(pts, x, y, dx, dy, sw, sh):
    """Append an outward rectangular NOTCH/step to a polygon point list.
    Moves along (dx,dy); pushes out by (sh) perpendicular for width (sw)."""
    # perpendicular direction (rotate 90)
    px, py = -dy, dx
    pts.append((x, y))
    pts.append((x + px * sh, y + py * sh))
    pts.append((x + px * sh + dx * sw, y + py * sh + dy * sw))
    pts.append((x + dx * sw, y + dy * sw))
    return x + dx * sw, y + dy * sw


def crescent_globe(d, cx, cy, r, c, w=2.0, bg=YEL):
    """Gridded globe circle with a real filled CRESCENT moon inside."""
    d.ring(cx, cy, r, c, w)
    # grid lines (latitude/longitude chords)
    for k in (-0.6, -0.3, 0.0, 0.3, 0.6):
        yy = cy + k * r
        hw = math.sqrt(max(0.0, r * r - (k * r) ** 2))
        d.line(cx - hw, yy, cx + hw, yy, c, w * 0.55)
    for k in (-0.6, -0.3, 0.0, 0.3, 0.6):
        xx = cx + k * r
        hh = math.sqrt(max(0.0, r * r - (k * r) ** 2))
        d.line(xx, cy - hh, xx, cy + hh, c, w * 0.55)
    # filled crescent moon: solid disc minus an offset background disc
    mr = r * 0.62
    mcx, mcy = cx - r * 0.10, cy
    d.disc(mcx, mcy, mr, c)
    d.disc(mcx + mr * 0.55, mcy - mr * 0.08, mr * 0.95, bg)


def waveform(d, x0, x1, cy, c, n=54, amp=1.0, seed=3, w=2.0):
    """Audio waveform: vertical mirrored bars of varying height."""
    dx = (x1 - x0) / n
    r = seed * 2246822519 & 0xFFFFFFFF
    for i in range(n):
        r = (1103515245 * r + 12345) & 0xFFFFFFFF
        env = math.sin(i / n * math.pi) ** 0.6
        h = (0.15 + ((r >> 16) % 100) / 100.0) * amp * env
        x = x0 + i * dx
        d.line(x, cy - h, x, cy + h, c, w)


def dotted_square(d, x0, y0, x1, y1, c, cell=6.0):
    """Checkered/dotted square pattern (filled small squares alternating)."""
    nx = int(round((x1 - x0) / cell))
    ny = int(round((y1 - y0) / cell))
    for j in range(ny):
        for i in range(nx):
            if (i + j) % 2 == 0:
                px = x0 + i * cell
                py = y0 + j * cell
                # solid filled square: a short vertical stroke of width ~cell so
                # it covers the cell (a zero-length line renders as nothing)
                d.rect(px + cell * 0.5, py + cell * 0.15, px + cell * 0.5,
                       py + cell * 0.85, c, cell * 0.95)


def progress_asterisks(d, x0, y0, x1, y1, c, filled=0.55):
    """Percent bar whose FILLED portion is packed with asterisks (clipped to
    the bar), an empty remainder, and a divider at the fill line."""
    d.rect(x0, y0, x1, y1, c, 1.6)
    h = y1 - y0
    fh = h * 0.6
    fx = x0 + (x1 - x0) * filled
    # pack asterisks only up to the fill line
    aw = d.text_width("* ", fh)
    n = max(1, int((fx - x0 - 6) / max(aw, 1)))
    d.text("* " * n, x0 + 4, y0 + h * 0.15, fh, c)
    d.line(fx, y0, fx, y1, c, 2.0)


def slot_tab(d, x0, y0, x1, y1, c, fill=None):
    """Small notched tab (top corner cut)."""
    pts = [(x0, y1), (x0, y0 + (y1 - y0) * 0.5), (x0 + 5, y0), (x1, y0), (x1, y1)]
    if fill is not None:
        _poly_fill(d, pts, fill)
    d.poly(pts, c, 1.6, closed=True)


def loading_blocks(d, x0, y0, x1, y1, c, filled=6, total=14):
    """Blocky/dashed progress bar of dark rectangles."""
    total_w = x1 - x0
    bw = total_w / total
    for i in range(total):
        px0 = x0 + i * bw
        px1 = px0 + bw * 0.7
        if i < filled:
            d.rect((px0 + px1) * 0.5, (y0 + y1) * 0.5, (px0 + px1) * 0.5, (y0 + y1) * 0.5,
                   c, y1 - y0)
        else:
            d.rect(px0, y0, px1, y1, c, 1.2)


# =====================================================================
#  BUILD
# =====================================================================
def build(d, W, H, t=0.0):
    def X(f):
        return f * W

    def Y(f):
        return f * H

    _panel_top_left(d, W, H, X, Y)
    _panel_top_right(d, W, H, X, Y)
    _panel_bottom_left(d, W, H, X, Y)
    _panel_bottom_right(d, W, H, X, Y)


LOREM = "LOREM IPSUM DOLOR SIT AMET, CONSECTETUR ADIPISCING ELIT."
LOREM2 = ("LOREM IPSUM DOLOR SIT AMET, CONSECTETUR ADIPISCING ELIT, SED DO "
          "EIUSMOD TEMPOR INCIDIDUNT UT LABORE ET DOLORE MAGNA ALIQUA. UT ENIM "
          "AD MINIM VENIAM, QUIS NOSTRUD EXERCITATION ULLAMCO LABORIS NISI UT "
          "ALIQUIP EX EA COMMODO CONSEQUAT. QUIS AUTE IRURE DOLOR IN")


# ---------------------------------------------------------------- PANEL 1
def _panel_top_left(d, W, H, X, Y):
    x0, y0, x1, y1 = X(0.018), Y(0.045), X(0.492), Y(0.415)
    cut = 22.0
    # AGGRESSIVELY ANGULAR body. Right edge has a rectangular NOTCH (steps IN
    # then back OUT); bottom-right & top-right are 45deg chamfers; bottom-left
    # has a stepped notch that juts down-out.
    step = 34.0        # width of the bottom-left step
    stepd = 24.0       # depth the step drops
    ntop = y0 + (y1 - y0) * 0.30   # right-edge notch top
    nbot = y0 + (y1 - y0) * 0.62   # right-edge notch bottom
    nin = 22.0                     # how far the notch steps in
    body = [
        (x0, y0),                       # top-left
        (x1 - cut, y0),                 # top edge
        (x1, y0 + cut),                 # top-right chamfer
        (x1, ntop),                     # right edge (upper)
        (x1 - nin, ntop + 6),           # step IN
        (x1 - nin, nbot - 6),           # down the inner face
        (x1, nbot),                     # step back OUT
        (x1, y1 - cut),                 # right edge (lower)
        (x1 - cut, y1),                 # bottom-right chamfer
        (x0 + step + stepd, y1),        # bottom edge to the step
        (x0 + step, y1 + stepd),        # step drops down-out
        (x0, y1 + stepd),               # to left edge (lower)
        (x0, y0),                       # up the left edge
    ]
    _poly_fill(d, body, YEL)
    d.poly(body, BLK, 2.6, closed=True)

    # FULL-WIDTH black header bar with an ANGLED right end
    hy0, hy1 = y0, y0 + (y1 - y0) * 0.175
    hbar = [(x0, hy0), (x1 - cut, hy0), (x1, hy0 + cut),
            (x1, hy1 - 6), (x1 - 10, hy1), (x0, hy1)]
    _poly_fill(d, hbar, BLK)
    d.text("WARNING", x0 + 14, hy0 + 8, (hy1 - hy0) * 0.62, YEL)
    d.text("LOREM IPSUM DOLOR SIT AMET, CONSECTETUR ADIPISCING.",
           x0 + 205, hy0 + 16, 11, YEL)
    # small corner-tick accents inside the yellow body
    corner_ticks(d, x0, hy1 + 4, x1, y1, BLK, ln=10, inset=6, w=1.4)

    # biohazard box (below-left) with DOUBLE-LINE inner frame + corner brackets
    bx0, by0 = x0 + 12, hy1 + 12
    bx1, by1 = x0 + 122, hy1 + 122
    d.rect(bx0, by0, bx1, by1, BLK, 2.6)
    # inner double-line frame
    d.rect(bx0 + 7, by0 + 7, bx1 - 7, by1 - 7, BLK, 1.4)
    # small corner brackets just inside the outer frame
    br = 12.0
    for (cxx, sx) in ((bx0 + 3, 1), (bx1 - 3, -1)):
        for (cyy, sy) in ((by0 + 3, 1), (by1 - 3, -1)):
            d.line(cxx, cyy, cxx + sx * br, cyy, BLK, 2.2)
            d.line(cxx, cyy, cxx, cyy + sy * br, BLK, 2.2)
    biohazard(d, (bx0 + bx1) * 0.5, (by0 + by1) * 0.5, 40, BLK, 3.0)

    # continuous ASTERISK row as its own clean line ABOVE the cells
    mx0 = bx1 + 20
    astery = hy1 + 8
    d.text("* " * 26, mx0, astery, 11, BLK)

    # mode selector A1..A4 — TALLER portrait cells with a -MODE- connector tab
    # on top of each, and BOTTOM corners cut at an angle
    my0 = astery + 22
    cellw = 52
    cellh = 96
    gap = 8
    bc = 10.0        # bottom-corner angled cut
    labels = ["A1", "A2", "A3", "A4"]
    for i, lab in enumerate(labels):
        cx0 = mx0 + i * (cellw + gap)
        cx1 = cx0 + cellw
        cy0 = my0
        cy1 = my0 + cellh
        # -MODE- connector tab bridging the top of each cell
        tabw = 34
        tabcx = (cx0 + cx1) * 0.5
        d.line(tabcx, cy0 - 10, tabcx, cy0, BLK, 1.4)           # stem into cell
        d.rect(tabcx - tabw * 0.5, cy0 - 18, tabcx + tabw * 0.5, cy0 - 10, BLK, 1.4)
        d.text("-MODE-", tabcx, cy0 - 17, 6.0, BLK, align="center")
        # cell body: top square, BOTTOM corners chamfered
        highlight = (i == 1)
        col = CHAR_HI if highlight else CHAR
        cell = [(cx0, cy0), (cx1, cy0), (cx1, cy1 - bc), (cx1 - bc, cy1),
                (cx0 + bc, cy1), (cx0, cy1 - bc)]
        _poly_fill(d, cell, col)
        # A2 gets a bright outline; others a dark outline
        ocol = YEL if highlight else BLK
        d.poly(cell, ocol, 2.4 if highlight else 1.6, closed=True)
        tcol = YEL if highlight else YEL_D
        d.text(lab, tabcx, cy0 + cellh * 0.30, 30, tcol, align="center")

    # paragraph of small filler text (right of the mode cells)
    ax0 = mx0 + 4 * (cellw + gap) + 6
    px = ax0
    py0 = astery - 2
    plines = [
        "LOREM IPSUM DOLOR SIT AMET,",
        "CONSECTETUR ADIPISCING ELIT.",
        "SED DO EIUSMOD TEMPOR",
        "INCIDIDUNT UT LABORE ET DOLORE",
        "MAGNA ALIQUA. UT ENIM AD MINIM",
        "VENIAM, QUIS NOSTRUD",
    ]
    for i, ln in enumerate(plines):
        d.text(ln, px, py0 + i * 11, 7.5, BLK)

    # horizontal progress/percent bar filled with asterisks — sits lower-right,
    # aligned with the bottom of the mode cells
    pbx0, pby0 = ax0, my0 + cellh - 22
    pbx1, pby1 = x1 - 46, my0 + cellh - 6
    progress_asterisks(d, pbx0, pby0, pbx1, pby1, BLK, filled=0.6)


# ---------------------------------------------------------------- PANEL 2
def _panel_top_right(d, W, H, X, Y):
    x0, y0, x1, y1 = X(0.532), Y(0.045), X(0.982), Y(0.40)
    cut = 16.0
    # ANGULAR body: chamfered top-left, a STEPPED top-right corner (drops down
    # into a small control-glyph shelf), chamfered bottom-right, and a small
    # notch on the LEFT edge.
    nly = y0 + (y1 - y0) * 0.55        # left-edge notch center
    body = [
        (x0 + 12, y0),                 # top-left chamfer start
        (x1 - 96, y0),                 # top edge
        (x1 - 78, y0 + 16),            # step DOWN to the glyph shelf
        (x1 - cut, y0 + 16),
        (x1, y0 + 16 + cut),           # top-right chamfer (lower, stepped)
        (x1, y1 - cut),                # right edge
        (x1 - cut, y1),                # bottom-right chamfer
        (x0 + 10, y1),                 # bottom edge
        (x0, y1 - 10),                 # bottom-left chamfer
        (x0, nly + 14),                # left edge (lower)
        (x0 + 12, nly),                # notch IN
        (x0, nly - 14),                # notch OUT
        (x0, y0 + 12),                 # left edge (upper)
    ]
    _poly_fill(d, body, YEL)
    d.poly(body, BLK, 2.2, closed=True)

    ix = x0 + 14
    # BLACK top strip with two SLOT-TAB cut-outs (black bar, yellow slot text)
    tbar = [(x0 + 12, y0), (x1 - 96, y0), (x1 - 84, y0 + 12), (x0 + 6, y0 + 12)]
    _poly_fill(d, tbar, BLK)
    d.text("LOREM IPSUM", ix, y0 + 1, 10, YEL)
    # slot tabs = yellow notches cut into the black strip
    _poly_fill(d, [(ix + 118, y0 + 2), (ix + 162, y0 + 2), (ix + 158, y0 + 10),
                   (ix + 118, y0 + 10)], YEL)
    d.text("SLOT 001", ix + 121, y0 + 2, 6.0, BLK)
    _poly_fill(d, [(ix + 168, y0 + 2), (ix + 212, y0 + 2), (ix + 208, y0 + 10),
                   (ix + 168, y0 + 10)], YEL)
    d.text("SLOT 002", ix + 171, y0 + 2, 6.0, BLK)

    # top-right control-glyph cluster on the stepped shelf (triangles + rect,
    # drawn from primitives, not text): [ <|  []  |> ]
    gx, gy = x1 - 72, y0 + 8
    d.tri_fill((gx, gy), (gx + 8, gy - 5), (gx + 8, gy + 5), BLK)   # left tri
    d.rect(gx + 13, gy - 5, gx + 23, gy + 5, BLK, 1.4)             # square
    d.tri_fill((gx + 36, gy), (gx + 28, gy - 5), (gx + 28, gy + 5), BLK)  # right tri
    d.line(gx + 10, gy - 6, gx + 10, gy + 6, BLK, 1.2)
    d.line(gx + 26, gy - 6, gx + 26, gy + 6, BLK, 1.2)

    # divider
    dvy = y0 + 26
    d.line(ix, dvy, x1 - 14, dvy, BLK, 2.0)
    # corner ticks inside the yellow body
    corner_ticks(d, x0, y0 + 18, x1, y1, BLK, ln=10, inset=6, w=1.4)

    midx = X(0.728)   # divider between left column and right column
    # vertical divider line between the two columns
    d.line(midx - 12, dvy + 4, midx - 12, y1 - 10, _f(BLK, 0.5), 1.2)

    # --- LEFT COLUMN ---
    # POSITION 01-05 header + dashed rule
    d.text("POSITION 01-05", ix, dvy + 8, 11, BLK)
    _dashes(d, ix + 118, dvy + 13, midx - 24, dvy + 13, BLK, dash=6, gap=5)

    # LOADING... + blocky/dashed progress bar
    ly = dvy + 26
    d.text("LOADING...", ix, ly, 15, BLK)
    loading_blocks(d, ix + 100, ly + 2, midx - 24, ly + 14, BLK, filled=5, total=13)

    # vertical list of ~7 rows (left column, no pills)
    listy = ly + 30
    for r in range(7):
        ry = listy + r * 15
        d.text("POSITION-01414141-0001", ix, ry, 8.5, BLK)

    # barcode lower-left
    barcode(d, ix, y1 - 46, ix + 110, y1 - 14, BLK, seed=7)

    # rounded Choice button (bottom of left column)
    ch0, cy0, ch1, cy1 = midx - 116, y1 - 52, midx - 24, y1 - 22
    d.rrect(ch0, cy0, ch1, cy1, 14, BLK, 2.4)
    d.text("Choice", (ch0 + ch1) * 0.5, cy0 + 6, 15, BLK, align="center")

    # --- RIGHT COLUMN ---
    rx = midx
    # MODE·TIME·GRAPH header
    d.text("MODE · TIME · GRAPH", rx, dvy + 8, 11, BLK)
    # small bar-graph / waveform tick strips top-right
    for k in range(3):
        yy = dvy + 3 + k * 6
        _tick_strip(d, rx + 138, yy, x1 - 16, yy, BLK)

    # POSITION 01-05 subheader (right)
    d.text("POSITION 01-05", rx, ly, 12, BLK)

    # 7 POSITION rows each with 3 pill indicators to the right
    for r in range(7):
        ry = listy + r * 15
        d.text("POSITION- 01414141- 0001", rx, ry, 7.0, BLK)
        for p in range(3):
            px = rx + 96 + p * 17
            d.rrect(px, ry, px + 14, ry + 8, 4.0, BLK, 1.3)

    # big WARNING + warning-triangle + OO-in-hexagon (right of pills)
    wx = rx + 160
    wy = ly + 6
    d.text("WARNING", wx, wy + 14, 19, BLK)
    warning_triangle(d, wx + 118, wy + 22, 16, BLK, 2.2)
    hexagon(d, wx + 160, wy + 22, 20, BLK, 2.2, flat=True)
    d.text("OO", wx + 160, wy + 15, 14, BLK, align="center")

    # dashed lines + hazard segments in the mid-right region
    for k in range(2):
        yy = wy + 44 + k * 9
        _dashes(d, wx + 92, yy, x1 - 22, yy, BLK)
    hazard_stripes(d, wx + 92, wy + 66, x1 - 22, wy + 82, BLK, sw=6, gap=6, w=4)

    # CODE · 17-WW-22-000 just below the panel's bottom-right (on gray, as ref)
    d.text("CODE · 17-WW-22-000", x1 - 6, y1 + 10, 12, BLK, align="right")


def _tick_strip(d, x0, y0, x1, y1, c):
    n = 22
    dx = (x1 - x0) / n
    for i in range(n):
        h = 3 if i % 2 == 0 else 6
        x = x0 + i * dx
        d.line(x, y0 - h * 0.5, x, y0 + h * 0.5, c, 1.4)


def _dashes(d, x0, y0, x1, y1, c, dash=8, gap=5):
    x = x0
    while x < x1:
        d.line(x, y0, min(x + dash, x1), y0, c, 2.4)
        x += dash + gap


# ---------------------------------------------------------------- PANEL 3
def _panel_bottom_left(d, W, H, X, Y):
    x0, y0, x1, y1 = X(0.095), Y(0.525), X(0.472), Y(0.945)
    cut = 20.0
    # MOST ANGULAR panel. Chunky STEPPED silhouette:
    #  - raised central MESA holding WARNING, with two-step shoulders dropping
    #    to thinner sides, small notches at the mesa top corners,
    #  - big 45deg chamfer at the bottom-LEFT, an angled right edge,
    #  - solid black bottom bar (added later).
    tm = 34.0          # inset of mesa top from each side (WIDE mesa)
    ts = 26.0          # mesa rise above shoulders
    bl = 46.0          # big bottom-left chamfer
    body = [
        # --- mesa top (raised block) ---
        (x0 + tm, y0 - ts),             # mesa top-left corner
        (x1 - tm, y0 - ts),             # mesa top-right corner
        # --- right shoulder: step down in two steps ---
        (x1 - tm + 12, y0 - ts + 14),   # diagonal step
        (x1 - tm + 12, y0),             # to shoulder level
        (x1 - cut, y0),                 # top edge (thin right side)
        (x1, y0 + cut),                 # top-right chamfer
        (x1 - 5, y0 + cut + 44),        # angled right edge (juts in)
        (x1, y0 + cut + 88),
        (x1, y1 - cut),                 # right edge (lower)
        (x1 - cut, y1),                 # bottom-right chamfer
        (x0 + bl, y1),                  # bottom edge
        (x0, y1 - bl),                  # BIG 45deg bottom-left chamfer
        (x0, y0 + cut),                 # left edge
        (x0 + cut, y0),                 # top-left chamfer
        # --- left shoulder: step up in two steps ---
        (x0 + tm - 12, y0),             # to shoulder
        (x0 + tm - 12, y0 - ts + 14),   # diagonal step up
        (x0 + tm, y0 - ts),             # up to mesa
    ]
    _poly_fill(d, body, YEL)
    d.poly(body, BLK, 2.6, closed=True)
    # thin raised sub-bar with tick marks above the mesa center
    sbx0, sbx1 = X(0.235) - 70, X(0.235) + 70
    d.line(sbx0, y0 - ts - 6, sbx1, y0 - ts - 6, BLK, 1.6)
    _tick_strip(d, sbx0 + 6, y0 - ts - 12, sbx1 - 6, y0 - ts - 12, BLK)
    # DOUBLE-LINE inner border echo
    d.poly([(x0 + cut + 7, y0 + 7), (x1 - cut - 7, y0 + 7), (x1 - 7, y0 + cut + 7),
            (x1 - 7, y1 - cut - 7), (x1 - cut - 7, y1 - 7), (x0 + bl + 4, y1 - 7),
            (x0 + 7, y1 - bl - 4), (x0 + 7, y0 + cut + 7)], BLK, 1.2, closed=True)
    # corner-tick accents
    corner_ticks(d, x0 + 4, y0 + 4, x1 - 4, y1 - 26, BLK, ln=11, inset=10, w=1.5)

    # big WARNING flanked by DOT-MATRIX CHECKER blocks (left AND right)
    hy = y0 + 22
    wsz = 36
    wtext_w = d.text_width("WARNING", wsz)
    wcx = X(0.235)
    dm_gap = 16
    dm_w = 42
    # left checker block (ends just before the WARNING text)
    dxl1 = wcx - wtext_w * 0.5 - dm_gap
    dotted_square(d, dxl1 - dm_w, hy + 6, dxl1, hy + 30, BLK, cell=6)
    d.text("WARNING", wcx, hy, wsz, BLK, align="center")
    # right checker block (starts just after the WARNING text)
    dxr0 = wcx + wtext_w * 0.5 + dm_gap
    dotted_square(d, dxr0, hy + 6, dxr0 + dm_w, hy + 30, BLK, cell=6)

    # paragraph of filler text
    py = hy + 54
    lines = [
        "LOREM IPSUM DOLOR SIT AMET, CONSECTETUR ADIPISCING ELIT. SED DO",
        "EIUSMOD TEMPOR INCIDIDUNT UT LABORE ET DOLORE MAGNA ALIQUA. UT ENIM",
        "AD MINIM VENIAM, QUIS NOSTRUD EXERCITATION ULLAMCO LABORIS NISI UT",
        "ALIQUIP EX EA COMMODO CONSEQUAT. QUIS AUTE IRURE DOLOR IN",
    ]
    for i, ln in enumerate(lines):
        d.text(ln, x0 + 26, py + i * 15, 9, BLK)

    # [SET-01] tag at right
    tg0, tg1 = x1 - 96, py
    d.rect(tg0, tg1, x1 - 26, tg1 + 18, BLK, 2.0)
    d.text("[SET-01]", tg0 + 6, tg1 + 3, 12, BLK)
    # a couple of small dash/tick marks below the [SET-01] tag (replaces the
    # old keypad grid — the ref only has a few dashes here)
    for k in range(2):
        dy = tg1 + 26 + k * 7
        _dashes(d, tg0, dy, x1 - 26, dy, BLK, dash=7, gap=4)

    # --- MID region: hazard box (mid-left-center) + barcode to its RIGHT ---
    midy = py + 74
    # diagonal hazard-stripe block on the FAR-LEFT edge (as in the ref)
    hzl0, hzl1 = x0 + 26, x0 + 118
    d.rect(hzl0, midy + 4, hzl1, midy + 20, BLK, 1.8)
    hazard_stripes(d, hzl0 + 2, midy + 6, hzl1 - 2, midy + 18, BLK, sw=6, gap=6, w=4)
    d.rect(hzl0, midy + 26, hzl1, midy + 42, BLK, 1.8)
    hazard_stripes(d, hzl0 + 2, midy + 28, hzl1 - 2, midy + 40, BLK, sw=6, gap=6, w=4)

    # warning-triangle inside hazard-striped box (mid-left-center)
    wb0, wby0 = X(0.235), midy
    wb1, wby1 = X(0.235) + 66, midy + 78
    d.rect(wb0, wby0, wb1, wby1, BLK, 2.0)
    hazard_stripes(d, wb0 + 2, wby0 + 2, wb1 - 2, wby0 + 18, BLK, sw=6, gap=6, w=4)
    hazard_stripes(d, wb0 + 2, wby1 - 18, wb1 - 2, wby1 - 2, BLK, sw=6, gap=6, w=4)
    d.text("WARNING", (wb0 + wb1) * 0.5, wby0 + 20, 7, BLK, align="center")
    warning_triangle(d, (wb0 + wb1) * 0.5, (wby0 + wby1) * 0.5 + 8, 16, BLK, 2.2)

    # LONG horizontal barcode to the RIGHT of the hazard box (center/right)
    bcx0 = wb1 + 16
    bcx1 = x1 - 40
    barcode(d, bcx0, midy + 2, bcx1, midy + 54, BLK, seed=11)
    # ERROR-SYSTEM small text below the barcode
    d.text("-ERROR-SYSTEM- 0x0000000", (bcx0 + bcx1) * 0.5, midy + 60, 9,
           _f(BLK, 0.7), align="center")
    # thin PROGRESS/segment bar (one filled segment) below the barcode
    prx0, pry0 = bcx0, midy + 74
    prx1, pry1 = bcx1, midy + 82
    d.rect(prx0, pry0, prx1, pry1, BLK, 1.6)
    fillx = prx0 + (prx1 - prx0) * 0.18
    _poly_fill(d, [(prx0, pry0), (fillx, pry0), (fillx, pry1), (prx0, pry1)], BLK)

    # DIAGONAL HAZARD STRIPES along the frame's bottom-right edge + small solid
    # black rectangles
    hzr0, hzr1 = x1 - 70, x1 - 14
    hzry0, hzry1 = y1 - 92, y1 - 26
    hazard_stripes(d, hzr0, hzry0, hzr1, hzry1, BLK, sw=8, gap=8, w=6)
    d.line(hzr0, hzry0, hzr0, hzry1, BLK, 1.6)
    d.rect(hzr1 + 4, hzry0 + 6, hzr1 + 10, hzry0 + 22, BLK, 2.0)
    _poly_fill(d, [(hzr1 + 4, hzry0 + 6), (hzr1 + 10, hzry0 + 6),
                   (hzr1 + 10, hzry0 + 22), (hzr1 + 4, hzry0 + 22)], BLK)

    # X mark bottom-left (above the black bar)
    d.text("X", x0 + 44, y1 - 52, 22, BLK)

    # THICK solid BLACK bar along the bottom edge (defining feature)
    bby0 = y1 - 20
    _poly_fill(d, [(x0 + cut + 6, bby0), (x1 - cut - 6, bby0),
                   (x1 - cut, y1 - 3), (x0 + cut, y1 - 3)], BLK)


# ---------------------------------------------------------------- PANEL 4
def _panel_bottom_right(d, W, H, X, Y):
    x0, y0, x1, y1 = X(0.518), Y(0.500), X(0.988), Y(0.965)
    r = 24.0                       # chamfer size (hard 45deg, not rounded)
    ylo = y0 + 20                  # lower top-edge level (left side, near "01")
    yhi = y0 - 6                   # raised top-edge level (right, FUTURISTIC)
    xstep = X(0.78)                # x where the top edge steps UP
    tabx = X(0.60)                 # left "01" raised tab
    ery0 = y1 - 44                 # bottom-right ERROR pill notch top
    body = [
        # --- stepped top edge: low on the left, stepping UP to the right ---
        (x0 + r, ylo),                 # top-left chamfer end
        (tabx - 24, ylo),              # to the 01-tab
        (tabx - 16, ylo - 12),         # raised 01 tab (up)
        (tabx + 40, ylo - 12),
        (tabx + 48, ylo),              # back down from tab
        (xstep - 14, ylo),             # top edge (low)
        (xstep, yhi),                  # STEP UP diagonal
        (x1 - r, yhi),                 # raised top edge (right)
        (x1, yhi + r),                 # top-right chamfer
        (x1, ery0),                    # right edge
        (x1 - 18, ery0 + 8),           # notch IN for the ERROR pill
        (x1 - 18, y1 - r),
        (x1 - r - 18, y1),             # bottom edge (right, inside notch)
        (x0 + r, y1),                  # bottom edge
        (x0, y1 - r),                  # bottom-left chamfer
        (x0, ylo + r),                 # left edge
    ]
    _poly_fill(d, body, YEL)
    d.poly(body, BLK, 2.6, closed=True)
    # corner-tick accents inside
    corner_ticks(d, x0 + 2, ylo + 4, x1 - 20, y1 - 4, BLK, ln=11, inset=10, w=1.5)

    # small 01 tab label (on the raised left tab)
    d.text("01", tabx - 8, ylo - 14, 16, BLK)
    # FUTURISTIC big headline top-right
    d.text("FUTURISTIC", x1 - 16, yhi + 6, 34, BLK, align="right")
    # small bar-graph top-right corner
    _tick_strip(d, x1 - 60, y0 + 40, x1 - 16, y0 + 40, BLK)

    # bar of diagonal hazard stripes near top
    hz0 = X(0.545)
    hazard_stripes(d, hz0, y0 + 40, X(0.735), y0 + 58, BLK, sw=9, gap=9, w=7)
    d.rect(hz0, y0 + 40, X(0.735), y0 + 58, BLK, 2.0)

    # crescent moon in gridded globe (left)
    crescent_globe(d, X(0.585), Y(0.755), 40, BLK, 2.2)

    # dark box with 7-seg timecode + warning triangle
    tb0, tby0 = X(0.635), Y(0.685)
    tb1, tby1 = X(0.755), Y(0.735)
    _poly_fill(d, [(tb0, tby0), (tb1 - 8, tby0), (tb1, tby0 + 8), (tb1, tby1), (tb0, tby1)], CHAR)
    d.poly([(tb0, tby0), (tb1 - 8, tby0), (tb1, tby0 + 8), (tb1, tby1), (tb0, tby1)], BLK, 1.6, closed=True)
    d.text("00:01:02", (tb0 + tb1) * 0.5, tby0 + 12, 26, YEL, align="center")
    warning_triangle(d, tb1 + 18, (tby0 + tby1) * 0.5, 14, BLK, 2.0)
    d.text("WARNING", tb1 + 6, tby1 + 2, 6, BLK)

    # crosshair / target reticle
    rx, ry = X(0.735), Y(0.80)
    rr = 26
    d.ring(rx, ry, rr, BLK, 1.8)
    d.line(rx - rr * 1.6, ry, rx + rr * 1.6, ry, BLK, 1.4)
    d.line(rx, ry - rr * 1.6, rx, ry + rr * 1.6, BLK, 1.4)
    for k in range(4):
        a = k * math.pi / 2
        d.line(rx + math.cos(a) * rr * 0.4, ry + math.sin(a) * rr * 0.4,
               rx + math.cos(a) * rr * 0.9, ry + math.sin(a) * rr * 0.9, BLK, 1.2)

    # audio waveform on the right
    waveform(d, X(0.80), x1 - 20, Y(0.735), BLK, n=60, amp=34, seed=5, w=2.0)

    # paragraph of filler
    py = Y(0.745)
    plines = [
        "LOREM IPSUM DOLOR SIT",
        "AMET, CONSECTETUR",
        "ADIPISCING ELIT, SED DO",
        "EIUSMOD TEMPOR",
        "INCIDIDUNT UT LABORE ET",
        "DOLORE MAGNA ALIQUA. UT",
        "ENIM AD MINIM VENIAM",
    ]
    for i, ln in enumerate(plines):
        d.text(ln, X(0.635), py + i * 12, 8.5, BLK)

    # 002_SYSTEM
    d.text("002_SYSTEM", X(0.775), Y(0.87), 15, BLK)
    for i in range(5):
        d.text("00170001    2000407", X(0.775), Y(0.895) + i * 9, 6.5, BLK)

    # rounded ERROR pill bottom-right with a notch
    eb0, eby0 = x1 - 130, y1 - 40
    eb1, eby1 = x1 - 16, y1 - 12
    _poly_fill(d, [(eb0 + 14, eby0), (eb1 - 14, eby0), (eb1, eby0 + 14),
                   (eb1, eby1), (eb0, eby1), (eb0, eby0 + 14)], CHAR)
    d.poly([(eb0 + 14, eby0), (eb1 - 14, eby0), (eb1, eby0 + 14),
            (eb1, eby1), (eb0, eby1), (eb0, eby0 + 14)], BLK, 1.8, closed=True)
    d.text("ERROR", (eb0 + eb1) * 0.5, eby0 + 6, 16, YEL, align="center")


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _ref_render import render_png, save_compare
    REF = "C:/Users/antho/Downloads/arcv/examples/refs/gallery/ref1_reference.webp"
    here = os.path.dirname(os.path.abspath(__file__))
    render_path = render_png(build, "gallery/ref1.png", size=(1277, 605), mode="flat",
                             base_color=(0.82, 0.82, 0.82, 1.0))
    save_compare(REF, render_path, os.path.join(here, "gallery/ref1_compare.png"), "REF1")
    print("done ->", render_path)
