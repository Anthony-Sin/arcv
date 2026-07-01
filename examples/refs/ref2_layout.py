"""ref2 — recreation of a print-style cyberpunk HUD poster (crisp white line
art on black), three vertical columns.

LEFT   : giant vertical CYBERPUNK type + hatched banner + wireframe TERRAIN
         mountain + barcode + database tag + small globe/oval/line-chart.
MIDDLE : boxed FUTURISTIC header (biohazard, 7-seg timecode, trefoil, barcode)
         + wireframe BODY in an arched capsule + 06_LOREAM2K4 meters +
         seismograph readouts + LOADING bar.
RIGHT  : 01 tab + MAIN MENU headline + wireframe GLOBE/VORTEX swirl + step-bar
         graph + buttons + ERROR-SYSTEM / LOADING hazard footer.

Rendered flat (opaque, no bloom) to match the vector-poster look.
All coordinates are absolute pixels for a 1307x547 canvas.
"""

from __future__ import annotations

import math

# ---- palette -------------------------------------------------------------
W_ = (0.95, 0.97, 1.0, 1.0)      # main white line
W_DIM = (0.78, 0.82, 0.88, 1.0)  # dimmer white / grey line
W_FAINT = (0.55, 0.60, 0.68, 1.0)
GREY = (0.45, 0.48, 0.55, 1.0)
RED = (0.90, 0.15, 0.15, 1.0)
BLACK = (0.0, 0.0, 0.0, 1.0)


# =========================================================================
# LOW-LEVEL GLYPH / TEXTURE HELPERS
# =========================================================================

def hazard_stripes(d, x0, y0, x1, y1, c, sw=8.0, gap=8.0, w=1.6, ang=1):
    """Fill a rectangle with diagonal hazard stripes (clipped to the box).
    ang=+1 => stripes go up-right, ang=-1 => down-right."""
    bw = x1 - x0
    bh = y1 - y0
    step = sw + gap
    # sweep offset from far left of the diagonal family
    start = -bh
    off = start
    while off < bw + bh:
        # line: from (x0+off, y1) going up-right (slope 1) => (x0+off+bh, y0)
        if ang > 0:
            ax, ay = x0 + off, y1
            bx, by = x0 + off + bh, y0
        else:
            ax, ay = x0 + off, y0
            bx, by = x0 + off + bh, y1
        # clip to box
        seg = _clip_seg(ax, ay, bx, by, x0, y0, x1, y1)
        if seg:
            d.line(seg[0], seg[1], seg[2], seg[3], c, w)
        off += step


def _clip_seg(x0, y0, x1, y1, cx0, cy0, cx1, cy1):
    """Liang-Barsky clip a segment to an axis-aligned box. Returns tuple or None."""
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


def barcode(d, x0, y0, x1, y1, c, seed=1, dense=1.0):
    """Vertical barcode: variable-width bars across the width."""
    x = x0
    i = seed
    while x < x1:
        i = (i * 1103515245 + 12345) & 0x7fffffff
        bw = 1.0 + (i >> 8) % 4
        gap = 1.0 + (i >> 3) % 3
        if (i >> 5) % 5 != 0:  # occasionally skip -> a gap
            d.rect(x, y0, min(x + bw, x1), y1, c, 0.0) if False else None
            _fill_rect(d, x, y0, min(x + bw, x1), y1, c)
        x += bw + gap


def _fill_rect(d, x0, y0, x1, y1, c):
    """Solid filled rectangle via rrect_fill with 0 radius."""
    d.rrect_fill(x0, y0, x1, y1, 0.0, c)


def warning_triangle(d, cx, cy, sz, c, w=1.6):
    d.tri((cx, cy - sz), (cx - sz * 0.92, cy + sz * 0.8),
          (cx + sz * 0.92, cy + sz * 0.8), c, w)
    d.line(cx, cy - sz * 0.25, cx, cy + sz * 0.35, c, w)
    d.disc(cx, cy + sz * 0.58, max(1.0, w * 0.9), c)


def radiation_trefoil(d, cx, cy, r, c):
    """Radiation symbol: 3 wedges + hub."""
    d.disc(cx, cy, r * 0.22, c)
    for k in range(3):
        a0 = -math.pi / 2 + k * (2 * math.pi / 3) - 0.55
        a1 = a0 + 1.10
        # wedge as filled fan of triangles between r*0.35 and r
        n = 6
        for i in range(n):
            b0 = a0 + (a1 - a0) * i / n
            b1 = a0 + (a1 - a0) * (i + 1) / n
            p0 = (cx + math.cos(b0) * r * 0.34, cy + math.sin(b0) * r * 0.34)
            p1 = (cx + math.cos(b0) * r, cy + math.sin(b0) * r)
            p2 = (cx + math.cos(b1) * r, cy + math.sin(b1) * r)
            p3 = (cx + math.cos(b1) * r * 0.34, cy + math.sin(b1) * r * 0.34)
            d.tri_fill(p0, p1, p2, c)
            d.tri_fill(p0, p2, p3, c)


def biohazard(d, cx, cy, r, c, w=1.6):
    """Biohazard: 3 overlapping rings arranged around center + inner motif."""
    for k in range(3):
        a = -math.pi / 2 + k * (2 * math.pi / 3)
        rx = cx + math.cos(a) * r * 0.62
        ry = cy + math.sin(a) * r * 0.62
        d.ring(rx, ry, r * 0.52, c, w)
    d.ring(cx, cy, r * 0.30, c, w)
    d.disc(cx, cy, r * 0.10, c)


def icon_box_slash(d, x0, y0, x1, y1, c, w=1.4, slash=True):
    d.rect(x0, y0, x1, y1, c, w)
    if slash:
        d.line(x0, y1, x1, y0, c, w)


def small_box_glyph(d, x0, y0, x1, y1, c, w=1.4):
    """A box with an X inside (approximates the ☒ glyph)."""
    d.rect(x0, y0, x1, y1, c, w)
    d.line(x0, y0, x1, y1, c, w)
    d.line(x0, y1, x1, y0, c, w)


def loading_bar(d, x0, y0, x1, y1, frac, c, w=1.4):
    d.rect(x0, y0, x1, y1, c, w)
    inner = x0 + (x1 - x0) * frac
    _fill_rect(d, x0 + 2, y0 + 2, inner, y1 - 2, c)


def step_bar_graph(d, x0, y0, x1, y1, c, w=1.4):
    """Rising step bars of increasing height, left->right."""
    n = 10
    bw = (x1 - x0) / n
    for i in range(n):
        h = (y1 - y0) * (0.12 + 0.88 * (i / (n - 1)))
        bx0 = x0 + i * bw + bw * 0.12
        bx1 = x0 + (i + 1) * bw - bw * 0.12
        _fill_rect(d, bx0, y1 - h, bx1, y1, c)


def seismograph_trace(d, x0, y0, x1, y1, c, seed=1, w=1.4):
    """A dense jagged waveform inside a box, symmetric-ish envelope."""
    cy = (y0 + y1) * 0.5
    amp = (y1 - y0) * 0.5
    pts = []
    n = 90
    i = seed
    for k in range(n):
        u = k / (n - 1)
        i = (i * 1103515245 + 12345) & 0x7fffffff
        rnd = ((i >> 6) % 1000) / 1000.0 - 0.5
        # envelope: taper at the edges, bulge in the middle
        env = math.sin(math.pi * u) ** 0.6
        y = cy + rnd * amp * 1.9 * env
        pts.append((x0 + u * (x1 - x0), y))
    d.poly(pts, c, w)


def dot_matrix(d, x0, y0, cols, rows, cell, c, seed=7, r=1.2, fill=0.5):
    """A grid of dots; pseudo-random subset filled."""
    i = seed
    for cy in range(rows):
        for cx in range(cols):
            i = (i * 1103515245 + 12345) & 0x7fffffff
            if ((i >> 7) % 100) / 100.0 < fill:
                d.disc(x0 + cx * cell, y0 + cy * cell, r, c)


# =========================================================================
# WIREFRAME HEROES
# =========================================================================

def _terrain_height(i, j):
    """Deterministic pseudo-height field: a BROAD mountain RANGE — one tall-ish
    central peak flanked by several medium rolling peaks that fill the whole
    footprint. i=across(0..1), j=depth(0..1, 1=far)."""
    # tallest peak (central, slightly left) — one clear summit above the range
    peak = math.exp(-(((i - 0.44) * 3.8) ** 2 + ((j - 0.64) * 2.8) ** 2)) * 1.35
    # a cluster of medium peaks spread across the range
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
    # rolling ripple that covers everything (mid-frequency hills)
    ripple = (math.sin(i * 9.0 + 0.5) * math.sin(j * 8.0 + 1.3) * 0.55
              + math.sin(i * 15.0 + 1.1) * math.sin(j * 13.0 + 2.1) * 0.35
              + math.sin(i * 27.0 + j * 8.0) * 0.18)
    # a raised rolling base so the whole width has terrain (a range, not a spike)
    base = 0.30 + 0.16 * math.sin(i * 6.0 + 0.7) + 0.10 * math.sin(i * 11.0 + j * 4.0)
    foot = 0.14 * (1.0 - j) * (0.5 + 0.5 * math.sin(i * 17.0 + 1.0))
    return acc + 0.16 * ripple + base + foot


def wireframe_terrain(d, x, y, w, h, c):
    """A 3D mountain/terrain mesh drawn as row + column polylines in a tilted
    perspective (rows shift up-right by row index)."""
    NX = 64   # columns (across)
    NY = 46   # rows (depth)
    # perspective: near rows (small j) at bottom, far rows at top-right
    depth_dx = w * 0.07   # each far row shifts right
    depth_dy = h * 0.40   # far rows compressed toward the top
    amp = h * 0.34
    z0 = 0.30             # baseline height subtracted so range sits low

    def proj(i, j):
        u = i / (NX - 1)      # 0..1 across
        v = j / (NY - 1)      # 0..1 depth (0 near/bottom, 1 far/top)
        # near rows wider than far rows (perspective converge)
        conv = 1.0 - v * 0.12
        px = x + w * 0.03 + (u - 0.5) * w * conv + 0.5 * w + v * depth_dx
        base_y = y + h - v * depth_dy
        height = _terrain_height(u, v) - z0
        py = base_y - height * amp
        return (px, py)

    grid = [[proj(i, j) for i in range(NX)] for j in range(NY)]
    # draw from far (top) to near (bottom) so near overdraws far
    for j in range(NY - 1, -1, -1):
        # row line
        d.poly(grid[j], c, 1.0)
    for i in range(NX):
        col = [grid[j][i] for j in range(NY)]
        d.poly(col, c, 1.0)


def _mesh_strip(d, ribs, c, lw, ncol, diag=False):
    """Draw a quad-mesh strip. `ribs` is a list of (cx, y, half_width). Each rib
    becomes a horizontal row of ncol+1 points; draw the rows, the two side
    edges, ncol+1 vertical connectors, and (if diag) one diagonal per quad so
    the mesh looks triangulated."""
    arrs = []
    for (rcx, y, hw) in ribs:
        arrs.append([(rcx - hw + 2 * hw * k / ncol, y) for k in range(ncol + 1)])
    for a in arrs:
        d.poly(a, c, lw)
    for k in range(ncol + 1):
        d.poly([arrs[j][k] for j in range(len(arrs))], c, lw)
    if diag:
        for j in range(len(arrs) - 1):
            for k in range(ncol):
                # alternate diagonal direction per cell for a woven look
                if (j + k) % 2 == 0:
                    p, q = arrs[j][k], arrs[j + 1][k + 1]
                else:
                    p, q = arrs[j][k + 1], arrs[j + 1][k]
                d.line(p[0], p[1], q[0], q[1], c, lw * 0.7)
    return arrs


def wireframe_body(d, cx, cy, bh, c):
    """Front-facing human as a scanned-mannequin quad mesh: head, T-pose torso
    with arms out, and two legs. cy = vertical centre of the figure; bh = total
    body height (head-top to feet)."""
    s = bh / 360.0
    lw = 0.7

    def Y(v):
        return cy + v * s

    def Xhw(v):
        return v * s

    # ---------- HEAD ----------
    hr = 18 * s
    hcy = cy - 165 * s
    d.poly([(cx + math.cos(a) * hr * 0.8, hcy + math.sin(a) * hr)
            for a in [2 * math.pi * k / 24 for k in range(25)]], c, 0.9)
    d.line(cx, hcy - hr, cx, hcy + hr, c, lw)
    d.line(cx - hr * 0.8, hcy, cx + hr * 0.8, hcy, c, lw)
    # neck
    d.line(cx - 8 * s, Y(-148), cx - 8 * s, Y(-138), c, lw)
    d.line(cx + 8 * s, Y(-148), cx + 8 * s, Y(-138), c, lw)

    # ---------- TORSO (shoulders -> hips) ----------
    torso = [
        (cx, Y(-138), Xhw(20)),   # base of neck
        (cx, Y(-128), Xhw(46)),   # shoulders (widest)
        (cx, Y(-112), Xhw(40)),   # chest top
        (cx, Y(-96), Xhw(37)),    # chest
        (cx, Y(-78), Xhw(33)),    # ribs
        (cx, Y(-58), Xhw(29)),    # waist
        (cx, Y(-40), Xhw(28)),    # lower waist
        (cx, Y(-22), Xhw(33)),    # hips top
        (cx, Y(-4), Xhw(40)),     # hips widest
    ]
    _mesh_strip(d, torso, c, lw, 8, diag=True)

    # ---------- ARMS (out to the sides, angled slightly down) ----------
    for sgn in (-1, 1):
        pts_top, pts_bot = [], []
        arm = [(46, -128, 13), (78, -118, 10), (108, -104, 8), (128, -90, 6)]
        for (dx, dy, th) in arm:
            px = cx + sgn * dx * s
            py = Y(dy)
            pts_top.append((px, py - th * s))
            pts_bot.append((px, py + th * s))
        d.poly(pts_top, c, lw)
        d.poly(pts_bot, c, lw)
        for i in range(len(pts_top)):
            d.line(pts_top[i][0], pts_top[i][1], pts_bot[i][0], pts_bot[i][1], c, lw)
        # hand
        hx, hy = cx + sgn * 132 * s, Y(-88)
        d.disc(hx, hy, 3.5 * s, c)

    # ---------- LEGS (two columns, small centre gap) ----------
    for sgn in (-1, 1):
        lcx = cx + sgn * 15 * s
        leg = [(-4, 20), (22, 19), (48, 16), (78, 13),
               (108, 11), (134, 10), (156, 10)]  # (y, half_width)
        ribs = [(lcx, Y(y), Xhw(hw)) for (y, hw) in leg]
        _mesh_strip(d, ribs, c, lw, 4, diag=True)
        # foot
        fy = Y(156)
        d.poly([(lcx - 10 * s, fy), (lcx - 13 * s, fy + 10 * s),
                (lcx + 8 * s, fy + 10 * s), (lcx + 10 * s, fy)], c, lw, closed=True)


def wireframe_globe(d, cx, cy, r, c, vortex=False, w=1.0):
    """A sphere drawn as latitude rings (ellipses) + longitude meridians.
    If vortex, the rings collapse toward an off-centre funnel and the meridians
    spiral inward (whirlpool / black-hole look)."""
    if not vortex:
        _plain_sphere(d, cx, cy, r, c, w)
    else:
        _vortex_sphere(d, cx, cy, r, c, w)


def _plain_sphere(d, cx, cy, r, c, w):
    n_lat, n_lon = 9, 14
    tilt = 0.34
    rings = []
    for li in range(1, n_lat):
        phi = math.pi * li / n_lat
        yy = cy - r * math.cos(phi)
        rw = r * math.sin(phi)
        rh = r * tilt * math.sin(phi)
        rings.append((cx, yy, rw, rh))
        d.poly([(cx + math.cos(a) * rw, yy + math.sin(a) * rh)
                for a in [2 * math.pi * k / 48 for k in range(49)]], c, w)
    top = (cx, cy - r)
    bot = (cx, cy + r)
    for lo in range(n_lon):
        a = 2 * math.pi * lo / n_lon
        pts = [top] + [(ccx + math.cos(a) * rw, ccy + math.sin(a) * rh)
                       for (ccx, ccy, rw, rh) in rings] + [bot]
        d.poly(pts, c, w)


def _vortex_sphere(d, cx, cy, r, c, w):
    """An exaggerated black-hole funnel: a spherical grid whose rings are sucked
    up and IN toward a small off-centre throat, spiralling harder the closer
    they get — a clear swirling whirlpool, not a symmetric ball. Parameterised
    by u in [0,1]: u=0 is the wide outer rim (bottom/front of the sphere),
    u=1 is the tight throat."""
    n_ring = 26      # dense stack of rings rim -> throat
    n_spoke = 22     # spiral spokes
    tilt = 0.40

    # throat: small, set back & up-left of centre (the drain the swirl sinks to)
    tx, ty = cx - r * 0.16, cy - r * 0.20
    throat_rw = r * 0.08

    def ring_at(u):
        """Return (ccx, ccy, rw, rh, spin) for parameter u (0 wide rim -> 1
        throat). The funnel MOUTH (u=0) is the big ellipse tilted toward the
        viewer near the top; rings shrink, rise and recede toward the throat,
        spinning harder — so it reads as a hole the grid sinks into."""
        # radius shrinks from full sphere radius to the tiny throat
        rw = throat_rw + (r - throat_rw) * (1.0 - u) ** 1.35
        rh = rw * tilt
        # mouth sits a bit LOW & forward; throat recedes up & back
        rim_cx = cx + r * 0.02
        rim_cy = cy + r * 0.16
        ccx = rim_cx + (tx - rim_cx) * (u ** 1.15)
        ccy = rim_cy + (ty - rim_cy) * (u ** 0.9)
        # spin ramps up hard toward the throat -> whirlpool
        spin = (u ** 1.35) * 6.8
        return ccx, ccy, rw, rh, spin

    rings = []
    for li in range(n_ring + 1):
        u = li / n_ring
        ccx, ccy, rw, rh, spin = ring_at(u)
        rings.append((ccx, ccy, rw, rh, spin))
        pts = [(ccx + math.cos(a + spin) * rw, ccy + math.sin(a + spin) * rh)
               for a in [2 * math.pi * k / 72 for k in range(73)]]
        # rings fade slightly as they approach the throat
        d.poly(pts, c, w * (1.0 - 0.25 * u))

    # spiral spokes threading every ring from rim to throat (the swirl lines)
    for lo in range(n_spoke):
        a0 = 2 * math.pi * lo / n_spoke
        pts = []
        for (ccx, ccy, rw, rh, spin) in rings:
            pts.append((ccx + math.cos(a0 + spin) * rw,
                        ccy + math.sin(a0 + spin) * rh))
        d.poly(pts, c, w * 0.8)

    # outer sphere silhouette so the vortex reads as sitting inside a globe
    d.poly([(cx + math.cos(a) * r, cy + math.sin(a) * r)
            for a in [2 * math.pi * k / 80 for k in range(81)]], c, w)
    # a faint back-hemisphere latitude ring or two for volume
    for yy in (cy - r * 0.5, cy + r * 0.35):
        rw = math.sqrt(max(0.0, r * r - (yy - cy) ** 2))
        d.poly([(cx + math.cos(a) * rw, yy + math.sin(a) * rw * tilt)
                for a in [2 * math.pi * k / 60 for k in range(61)]], c, w * 0.5)


def wireframe_oval(d, cx, cy, rx, ry, c, w=1.2):
    """A simple 3D-looking oval/ellipsoid: outer ellipse + inner meridian
    ellipse + equator line (the left-column central ellipse motif)."""
    outer = [(cx + math.cos(a) * rx, cy + math.sin(a) * ry)
             for a in [2 * math.pi * k / 60 for k in range(61)]]
    d.poly(outer, c, w)
    # inner vertical meridian (thin ellipse)
    inner = [(cx + math.cos(a) * rx * 0.34, cy + math.sin(a) * ry)
             for a in [2 * math.pi * k / 60 for k in range(61)]]
    d.poly(inner, c, w)
    d.line(cx - rx, cy, cx + rx, cy, c, w)


def line_chart(d, x0, y0, x1, y1, c, w=1.4):
    """Jagged multi-line chart over a faint grid (bottom-left column)."""
    # grid
    for k in range(0, 7):
        gx = x0 + (x1 - x0) * k / 6
        d.line(gx, y0, gx, y1, W_FAINT, 0.7)
    for k in range(0, 5):
        gy = y0 + (y1 - y0) * k / 4
        d.line(x0, gy, x1, gy, W_FAINT, 0.7)
    # two jagged traces
    seeds = [(3, y0 + (y1 - y0) * 0.55), (11, y0 + (y1 - y0) * 0.75)]
    for seed, base in seeds:
        pts = []
        i = seed
        n = 22
        for k in range(n):
            u = k / (n - 1)
            i = (i * 1103515245 + 12345) & 0x7fffffff
            rnd = ((i >> 6) % 1000) / 1000.0
            # rising trend with jitter
            yv = y1 - (y1 - y0) * (0.15 + 0.7 * u + 0.18 * (rnd - 0.5))
            pts.append((x0 + u * (x1 - x0), yv))
        d.poly(pts, c, w)


# =========================================================================
# TEXT HELPERS
# =========================================================================

def vtext(d, s, x, y, ch, c, gap=1.0):
    """Draw text stacked vertically (each char below the previous)."""
    for i, ch_ in enumerate(s):
        d.text(ch_, x, y + i * ch * gap, ch, c, align="center")


def filler(d, x0, y0, w, ch, c, lines, lh=None, justify=False):
    """Draw `lines` of lorem-ish text word-wrapped to width w."""
    if lh is None:
        lh = ch * 1.35
    words = ("sed ut perspiciatis unde omnis iste natus error sit voluptatem "
             "accusantium doloremque laudantium totam rem aperiam eaque ipsa "
             "quae ab illo inventore veritatis et quasi architecto beatae vitae "
             "dicta sunt explicabo nemo enim ipsam voluptatem quia voluptas").split()
    wi = 0
    for ln in range(lines):
        line = ""
        while wi < len(words):
            test = (line + " " + words[wi]).strip()
            if d.text_width(test, ch) > w and line:
                break
            line = test
            wi += 1
            if wi >= len(words):
                wi = 0
        d.text(line, x0, y0 + ln * lh, ch, c)


# =========================================================================
# COLUMN BUILDERS
# =========================================================================

def build_left(d):
    x0, y0, x1, y1 = 8, 60, 438, 500   # outer frame region
    # outer notched frame
    _panel_frame(d, x0, y0, x1, y1, W_, notch_tr=True)

    # --- top-left hatched banner block (notched) ---
    bx0, by0, bx1, by1 = 34, 88, 205, 158
    d.poly([(bx0, by0), (bx1, by0), (bx1, by1 - 14), (bx1 - 14, by1),
            (bx0, by1)], W_, 2.0, closed=True)
    hazard_stripes(d, bx0 + 4, by0 + 4, bx1 - 6, by1 - 6, W_, sw=9, gap=9, w=2.4, ang=1)

    # --- far-left vertical texture strip (small diagonal marks) ---
    for k in range(26):
        yy = 175 + k * 11
        d.line(46, yy, 62, yy - 9, W_DIM, 1.1)

    # --- giant vertical CYBERPUNK (upright letters, C top -> K bottom) ---
    _vertical_cyberpunk(d, 122, 170, 492)
    # --- vertical barcode strip (far left, lower) ---
    barcode_v(d, 210, 350, 232, 490, W_)
    # small label under barcode
    d.rect(210, 492, 262, 498, W_DIM, 1.0)

    # --- asterisk in box (bottom-left) ---
    ax, ay = 178, 372
    d.rect(ax - 22, ay - 22, ax + 22, ay + 22, W_, 2.0)
    _asterisk(d, ax, ay, 16, W_)

    # --- HERO: wireframe terrain range (top area of right sub-column) ---
    wireframe_terrain(d, 248, 82, 188, 190, W_)
    # terrain sits above a baseline
    d.line(258, 272, 430, 272, W_, 1.2)

    # --- ERROR-SYSTEM dotted line ---
    ey = 288
    d.text("-ERROR-SYSTEM-", 258, ey - 6, 9, W_)
    dx = 258 + d.text_width("-ERROR-SYSTEM-", 9) + 8
    for k in range(28):
        d.disc(dx + k * 4, ey, 0.9, W_DIM)
    # barcode strip to the right on same line
    barcode(d, 372, ey - 8, 434, ey + 4, W_, seed=5)

    # --- small paragraph filler (left) ---
    filler(d, 258, 302, 46, 5.0, W_DIM, 10, lh=7.0)

    # --- empty panel (right of filler) ---
    d.rect(312, 300, 434, 372, W_, 1.4)
    # tiny slider under panel
    d.line(316, 380, 396, 380, W_DIM, 1.0)
    d.disc(360, 380, 2.4, W_)

    # --- row of 3 connector icon boxes ---
    for k in range(3):
        ix = 258 + k * 22
        d.rect(ix, 388, ix + 18, 404, W_, 1.4)
        d.line(ix + 9, 388, ix + 9, 382, W_, 1.4)
        d.line(ix + 4, 382, ix + 14, 382, W_, 1.4)

    # --- [DATABASE] red tag ---
    d.text("[", 258, 410, 12, RED)
    d.text("DATABASE", 264, 410, 12, RED)
    d.text("]", 264 + d.text_width("DATABASE", 12) + 2, 410, 12, RED)
    _fill_rect(d, 263, 411, 264 + d.text_width("DATABASE", 12) + 1, 423, RED)
    # re-draw text in black over the red fill
    d.text("DATABASE", 264, 410, 12, BLACK)

    # --- FUTURISTIC USER INTERFACE label ---
    d.text("FUTURISTIC USER INTERFACE :", 258, 432, 7.5, W_)
    d.line(258, 444, 434, 444, W_DIM, 1.0)

    # --- row of ~6 icon boxes with diagonal slashes ---
    for k in range(6):
        ix = 320 + k * 20
        icon_box_slash(d, ix, 430, ix + 15, 445, W_, 1.3, slash=(k % 2 == 0))

    # --- bottom row: small wireframe globe, oval, line chart ---
    wireframe_globe(d, 282, 476, 26, W_DIM, vortex=True, w=0.9)
    d.rect(256, 448, 310, 500, W_, 1.3)
    wireframe_oval(d, 356, 474, 26, 28, W_, 1.2)
    line_chart(d, 386, 452, 434, 498, W_, 1.3)


def build_mid(d):
    x0, y0, x1, y1 = 452, 22, 866, 526
    # outer frame
    d.rect(x0, y0, x1, y1, W_, 1.6)

    # ============ TOP HEADER BOX ============
    hx0, hy0, hx1, hy1 = 462, 34, 858, 156
    d.rect(hx0, hy0, hx1, hy1, W_, 2.0)

    # FUTURISTIC pill (notched)
    fx0, fy0, fx1, fy1 = 470, 42, 588, 66
    d.poly([(fx0 + 8, fy0), (fx1, fy0), (fx1, fy1), (fx0 + 8, fy1),
            (fx0, (fy0 + fy1) / 2)], W_, 1.8, closed=True)
    d.text("FUTURISTIC", (fx0 + fx1) / 2 + 4, fy0 + 3, 15, W_, align="center")

    # biohazard
    biohazard(d, 612, 54, 15, W_, 1.4)
    # radiation trefoil below biohazard
    radiation_trefoil(d, 612, 96, 15, W_)

    # 7-seg TIMECODE 00:01:02 in a grey bevel box
    tcx0, tcy0, tcx1, tcy1 = 648, 42, 782, 74
    _fill_rect(d, tcx0, tcy0, tcx1, tcy1, GREY)
    seven_seg(d, "00:01:02", tcx0 + 8, tcy0 + 5, 22, W_)
    # warning triangle + WARNING text to right of timecode
    warning_triangle(d, 800, 52, 12, W_, 1.4)
    d.text("WARNING", 786, 66, 5.5, W_)
    hazard_stripes(d, 786, 70, 826, 76, W_, sw=4, gap=3, w=1.0, ang=1)

    # filler paragraph inside header (right)
    filler(d, 648, 82, 200, 5.0, W_DIM, 4, lh=7.5)

    # -i-i- dashes
    d.text("-i-i-", 604, 118, 16, W_, align="center")

    # box glyphs row: ☒高 中等 困☒  -> approximate with boxed cells
    gy = 116
    cells = [(648, "X#"), (700, "##"), (752, "#X")]
    for gx, _ in cells:
        d.rect(gx, gy, gx + 44, gy + 24, W_, 1.4)
    small_box_glyph(d, 652, gy + 4, 668, gy + 20, W_, 1.3)   # ☒ left cell
    _mini_hanzi(d, 674, gy + 4, 692, gy + 20, W_)            # 高
    _mini_hanzi(d, 704, gy + 4, 722, gy + 20, W_)            # 中
    _mini_hanzi(d, 728, gy + 4, 746, gy + 20, W_)            # 等
    _mini_hanzi(d, 756, gy + 4, 774, gy + 20, W_)            # 困
    small_box_glyph(d, 778, gy + 4, 794, gy + 20, W_, 1.3)   # ☒

    # CODE - 17-WW-22-000 (bottom-left of header) with hatch prefix
    hazard_stripes(d, 470, 132, 490, 148, W_, sw=4, gap=3, w=1.0)
    d.rect(470, 132, 606, 148, W_, 1.4)
    d.text("CODE-17-WW-22-000", 496, 134, 10, W_)
    # barcode along bottom-right of header
    barcode(d, 616, 130, 852, 150, W_, seed=9)

    # ============ BODY HERO in arched capsule ============
    cap_x0, cap_x1 = 468, 620
    cap_top, cap_bot = 172, 500
    cx = (cap_x0 + cap_x1) / 2
    # arched capsule frame
    _arched_capsule(d, cap_x0, cap_top, cap_x1, cap_bot, W_)
    # sunburst behind head (top of capsule)
    _sunburst(d, cx, 200, 44, W_DIM)
    wireframe_body(d, cx, 316, 272, W_)

    # readouts bottom-left (4.121 / 1.323)
    d.text("LOREM IPSUM", 478, 448, 6, W_DIM)
    d.text("4.121", 478, 458, 18, W_)
    seismograph_trace(d, 528, 452, 600, 476, W_, seed=3, w=1.2)
    d.text("LOREM IPSUM", 478, 486, 6, W_DIM)
    d.text("1.323", 478, 496, 18, W_)
    seismograph_trace(d, 528, 490, 600, 512, W_, seed=17, w=1.2)

    # ============ RIGHT SUB-COLUMN of middle ============
    # CYBERPUNK label + hatch
    d.text("CYBERPUNK", 630, 182, 20, W_)
    hazard_stripes(d, 764, 176, 812, 204, W_, sw=6, gap=6, w=1.8, ang=1)
    barcode(d, 630, 210, 720, 220, W_, seed=21)
    d.text("*", 724, 210, 10, W_)
    # small wireframe sphere top-right
    wireframe_globe(d, 828, 192, 24, W_DIM, vortex=False, w=0.8)

    # WARNING: DETECTED bar with arrows
    ay = 232
    d.rect(632, ay, 758, ay + 16, W_, 1.4)
    d.text("WARNING : DETECTED", 638, ay + 2, 9, W_)
    _arrows(d, 604, ay + 8, 6, W_, n=4, dr=1)
    _arrows(d, 774, ay + 8, 6, W_, n=5, dr=-1)

    # middle black panel (empty scan window)
    d.rect(632, 256, 726, 456, W_, 1.4)

    # 06_LOREAM2K4 panel (right)
    px0, py0, px1, py1 = 734, 252, 858, 456
    _panel_frame(d, px0, py0, px1, py1, W_, notch_tr=True, small=True)
    d.text("06_LOREAM2K4", (px0 + px1) / 2, py0 + 6, 12, W_, align="center")
    d.line(px0 + 6, py0 + 24, px1 - 6, py0 + 24, W_DIM, 1.0)
    # small icon row
    for k in range(4):
        ix = px0 + 10 + k * 14
        d.rect(ix, py0 + 30, ix + 10, py0 + 40, W_DIM, 1.0)
    # vertical filled bar-meter (segmented)
    mx0, mx1 = px0 + 10, px0 + 44
    my0, my1 = py0 + 48, py1 - 60
    d.rrect(mx0, my0, mx1, my1, 8, W_, 1.4)
    nseg = 20
    for k in range(nseg):
        sy0 = my0 + 6 + k * (my1 - my0 - 12) / nseg
        sy1 = sy0 + (my1 - my0 - 12) / nseg - 1.5
        _fill_rect(d, mx0 + 4, sy0, mx1 - 4, sy1, W_)
    # value/bar rows to the right of meter
    for k in range(12):
        ry = py0 + 52 + k * 12
        d.text("TEXT", px0 + 52, ry, 4.5, W_DIM)
        bar_len = 12 + ((k * 37) % 40)
        d.line(px0 + 74, ry + 4, px0 + 74 + bar_len, ry + 4, W_, 1.4)
    # slot buttons at bottom
    for k in range(3):
        sx = px0 + 6 + k * 40
        d.rect(sx, py1 - 44, sx + 34, py1 - 32, W_DIM, 1.0)
        d.text("SLOT XX", sx + 17, py1 - 43, 4, W_DIM, align="center")
    # LOADING bar
    d.text("LOADING", (px0 + px1) / 2, py1 - 24, 8, W_, align="center")
    loading_bar(d, px0 + 6, py1 - 12, px1 - 6, py1 - 4, 0.62, W_, 1.2)


def build_right(d):
    x0, y0, x1, y1 = 872, 22, 1300, 526
    d.rect(x0, y0, x1, y1, W_, 1.6)

    # ===== TOP: 01 tab + sphere + numbers + MAIN MENU headline =====
    # header bar with notched ends
    _panel_frame(d, 884, 40, 1288, 96, W_, notch_tr=True, notch_bl=True)
    # 01 tab
    d.rect(892, 52, 946, 84, W_, 1.8)
    d.text("01", 919, 56, 22, W_, align="center")
    # wireframe sphere
    wireframe_globe(d, 986, 68, 24, W_, vortex=False, w=0.9)
    # number columns
    for r in range(5):
        d.text("6879834  2360467", 1024, 48 + r * 8, 5, W_DIM)
    # MAIN MENU headline
    d.text("MAIN MENU", 1150, 52, 30, W_, align="center")
    # bracket at end
    d.poly([(1268, 54), (1280, 54), (1280, 84), (1268, 84)], W_, 2.0)
    d.line(1280, 62, 1286, 56, W_, 2.0)

    # ===== HERO: big wireframe globe/vortex =====
    wireframe_globe(d, 970, 250, 118, W_, vortex=True, w=1.1)

    # ===== justified paragraph (right of globe) =====
    filler(d, 1108, 190, 178, 8.5, W_, 12, lh=12.0)

    # ===== number ramp + step bar graph + dot matrix =====
    # dot/step decorative row
    dot_matrix(d, 1112, 300, 8, 4, 6, W_DIM, seed=4, r=1.0, fill=0.55)
    step_bar_graph(d, 1160, 296, 1230, 326, W_, 1.2)
    dot_matrix(d, 1240, 300, 8, 4, 6, W_DIM, seed=9, r=1.0, fill=0.5)
    # number ramp 1..10
    for k in range(10):
        d.text(str(k + 1), 1114 + k * 17, 332, 8, W_DIM)

    # ===== lower filler paragraph + small globe + buttons =====
    filler(d, 1000, 360, 288, 6.5, W_DIM, 4, lh=9.0)
    wireframe_oval(d, 940, 388, 40, 22, W_DIM, 0.9)
    d.rect(886, 356, 992, 420, W_, 1.2)
    # row of buttons
    for k in range(4):
        bx = 1000 + k * 62
        d.rect(bx, 400, bx + 52, 420, W_DIM, 1.2)
        # little inner tabs
        d.line(bx + 4, 400, bx + 4, 396, W_DIM, 1.0)

    # ===== FOOTER =====
    # separator with notch
    d.line(884, 440, 1030, 440, W_, 1.6)
    d.poly([(1030, 440), (1050, 440), (1060, 430), (1288, 430)], W_, 1.6)

    # ERROR-SYSTEM tiny label above LOADING
    d.text("-ERROR-SYSTEM-", 1004, 448, 7, W_)
    d.text("LOADING", 1004, 456, 4.5, W_DIM)

    # hatched vertical bar + dot matrix at footer left
    hazard_stripes(d, 950, 452, 984, 512, W_, sw=6, gap=6, w=1.8, ang=1)
    d.rect(948, 450, 986, 514, W_, 1.4)
    dot_matrix(d, 996, 456, 8, 8, 6, W_, seed=13, r=1.2, fill=0.5)

    # LOADING... bar with hazard stripes
    d.text("LOADING...", 1050, 470, 12, W_)
    ldx0, ldy0, ldx1, ldy1 = 1048, 486, 1288, 504
    d.rect(ldx0, ldy0, ldx1, ldy1, W_, 1.4)
    hazard_stripes(d, ldx0 + 3, ldy0 + 3, ldx0 + 150, ldy1 - 3, W_, sw=7, gap=7, w=2.0, ang=1)
    dot_matrix(d, 1160, 468, 20, 2, 6, W_DIM, seed=2, r=1.0, fill=0.5)

    # ERROR-SYSTEM-0x0000000
    d.text("-ERROR-SYSTEM-", 884, 500, 12, W_)
    d.text("0x0000000", 884 + d.text_width("-ERROR-SYSTEM-", 12) + 8, 500, 12, W_)

    # bottom row: hex box, barcode, [-ERROR-SYSTEM-], warning triangle
    icon_box_slash(d, 892, 512, 918, 524, W_, 1.2, slash=True)
    d.rect(918, 512, 930, 524, W_, 1.2)
    barcode(d, 1000, 512, 1090, 524, W_, seed=31)
    # hex badge
    _hex_badge(d, 1050, 470, 16, W_)
    d.text("[-ERROR-SYSTEM-]", 1180, 514, 9, W_, align="center")
    warning_triangle(d, 1280, 516, 8, W_, 1.2)


# =========================================================================
# SHAPE UTILITIES
# =========================================================================

def _panel_frame(d, x0, y0, x1, y1, c, notch_tr=False, notch_bl=False, small=False):
    """Rounded/notched panel outline (corner cuts)."""
    n = 10 if not small else 8
    pts = [(x0 + n, y0)]
    if notch_tr:
        pts += [(x1 - n, y0), (x1, y0 + n)]
    else:
        pts += [(x1, y0)]
    pts += [(x1, y1 - n), (x1 - n, y1)]
    if notch_bl:
        pts += [(x0 + n, y1), (x0, y1 - n)]
    else:
        pts += [(x0, y1)]
    pts += [(x0, y0 + n)]
    d.poly(pts, c, 2.0, closed=True)


def _vertical_cyberpunk(d, cx, y_top, y_bot):
    """Draw 'CYBERPUNK' as bold FILLED block capitals stacked vertically, C at
    top -> K at bottom, each letter upright and clearly legible."""
    word = "CYBERPUNK"
    n = len(word)
    cell = (y_bot - y_top) / n
    hw = 30.0          # glyph half-width
    gap = cell * 0.22  # vertical gap between letters
    for i, ch in enumerate(word):
        gy0 = y_top + i * cell + gap * 0.5
        gy1 = y_top + (i + 1) * cell - gap * 0.5
        _block_letter(d, ch, cx, gy0, gy1, hw)


def _fbar(d, x0, y0, x1, y1, c=None):
    """Filled rectangular bar (a single glyph stroke)."""
    d.rrect_fill(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), 0.0,
                 c if c is not None else W_)


def _fquad(d, p0, p1, p2, p3, c=None):
    """Filled quad via two triangles (for diagonal glyph strokes)."""
    col = c if c is not None else W_
    d.tri_fill(p0, p1, p2, col)
    d.tri_fill(p0, p2, p3, col)


def _fdiag(d, ax, ay, bx, by, th, c=None):
    """A thick filled diagonal bar from (ax,ay) to (bx,by), thickness th
    (offset horizontally so verticals stay crisp)."""
    hx = th * 0.5
    _fquad(d, (ax - hx, ay), (ax + hx, ay), (bx + hx, by), (bx - hx, by), c)


def _block_letter(d, ch, cx, y0, y1, hw):
    """Draw one FILLED bold block capital in the cell [cx-hw,cx+hw]x[y0,y1].
    Strokes are filled rectangles / quads => heavy legible type."""
    x0, x1 = cx - hw, cx + hw
    h = y1 - y0
    ym = (y0 + y1) * 0.5
    st = hw * 0.34          # stroke thickness (bold but counters stay open)
    stv = h * 0.16          # horizontal-bar thickness (keeps bars chunky)
    # helper edges
    xL0, xL1 = x0, x0 + st          # left stem
    xR0, xR1 = x1 - st, x1          # right stem
    yT0, yT1 = y0, y0 + stv         # top bar
    yB0, yB1 = y1 - stv, y1         # bottom bar
    yM0, yM1 = ym - stv * 0.5, ym + stv * 0.5  # mid bar

    if ch == "C":
        _fbar(d, xL0, y0, xL1, y1)          # left stem
        _fbar(d, x0, yT0, x1, yT1)          # top
        _fbar(d, x0, yB0, x1, yB1)          # bottom
    elif ch == "Y":
        # two diagonals meeting at centre, then a stem down
        _fdiag(d, x0 + st * 0.5, y0, cx, ym, st)
        _fdiag(d, x1 - st * 0.5, y0, cx, ym, st)
        _fbar(d, cx - st * 0.5, ym - st * 0.3, cx + st * 0.5, y1)
    elif ch == "B":
        _fbar(d, xL0, y0, xL1, y1)          # left stem
        _fbar(d, x0, yT0, x1 - st * 0.4, yT1)  # top bar
        _fbar(d, x0, yM0, x1 - st * 0.4, yM1)  # mid bar
        _fbar(d, x0, yB0, x1 - st * 0.4, yB1)  # bottom bar
        _fbar(d, xR0, yT0, xR1, ym)         # upper right stem
        _fbar(d, xR0, ym, xR1, yB1)         # lower right stem
    elif ch == "E":
        _fbar(d, xL0, y0, xL1, y1)          # left stem
        _fbar(d, x0, yT0, x1, yT1)          # top
        _fbar(d, x0, yM0, x1 - st * 0.3, yM1)  # mid
        _fbar(d, x0, yB0, x1, yB1)          # bottom
    elif ch == "R":
        _fbar(d, xL0, y0, xL1, y1)          # left stem
        _fbar(d, x0, yT0, x1 - st * 0.4, yT1)  # top bar
        _fbar(d, x0, yM0, x1 - st * 0.4, yM1)  # mid bar
        _fbar(d, xR0, yT0, xR1, ym)         # upper right stem
        _fdiag(d, cx, ym, x1, y1, st)       # diagonal leg
    elif ch == "P":
        _fbar(d, xL0, y0, xL1, y1)          # left stem
        _fbar(d, x0, yT0, x1 - st * 0.4, yT1)  # top bar
        _fbar(d, x0, yM0, x1 - st * 0.4, yM1)  # mid bar
        _fbar(d, xR0, yT0, xR1, ym)         # right stem (upper half)
    elif ch == "U":
        _fbar(d, xL0, y0, xL1, yB0)         # left stem
        _fbar(d, xR0, y0, xR1, yB0)         # right stem
        _fbar(d, x0, yB0, x1, yB1)          # bottom bar
    elif ch == "N":
        _fbar(d, xL0, y0, xL1, y1)          # left stem
        _fbar(d, xR0, y0, xR1, y1)          # right stem
        _fdiag(d, x0 + st, y0, x1 - st, y1, st * 1.1)  # diagonal
    elif ch == "K":
        _fbar(d, xL0, y0, xL1, y1)          # left stem
        _fdiag(d, x1, y0, xL1 + st * 0.2, ym, st)      # upper arm
        _fdiag(d, xL1 + st * 0.2, ym, x1, y1, st)      # lower leg


def _asterisk(d, cx, cy, r, c):
    for k in range(6):
        a = k * math.pi / 3
        d.line(cx, cy, cx + math.cos(a) * r, cy + math.sin(a) * r, c, 3.0)


def barcode_v(d, x0, y0, x1, y1, c):
    """Vertical strip barcode (bars run vertically along a tall column)."""
    barcode(d, x0, y0, x1, y1, c, seed=13)


def seven_seg(d, s, x, y, h, c):
    """Draw a string in a chunky 7-seg style (approximate with bold text)."""
    d.text(s, x, y, h, c)


def _arched_capsule(d, x0, y0, x1, y1, c):
    """A tall capsule with a rounded (arched) top and squared bottom, plus a
    thin inner outline. Built as one continuous polyline going CCW so no stray
    chords appear."""
    cx = (x0 + x1) / 2
    r = (x1 - x0) / 2

    def outline(ox0, oy0, ox1, oy1, ww, col):
        rr = (ox1 - ox0) / 2
        ccx = (ox0 + ox1) / 2
        base_y = oy0 + rr            # y where arch meets the straight sides
        # arch from left spring point over the top to the right spring point
        arc = [(ccx + math.cos(a) * rr, base_y - math.sin(a) * rr)
               for a in [math.pi * (1.0 - k / 24) for k in range(25)]]
        # left side down + bottom + right side up  (single closed loop)
        pts = ([(ox0, base_y), (ox0, oy1), (ox1, oy1), (ox1, base_y)] + arc)
        d.poly(pts, col, ww, closed=True)

    outline(x0, y0, x1, y1, 2.0, c)
    m = 8
    outline(x0 + m, y0 + m, x1 - m, y1 - m, 1.0, W_DIM)


def _sunburst(d, cx, cy, r, c):
    """A fan of rays emanating downward/outward behind the head (top of the
    capsule). Only the upper hemisphere, sparse, so it doesn't muddy the body."""
    for k in range(24):
        a = math.pi + math.pi * k / 23   # from left (pi) over the top to right (2pi)
        d.line(cx + math.cos(a) * r * 0.30, cy + math.sin(a) * r * 0.30,
               cx + math.cos(a) * r, cy + math.sin(a) * r, c, 0.6)


def _arrows(d, x, y, sz, c, n=4, dr=1):
    """Row of >> chevrons; dr=+1 points right, -1 points left."""
    for k in range(n):
        bx = x + dr * k * (sz + 3)
        d.poly([(bx, y - sz), (bx + dr * sz, y), (bx, y + sz)], c, 1.4)


def _mini_hanzi(d, x0, y0, x1, y1, c):
    """Approximate a CJK glyph with a small grid of strokes."""
    d.line(x0, y0, x1, y0, c, 1.0)
    d.line(x0, (y0 + y1) / 2, x1, (y0 + y1) / 2, c, 1.0)
    d.line(x0, y1, x1, y1, c, 1.0)
    d.line((x0 + x1) / 2, y0, (x0 + x1) / 2, y1, c, 1.0)


def _hex_badge(d, cx, cy, r, c):
    pts = [(cx + math.cos(math.radians(60 * k - 90)) * r,
            cy + math.sin(math.radians(60 * k - 90)) * r) for k in range(6)]
    d.poly(pts, c, 1.6, closed=True)
    d.disc(cx - r * 0.35, cy, 1.6, c)
    d.disc(cx + r * 0.35, cy, 1.6, c)


# =========================================================================
# MAIN BUILD
# =========================================================================

def build(d, W, H, t=0.0):
    build_left(d)
    build_mid(d)
    build_right(d)


if __name__ == "__main__":
    import os, sys
    HERE = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, HERE)
    from _ref_render import render_png, save_compare
    REF = "C:/Users/antho/Downloads/arcv/examples/refs/gallery/ref2_reference.webp"
    out = os.path.join(HERE, "gallery", "ref2.png")
    cmp = os.path.join(HERE, "gallery", "ref2_compare.png")
    render_png(build, out, size=(1307, 547), mode="flat",
               base_color=(0.0, 0.0, 0.0, 1.0))
    save_compare(REF, out, cmp, "REF2")
    print("done")
