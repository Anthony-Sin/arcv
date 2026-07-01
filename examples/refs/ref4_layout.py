"""REF4 — clean automotive/helmet WINDSHIELD HUD (Intel "HUD Helmet App", 2014).

A thin, delicate, Apple-clean instrument overlay drawn over a dark night street:
a large curved windshield outline framing lots of negative space, with a Spotify
media player + phone/bt icons top-left, a weather block + wifi top-center, a
targeting ring with a nav arrow and a dotted perspective line down the center,
a boxed SPEED CLUSTER bottom-center, a navigation/destination stack on the right,
and a client/project footer table bottom-right.

Authored against the ARCV adapter `d` (see examples/_hud_adapters.py). Rendered
through the shared harness in _ref_render.py at (1562, 771) with a very restrained
glow theme so the lines stay crisp white/light-gray, not glowy.

Deterministic: no `t` dependence in the geometry (idle, static instrument look).
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------- palette
WHITE = (0.97, 0.98, 1.00, 1.00)     # primary bright lines / text
SOFT = (0.90, 0.92, 0.96, 0.92)      # slightly softened white
GRAY = (0.60, 0.62, 0.66, 1.00)      # secondary text / labels
GRAY_DIM = (0.50, 0.52, 0.57, 0.85)  # dim secondary
GRAY_QUEUE = (0.42, 0.44, 0.49, 0.85)  # dimmer — queued/next track
FAINT = (0.42, 0.45, 0.50, 0.60)     # very faint frame / ticks
GHOST = (0.34, 0.37, 0.42, 0.42)     # windshield outline
YELLOW = (0.82, 0.70, 0.22, 0.55)    # faint road center line
ROAD = (0.30, 0.33, 0.38, 0.35)      # faint road edge lines


def _fade(c, a):
    return (c[0], c[1], c[2], c[3] * a)


def _tight_number(d, s_str, x, y, h, c, pitch=0.62):
    """Draw a numeric string glyph-by-glyph at a tighter advance than the
    monospace default, so big bold numbers ("55", "88") sit snug like the
    reference instead of showing a wide gap. Returns the x after the last glyph.
    ``pitch`` is the fraction of the per-glyph monospace advance to use."""
    adv = d.text_width("0", h) * pitch
    cx = x
    for ch in s_str:
        d.text(ch, cx, y, h, c)
        cx += adv
    return cx


# ================================================================ build
def build(d, W, H, t=8.0):
    s = H / 771.0

    def X(fx):
        return fx * W

    def Y(fy):
        return fy * H

    perspective_road(d, W, H, s)
    windshield_frame(d, W, H, s)

    # -- top-left cluster
    _left_icons(d, W, H, s)
    media_player(d, W, H, s)
    _left_edge_icons(d, W, H, s)

    # -- top-center
    weather_widget(d, W, H, s)

    # -- center nav
    nav_path(d, W, H, s)

    # -- bottom-center speed cluster
    speed_cluster(d, W, H, s)

    # -- right navigation stack
    nav_card(d, W, H, s)

    # -- bottom-right footer
    footer_table(d, W, H, s)


# ============================================================ windshield
def windshield_frame(d, W, H, s):
    """Big thin curved windshield outline: nearly full width at the top with
    almost-vertical sides that curve inward only near the bottom, a gently
    curved bottom edge, and a small tab/notch dipping down at bottom-center.

    Built from cubic-Bezier corners so the whole outline reads as one smooth,
    continuous piece of glass (matching the reference)."""
    c = GHOST
    lw = 1.4 * s

    def P(fx, fy):
        return (fx * W, fy * H)

    def bez(p0, p1, p2, p3, n=22):
        pts = []
        for i in range(n + 1):
            u = i / n
            mu = 1.0 - u
            x = (mu**3 * p0[0] + 3 * mu**2 * u * p1[0]
                 + 3 * mu * u**2 * p2[0] + u**3 * p3[0])
            y = (mu**3 * p0[1] + 3 * mu**2 * u * p1[1]
                 + 3 * mu * u**2 * p2[1] + u**3 * p3[1])
            pts.append((x, y))
        return pts

    # corner anchors (fractions) — WIDE and SHALLOW: top corners pulled a touch
    # down, bottom corners spread wider and raised so the frame is broad, not a
    # deep bowl.
    tl = P(0.024, 0.058)
    tr = P(0.976, 0.058)
    bl = P(0.150, 0.788)
    br = P(0.850, 0.788)
    # bottom tab
    tab_l = P(0.432, 0.792)
    tab_dl = P(0.456, 0.818)
    tab_dr = P(0.544, 0.818)
    tab_r = P(0.568, 0.792)

    path = []
    # top edge: gently peaked at the center (bows up), corners sit lower
    path += bez(tl, P(0.33, 0.028), P(0.67, 0.028), tr)
    # right side: near-vertical up top, curves inward only near the bottom
    path += bez(tr, P(0.988, 0.40), P(0.945, 0.70), br)[1:]
    # bottom-right up to tab (shallow curve)
    path += bez(br, P(0.740, 0.808), P(0.650, 0.798), tab_r)[1:]
    # tab notch (small dip: tab_r -> tab_dr -> tab_dl -> tab_l)
    path += [tab_dr, tab_dl, tab_l]
    # bottom-left from tab (shallow curve)
    path += bez(tab_l, P(0.350, 0.798), P(0.260, 0.808), bl)[1:]
    # left side: curves out then rises near-vertical
    path += bez(bl, P(0.055, 0.70), P(0.012, 0.40), tl)[1:]

    d.poly(path, c, lw, closed=True)


# =============================================================== road bg
def perspective_road(d, W, H, s):
    """Very faint dashed double-yellow center line on the dark ground, receding
    from just below the center ring down to the bottom of the frame. Kept subtle
    so the HUD stays dominant (we have no photographic background)."""
    vx, vy = W * 0.500, H * 0.470   # vanishing point (behind the ring)
    horizon = H * 0.800             # bottom of frame region

    # double-yellow dashed center line (two close lines with dashes)
    n = 14
    for k in range(n):
        u0 = k / n
        u1 = (k + 0.55) / n

        def pt(u, off):
            e = u * u  # dashes bunch near the vanishing point
            y = vy + (horizon - vy) * e
            xoff = off * (3 * s + 26 * s * e)
            return (vx + xoff, y)

        for off in (-1, 1):
            a = pt(u0, off)
            b = pt(u1, off)
            fade = 0.25 + 0.75 * (u0 * u0)  # fainter far away
            d.line(a[0], a[1], b[0], b[1], _fade(YELLOW, fade), 2.0 * s)


# =========================================================== left icons
def _phone_icon(d, x, y, s, c=WHITE):
    """small smartphone outline."""
    w, h = 15 * s, 26 * s
    d.rrect(x, y, x + w, y + h, 3 * s, c, 1.4 * s)
    d.line(x + w * 0.36, y + 2.5 * s, x + w * 0.64, y + 2.5 * s, c, 1.2 * s)
    d.disc(x + w * 0.5, y + h - 3.5 * s, 1.2 * s, c)


def _bluetooth_icon(d, cx, cy, s, c=WHITE):
    """classic bluetooth rune: a vertical stem with two chevrons meeting at
    top/bottom, crossed by two short diagonals."""
    h = 12 * s
    w = 6 * s
    top = (cx, cy - h)
    bot = (cx, cy + h)
    mid = (cx, cy)
    ur = (cx + w, cy - h * 0.5)   # upper-right
    lr = (cx + w, cy + h * 0.5)   # lower-right
    ml = (cx - w, cy - h * 0.5)   # mid-left upper
    ml2 = (cx - w, cy + h * 0.5)  # mid-left lower
    # right rune: top -> ur -> mid -> lr -> bot -> back through mid to top
    d.poly([top, ur, mid, lr, bot], c, 1.3 * s)
    d.poly([top, mid, bot], c, 1.3 * s)
    # left diagonals crossing
    d.line(ml[0], ml[1], ur[0], ur[1], c, 1.3 * s)
    d.line(ml2[0], ml2[1], lr[0], lr[1], c, 1.3 * s)


def _left_icons(d, W, H, s):
    _phone_icon(d, W * 0.048, H * 0.052, s)
    _bluetooth_icon(d, W * 0.070, H * 0.088, s)


# =========================================================== media player
def _spotify_logo(d, cx, cy, r, s):
    """Spotify glyph: an outer ring with three concentric upward-bowing arcs
    (the classic sound-wave sweep). Additive glow can't paint dark-on-light, so
    we draw it as white line art rather than the filled green mark."""
    d.ring(cx, cy, r, WHITE, 2.2 * s)
    # three arcs sweeping across the disc, each bowing upward, nested so the
    # top one is longest — centers sit BELOW so the arc tops bow up.
    for rr, cyy, span in (
            (r * 1.05, cy + r * 0.42, 118),   # top, widest
            (r * 0.78, cy + r * 0.20, 128),   # middle
            (r * 0.52, cy - r * 0.02, 140)):  # bottom, tightest
        half = math.radians(span * 0.5)
        d.ring(cx, cyy, rr, WHITE, 1.9 * s,
               a0=math.radians(270) - half, a1=math.radians(270) + half)


def media_player(d, W, H, s):
    x = W * 0.075
    # Spotify logo
    _spotify_logo(d, W * 0.078, H * 0.165, 14 * s, s)

    # transport controls: pause "❚❚" and next "▶❙"
    px = W * 0.120
    py = H * 0.172
    # pause: two vertical bars
    d.line(px, py - 9 * s, px, py + 9 * s, WHITE, 3.0 * s)
    d.line(px + 7 * s, py - 9 * s, px + 7 * s, py + 9 * s, WHITE, 3.0 * s)
    # next: triangle + bar
    nx = W * 0.152
    d.tri_fill((nx, py - 8 * s), (nx, py + 8 * s), (nx + 13 * s, py), GRAY)
    d.line(nx + 15 * s, py - 8 * s, nx + 15 * s, py + 8 * s, GRAY, 2.6 * s)

    # progress line with a dot handle
    bar_x0 = W * 0.066
    bar_x1 = W * 0.196
    bar_y = H * 0.202
    d.line(bar_x0, bar_y, bar_x1, bar_y, GRAY_DIM, 2.0 * s)
    frac = 0.42
    hx = bar_x0 + (bar_x1 - bar_x0) * frac
    d.line(bar_x0, bar_y, hx, bar_y, WHITE, 2.2 * s)
    d.disc(hx, bar_y, 4.5 * s, WHITE)

    # small vertical tick at the start of the progress (like ref)
    d.line(bar_x0, bar_y - 6 * s, bar_x0, bar_y + 6 * s, WHITE, 2.0 * s)

    # track text — line 1 white
    tx = W * 0.075
    d.text("DaftPunk", tx, H * 0.222, 19 * s, WHITE)
    d.text("Get Lucky", tx, H * 0.248, 19 * s, WHITE)
    d.text("6:07", W * 0.205, H * 0.248, 17 * s, GRAY, align="right")
    # track text — line 2 dimmer gray (queued / next track)
    d.text("LCD Soundsystem", tx, H * 0.304, 19 * s, GRAY_QUEUE)
    d.text("You wanted a hit", tx, H * 0.330, 19 * s, GRAY_QUEUE)
    d.text("9:06", W * 0.215, H * 0.330, 17 * s, GRAY_QUEUE, align="right")


def _left_edge_icons(d, W, H, s):
    """music-note, location pin, phone-handset down the left edge."""
    cx = W * 0.095
    # music note
    ny = H * 0.445
    d.disc(cx - 6 * s, ny + 12 * s, 4 * s, WHITE)
    d.disc(cx + 8 * s, ny + 9 * s, 4 * s, WHITE)
    d.line(cx - 2 * s, ny + 12 * s, cx - 2 * s, ny - 8 * s, WHITE, 2.0 * s)
    d.line(cx + 12 * s, ny + 9 * s, cx + 12 * s, ny - 11 * s, WHITE, 2.0 * s)
    d.line(cx - 2 * s, ny - 8 * s, cx + 12 * s, ny - 11 * s, WHITE, 2.0 * s)

    # location pin (teardrop + inner circle)
    py = H * 0.500
    d.ring(cx, py, 9 * s, WHITE, 2.0 * s, a0=math.radians(35), a1=math.radians(325 + 180) - math.radians(180))
    # simpler: a full ring plus a point below
    d.ring(cx, py, 9 * s, WHITE, 2.0 * s)
    d.disc(cx, py, 3.2 * s, WHITE)
    d.poly([(cx - 5 * s, py + 7 * s), (cx, py + 15 * s), (cx + 5 * s, py + 7 * s)], WHITE, 2.0 * s)

    # phone handset
    hy = H * 0.560
    _handset(d, cx, hy, s, WHITE)


def _handset(d, cx, cy, s, c):
    """classic telephone handset silhouette."""
    pts = [
        (cx - 10 * s, cy - 10 * s),
        (cx - 6 * s, cy - 14 * s),
        (cx - 2 * s, cy - 10 * s),
        (cx - 4 * s, cy - 6 * s),
        (cx + 6 * s, cy + 4 * s),
        (cx + 10 * s, cy + 2 * s),
        (cx + 14 * s, cy + 6 * s),
        (cx + 10 * s, cy + 10 * s),
    ]
    # draw a curved handset as two ear discs joined by a bar
    d.disc(cx - 8 * s, cy - 8 * s, 4 * s, c)
    d.disc(cx + 8 * s, cy + 8 * s, 4 * s, c)
    d.line(cx - 6 * s, cy - 6 * s, cx + 6 * s, cy + 6 * s, c, 3.2 * s)
    d.ring(cx - 8 * s, cy - 8 * s, 8 * s, c, 2.0 * s,
           a0=math.radians(120), a1=math.radians(300))
    d.ring(cx + 8 * s, cy + 8 * s, 8 * s, c, 2.0 * s,
           a0=math.radians(-60), a1=math.radians(120))


# =========================================================== weather widget
def weather_widget(d, W, H, s):
    cx = W * 0.428
    cy = H * 0.170
    # cloud icon: overlapping discs + flat base
    _cloud(d, cx, cy, s)
    # temperature
    d.text("68°", cx + 26 * s, H * 0.150, 30 * s, WHITE)
    d.text("Brooklyn NY", cx, H * 0.208, 16 * s, GRAY)

    # wifi icon (stacked arcs) — extra horizontal gap from "68°"
    wx = W * 0.495
    wy = H * 0.185
    for i, rr in enumerate((20 * s, 13 * s, 6 * s)):
        d.ring(wx, wy, rr, WHITE, 2.0 * s,
               a0=math.radians(215), a1=math.radians(325))
    d.disc(wx, wy, 2.2 * s, WHITE)

    # small diagonal arrow (up-right)
    ax = W * 0.533
    ay = H * 0.180
    d.line(ax - 8 * s, ay + 8 * s, ax + 8 * s, ay - 8 * s, WHITE, 2.4 * s)
    d.poly([(ax + 2 * s, ay - 8 * s), (ax + 8 * s, ay - 8 * s), (ax + 8 * s, ay - 2 * s)],
           WHITE, 2.4 * s)


def _cloud(d, cx, cy, s):
    c = WHITE
    lw = 2.0 * s
    # three bumps forming the top of a cloud, drawn as arcs
    d.ring(cx - 8 * s, cy, 8 * s, c, lw, a0=math.radians(90), a1=math.radians(270))
    d.ring(cx, cy - 5 * s, 10 * s, c, lw, a0=math.radians(180), a1=math.radians(360))
    d.ring(cx + 10 * s, cy, 7 * s, c, lw, a0=math.radians(-90), a1=math.radians(90))
    d.line(cx - 8 * s, cy + 8 * s, cx + 10 * s, cy + 7 * s, c, lw)


# =========================================================== nav path (center)
def nav_path(d, W, H, s):
    cx = W * 0.500
    cy = H * 0.460
    r = 60 * s

    # targeting ring
    d.ring(cx, cy, r, SOFT, 1.8 * s)

    # curved navigation arrow (bends right then up)
    ax0 = cx - 22 * s
    ay0 = cy + 34 * s
    arrow = [
        (ax0, ay0),
        (cx - 10 * s, cy + 10 * s),
        (cx + 6 * s, cy - 6 * s),
        (cx + 22 * s, cy - 22 * s),
    ]
    d.poly(arrow, WHITE, 3.0 * s)
    # arrow head
    hx, hy = cx + 22 * s, cy - 22 * s
    d.poly([(hx - 12 * s, hy + 2 * s), (hx, hy), (hx - 2 * s, hy + 12 * s)], WHITE, 3.0 * s)

    # small tick at bottom of ring
    d.line(cx, cy + r, cx, cy + r + 8 * s, SOFT, 1.6 * s)

    # dotted perspective line of dots across the road (a horizontal row of dots)
    row_y = H * 0.418
    x0, x1 = W * 0.205, W * 0.760
    ndots = 20
    for i in range(ndots):
        u = i / (ndots - 1.0)
        dx = x0 + (x1 - x0) * u
        # dots grow toward the near side; skip the range behind the ring
        rr = (1.6 + 1.6 * abs(u - 0.5) * 2.0) * s
        # brighter big dots at the two ends, faint small ones near center
        near = abs(u - 0.5)
        col = _fade(WHITE, 0.35 + 0.65 * near)
        d.disc(dx, row_y, rr, col)

    # two faint dotted arcs of dots fanning down-left and down-right from just
    # below the ring center (the receding lane markers), like the reference
    for side in (-1, 1):
        for k in range(6):
            u = k / 5.0
            px = cx + side * (10 * s + 58 * s * u)
            py = cy + 12 * s + 44 * s * (u ** 0.9)
            d.disc(px, py, (1.2 + 0.7 * u) * s, _fade(WHITE, 0.35 + 0.4 * u))

    # "0.8 mile" label beneath the ring, clear of the road line
    d.text("0.8 mile", cx, H * 0.590, 19 * s, WHITE, align="center")


# =========================================================== speed cluster
def _vbar_gauge(d, x, y0, y1, s, fill_frac, label_top, label_bot):
    """vertical segmented bar gauge with F..E labels."""
    d.text(label_top, x + 2 * s, y0 - 12 * s, 11 * s, GRAY, align="center")
    n = 14
    seg_h = (y1 - y0) / n
    filled = int(round(n * fill_frac))
    w = 9 * s
    for i in range(n):
        yy = y1 - (i + 1) * seg_h + 1.5 * s
        col = WHITE if i < filled else _fade(GRAY, 0.35)
        d.line(x - w * 0.5, yy, x + w * 0.5, yy, col, 3.2 * s)
    d.text(label_bot, x + 2 * s, y1 + 4 * s, 11 * s, GRAY, align="center")


def speed_cluster(d, W, H, s):
    x0 = W * 0.375
    y0 = H * 0.635
    x1 = W * 0.612
    y1 = H * 0.760

    # panel outline
    d.rect(x0, y0, x1, y1, FAINT, 1.4 * s)

    # "60 mph / Speed Limit" small, at left, ABOVE the box corner
    d.text("60", W * 0.356, H * 0.640, 20 * s, WHITE, align="right")
    d.text("mph", W * 0.360, H * 0.648, 10 * s, GRAY)
    d.text("Speed Limit", W * 0.339, H * 0.685, 11 * s, GRAY)

    # big "55 / mph" — digits drawn tight (the focal point)
    inx = x0 + 16 * s
    _tight_number(d, "55", inx, H * 0.655, 58 * s, WHITE, pitch=0.60)
    d.text("mph", inx, H * 0.730, 20 * s, WHITE)

    # divider after 55
    dvx = x0 + 92 * s
    d.line(dvx, y0 + 8 * s, dvx, y1 - 8 * s, FAINT, 1.2 * s)

    # "88 / kph" and "D2"
    kx = dvx + 12 * s
    _tight_number(d, "88", kx, H * 0.655, 26 * s, WHITE, pitch=0.66)
    d.text("kph", kx, H * 0.688, 15 * s, GRAY)
    d.text("D2", kx, H * 0.720, 26 * s, WHITE)

    # divider
    dvx2 = kx + 52 * s
    d.line(dvx2, y0 + 8 * s, dvx2, y1 - 8 * s, FAINT, 1.2 * s)

    # Gas & Oil gauges: tall segmented Gas bar (left) + 5 stacked Oil squares
    # (right), with a vertical F..E scale line between them.
    gy0, gy1 = y0 + 22 * s, y1 - 22 * s
    gx = dvx2 + 20 * s     # gas bar center
    fx = gx + 22 * s       # F..E scale line
    ox = fx + 20 * s       # oil squares center

    d.text("Gas", gx, y0 + 6 * s, 11 * s, GRAY, align="center")
    d.text("Oil", ox, y0 + 6 * s, 11 * s, GRAY, align="center")

    # Gas: tall stack of ~13 horizontal segments (mostly filled)
    ngas = 13
    gh = (gy1 - gy0) / ngas
    gfilled = 9
    gw = 11 * s
    for i in range(ngas):
        yy = gy1 - (i + 1) * gh + gh * 0.35
        col = WHITE if i < gfilled else _fade(GRAY, 0.4)
        d.line(gx - gw * 0.5, yy, gx + gw * 0.5, yy, col, 2.6 * s)

    # F..E vertical scale
    d.text("F", fx, y0 + 6 * s, 11 * s, GRAY, align="center")
    d.line(fx, gy0 + 6 * s, fx, gy1 - 6 * s, _fade(GRAY, 0.6), 1.2 * s)
    d.text("E", fx, y1 - 18 * s, 11 * s, GRAY, align="center")

    # Oil: 5 stacked hollow squares (partly filled from bottom)
    noil = 5
    oh = (gy1 - gy0) / noil
    ofilled = 2
    ow = 10 * s
    for i in range(noil):
        oy0 = gy1 - (i + 1) * oh + 2 * s
        oy1 = gy1 - i * oh - 2 * s
        if i < ofilled:
            d.rrect_fill(ox - ow * 0.5, oy0, ox + ow * 0.5, oy1, 2 * s, _fade(WHITE, 0.85))
        else:
            d.rrect(ox - ow * 0.5, oy0, ox + ow * 0.5, oy1, 2 * s, _fade(GRAY, 0.55), 1.2 * s)

    # small fuel-pump / oilcan glyphs at bottom
    d.rrect(gx - 4 * s, y1 - 16 * s, gx + 3 * s, y1 - 8 * s, 1 * s, GRAY, 1.2 * s)
    d.line(gx + 3 * s, y1 - 14 * s, gx + 6 * s, y1 - 15 * s, GRAY, 1.2 * s)
    d.disc(ox - 2 * s, y1 - 11 * s, 3 * s, GRAY)
    d.line(ox + 1 * s, y1 - 13 * s, ox + 7 * s, y1 - 15 * s, GRAY, 1.4 * s)

    # RIGHT sub-panel: gear row + equalizer
    rx0 = ox + 24 * s
    d.line(rx0, y0 + 8 * s, rx0, y1 - 8 * s, FAINT, 1.2 * s)

    # gear row "R P N D1 D2 D3" — D2 big/bold
    gears = [("R", 22), ("P", 22), ("N", 22), ("D1", 22), ("D2", 34), ("D3", 22)]
    gxx = rx0 + 12 * s
    gyy = H * 0.658
    for lbl, sz in gears:
        emph = lbl == "D2"
        col = WHITE if emph else GRAY
        d.text(lbl, gxx, gyy - (sz - 22) * 0.4 * s, sz * s, col)
        gxx += d.text_width(lbl, sz * s) + (10 * s if not emph else 14 * s)

    # horizontal equalizer / bar graphic
    ey0 = H * 0.700
    ey1 = H * 0.748
    ex0 = rx0 + 12 * s
    ex1 = x1 - 12 * s
    d.rect(ex0, ey0, ex1, ey1, _fade(GRAY, 0.5), 1.0 * s)
    # a small "cassette/level" icon at far left
    d.rect(ex0 + 3 * s, ey0 + 4 * s, ex0 + 14 * s, ey1 - 4 * s, GRAY, 1.0 * s)
    # vertical bars of varying height (equalizer)
    nbars = 30
    bx0 = ex0 + 20 * s
    for i in range(nbars):
        bx = bx0 + (ex1 - 4 * s - bx0) * (i / (nbars - 1.0))
        hgt = (0.30 + 0.65 * abs(math.sin(i * 1.7 + 0.5))) * (ey1 - ey0 - 8 * s)
        d.line(bx, ey1 - 4 * s, bx, ey1 - 4 * s - hgt, _fade(WHITE, 0.85), 1.6 * s)


# =========================================================== nav card (right)
def nav_card(d, W, H, s):
    x0 = W * 0.780
    x1 = W * 0.958

    # "Destination: Theatre" boxed
    dy0, dy1 = H * 0.130, H * 0.172
    d.rect(x0, dy0, x1, dy1, FAINT, 1.3 * s)
    d.text("Destination: Theatre", x0 + 12 * s, H * 0.140, 17 * s, WHITE)

    # compass/target icon + "20 miles  6 mins" boxed
    my0, my1 = dy1 + 4 * s, dy1 + 46 * s
    d.rect(x0, my0, x1, my1, FAINT, 1.3 * s)
    ccx, ccy = x0 + 20 * s, (my0 + my1) * 0.5
    d.ring(ccx, ccy, 11 * s, WHITE, 1.8 * s)
    d.line(ccx - 15 * s, ccy, ccx - 11 * s, ccy, WHITE, 1.6 * s)
    d.line(ccx + 11 * s, ccy, ccx + 15 * s, ccy, WHITE, 1.6 * s)
    d.line(ccx, ccy - 15 * s, ccx, ccy - 11 * s, WHITE, 1.6 * s)
    d.line(ccx, ccy + 11 * s, ccx, ccy + 15 * s, WHITE, 1.6 * s)
    d.disc(ccx, ccy, 2.5 * s, WHITE)
    d.text("20", ccx + 22 * s, ccy - 14 * s, 24 * s, WHITE)
    d.text("miles", ccx + 22 * s + d.text_width("20", 24 * s) + 5 * s, ccy - 2 * s, 14 * s, GRAY)
    mtx = ccx + 105 * s
    d.text("6", mtx, ccy - 14 * s, 24 * s, WHITE)
    d.text("mins", mtx + d.text_width("6", 24 * s) + 5 * s, ccy - 2 * s, 14 * s, GRAY)

    # big right-turn arrow + "Next Right / on Broadway / 0.8 mile"
    ay = H * 0.280
    # arrow: up then right with head
    aax = x0 + 6 * s
    d.line(aax, ay + 22 * s, aax, ay + 2 * s, WHITE, 3.4 * s)
    d.poly([(aax, ay + 4 * s), (aax, ay - 6 * s), (aax + 18 * s, ay - 6 * s)], WHITE, 3.4 * s)
    d.poly([(aax + 10 * s, ay - 15 * s), (aax + 22 * s, ay - 6 * s), (aax + 10 * s, ay + 3 * s)],
           WHITE, 3.4 * s)

    tx = x0 + 44 * s
    d.text("Next", tx, H * 0.260, 17 * s, GRAY)
    d.text("Right", tx + d.text_width("Next ", 17 * s) + 6 * s, H * 0.256, 22 * s, WHITE)
    d.text("on Broadway", tx, H * 0.288, 17 * s, GRAY)
    d.text("0.8 mile", tx, H * 0.312, 14 * s, GRAY)

    # two smaller "Turn Left on ..." lines with little arrows
    for i, (main, tail) in enumerate((("Turn Left", "on Main St."),
                                       ("Turn Left", "on 6th Ave"))):
        ly = H * 0.348 + i * 0.032 * H
        # small up-left arrow
        d.poly([(x0 + 8 * s, ly + 2 * s), (x0 + 2 * s, ly - 4 * s), (x0 + 8 * s, ly - 4 * s)],
               GRAY, 1.6 * s)
        d.line(x0 + 2 * s, ly - 4 * s, x0 + 10 * s, ly + 6 * s, GRAY, 1.6 * s)
        d.text(main, x0 + 20 * s, ly - 8 * s, 15 * s, GRAY)
        d.text(tail, x0 + 20 * s + d.text_width(main + " ", 15 * s), ly - 8 * s, 15 * s, GRAY_DIM)


# =========================================================== footer table
def footer_table(d, W, H, s):
    x0 = W * 0.665
    x1 = W * 0.982
    y0 = H * 0.900
    y_hdr = H * 0.918
    y_mid = H * 0.945
    y_val = H * 0.968

    cols = ["Client", "Project", "Date", "Point"]
    vals = ["Intel, Wearables Division", "HUD Helmet App", "July 2014", "Veronica Velasquez"]
    xs = [x0, x0 + (x1 - x0) * 0.42, x0 + (x1 - x0) * 0.63, x0 + (x1 - x0) * 0.80]

    # top rule
    d.line(x0, y0, x1, y0, FAINT, 1.2 * s)
    # middle rule (under headers)
    d.line(x0, y_mid, x1, y_mid, FAINT, 1.2 * s)

    for i, (col, val) in enumerate(zip(cols, vals)):
        cx = xs[i] + 6 * s
        # vertical separators
        if i > 0:
            d.line(xs[i], y0, xs[i], H * 0.985, FAINT, 1.0 * s)
        d.text(col, cx, y_hdr, 14 * s, WHITE)
        d.text(val, cx, y_val, 12 * s, GRAY)


# ================================================================ __main__
if __name__ == "__main__":
    import os
    import sys

    _HERE = os.path.dirname(os.path.abspath(__file__))
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)

    from _ref_render import render_png, save_compare  # noqa: E402
    from arcv.theme import make_theme  # noqa: E402

    REF = "C:/Users/antho/Downloads/arcv/examples/refs/gallery/ref4_reference.webp"
    SIZE = (1562, 771)

    theme = make_theme("ice", bloom_intensity=0.22, bloom_threshold=0.7, exposure=1.5,
                       scanline_strength=0.0, sweep_strength=0.0)
    theme.glow = (0.9, 0.95, 1.0)

    out = render_png(build, "gallery/ref4.png", size=SIZE, mode="glow", theme=theme,
                     base_color=(0.015, 0.02, 0.03, 1.0), t=8.0)
    print("wrote", out)
    cmp = save_compare(REF, out, os.path.join(_HERE, "gallery/ref4_compare.png"), "REF4")
    print("wrote", cmp)
