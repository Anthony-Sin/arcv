"""Layout for examples/anime_gallery.py — recreations of anime.js's iconic demos,
each drawn on the ARCV GPU pipeline (Draw over FlatOverlay), deterministic in ``t``.

Every panel is a pure function of time, so the same ``build(d, W, H, t)`` drives
the headless still / GIF export and the live window. Each demo notes its anime.js
origin and which ARCV capability (bucket) it exercises.
"""

from __future__ import annotations

import math

from arcv import easing
from arcv.overlay import anim
from arcv.overlay.adapters import DriverFromSignal, Draggable

DUR = 8.0  # loop period (seconds)

# palette
CYAN = (0.25, 0.95, 1.0, 1.0)
AMBER = (1.0, 0.72, 0.22, 1.0)
MAG = (1.0, 0.36, 0.72, 1.0)
GREEN = (0.45, 1.0, 0.62, 1.0)
LABEL = (0.62, 0.86, 0.96, 1.0)
BORDER = (0.22, 0.46, 0.56, 0.7)
FAINT = (0.3, 0.55, 0.66, 0.5)
DIM = (0.22, 0.42, 0.52, 0.35)

TAU = math.pi * 2.0


# ------------------------------------------------------------------- helpers
def _lerp(a, b, t):
    return a + (b - a) * t


def _reg_polygon(cx, cy, rad, n, rot=0.0):
    return [(cx + rad * math.cos(rot + TAU * i / n),
             cy + rad * math.sin(rot + TAU * i / n)) for i in range(n)]


def _star(cx, cy, rad, points, inner=0.46, rot=-math.pi / 2):
    pts = []
    for i in range(points * 2):
        rr = rad if i % 2 == 0 else rad * inner
        a = rot + math.pi * i / points
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def _sine_path(x0, x1, yc, amp, cycles, samples=48):
    return [(x0 + (x1 - x0) * i / samples,
             yc + amp * math.sin(TAU * cycles * i / samples))
            for i in range(samples + 1)]


def _panel(d, rect, title):
    """Draw a panel border + title; return the inset content rect."""
    x0, y0, x1, y1 = rect
    d.rect(x0, y0, x1, y1, BORDER, 1.0)
    d.text(title, x0 + 10, y0 + 7, 12, LABEL)
    # corner ticks (Arwes flourish)
    for cx, cy, sx, sy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line(cx, cy, cx + 10 * sx, cy, CYAN, 1.5)
        d.line(cx, cy, cx, cy + 10 * sy, CYAN, 1.5)
    return (x0 + 14, y0 + 28, x1 - 14, y1 - 12)


# ------------------------------------------------------------------- demos
def demo_grid_ripple(d, r, t):
    """anime.js grid stagger ripple — scale/color wave radiating from centre.
    Bucket 1 (animate disc radius/color) + stagger(grid=…, from_='center')."""
    x0, y0, x1, y1 = r
    cols, rows = 9, 5
    gx = (x1 - x0) / cols
    gy = (y1 - y0) / rows
    delays = anim.Stagger(1.0, grid=(cols, rows), from_="center").values(cols * rows)
    base_r = min(gx, gy) * 0.42
    for i in range(cols * rows):
        cx = x0 + (i % cols + 0.5) * gx
        cy = y0 + (i // cols + 0.5) * gy
        amt = 0.5 + 0.5 * math.sin(t * 3.0 - delays[i] * 1.7)
        col = anim.lerp_color(CYAN, MAG, amt)
        d.disc(cx, cy, base_r * (0.28 + 0.72 * amt), col)


def demo_draw_on(d, r, t):
    """anime.js SVG line draw-on — strokeDashoffset. Bucket 1: existing `reveal`."""
    x0, y0, x1, y1 = r
    # a little circuit trace
    mx, my = x0 + 6, y0 + 6
    Mx, My = x1 - 6, y1 - 6
    pts = [(mx, My), (mx, my + (My - my) * 0.35), (mx + (Mx - mx) * 0.30, my + (My - my) * 0.35),
           (mx + (Mx - mx) * 0.30, my), (mx + (Mx - mx) * 0.68, my),
           (mx + (Mx - mx) * 0.68, my + (My - my) * 0.6), (Mx, my + (My - my) * 0.6), (Mx, My)]
    tm = anim.Timer(2.4, loop=True, alternate=True)
    reveal = easing.in_out_cubic(tm.at(t))
    d.poly(pts, DIM, 1.0)                      # ghost of the full path
    d.poly(pts, CYAN, 2.0, reveal=reveal)      # drawn-on portion
    # node dots appear as the line reaches them
    total = anim.path_length(pts)
    acc = 0.0
    for i in range(len(pts) - 1):
        acc += math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        if reveal >= acc / total:
            d.disc(pts[i + 1][0], pts[i + 1][1], 3.0, AMBER)


def demo_morph(d, r, t):
    """anime.js shape morph A→B→C loop. Bucket 2: anim.morph static interp."""
    x0, y0, x1, y1 = r
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rad = min(x1 - x0, y1 - y0) * 0.4
    shapes = [
        _reg_polygon(cx, cy, rad, 3, -math.pi / 2),
        _reg_polygon(cx, cy, rad, 4, math.pi / 4),
        _star(cx, cy, rad, 5),
        _reg_polygon(cx, cy, rad, 6),
    ]
    n = len(shapes)
    seg = DUR / n
    idx = int(t / seg) % n
    local = easing.in_out_cubic((t % seg) / seg)
    pts = anim.morph(shapes[idx], shapes[(idx + 1) % n], local, samples=64, closed=True)
    d.poly(pts, GREEN, 2.0, closed=True)


def demo_motion_path(d, r, t):
    """anime.js motion path — follower rotates to face travel. sample_path + marker."""
    x0, y0, x1, y1 = r
    yc = (y0 + y1) / 2
    path = _sine_path(x0 + 8, x1 - 8, yc, (y1 - y0) * 0.32, 1.5, samples=60)
    d.poly(path, FAINT, 1.0)
    u = (t / 3.0) % 1.0
    px, py, ang = anim.sample_path(path, u)
    d.marker(px, py, anim.shape_triangle(), AMBER, angle=ang, scale=11.0, fill=True)
    # a short chevron trail
    for k in range(1, 4):
        uu = (u - k * 0.03) % 1.0
        qx, qy, qa = anim.sample_path(path, uu)
        d.marker(qx, qy, anim.shape_chevron(), anim.lerp_color(CYAN, (0, 0, 0, 0), k / 4), angle=qa, scale=7.0)


def demo_text_stagger(d, r, t):
    """anime.js split text — per char / word / line staggered entrances."""
    x0, y0, x1, y1 = r
    local = (t % 4.0)
    per_c = anim.text_entrance("ANIME.JS", local, by="chars", stagger=0.05,
                               duration=0.4, ease="outBack", slide=9.0, scale_from=0.3)
    d.text_fx("ANIME.JS", x0, y0 + 4, 24, CYAN, per_char=per_c)
    per_w = anim.text_entrance("MOTION IN ARCV", local, by="words", stagger=0.2,
                               duration=0.5, slide=6.0)
    d.text_fx("MOTION IN ARCV", x0, y0 + 40, 14, AMBER, per_char=per_w)
    per_l = anim.text_entrance("PER-LINE\nSTAGGER", local, by="lines", stagger=0.35,
                               duration=0.5, slide=8.0)
    d.text_fx("PER-LINE\nSTAGGER", x0, y0 + 66, 12, MAG, per_char=per_l, line_height=1.25)


def demo_timeline(d, r, t):
    """anime.js Timeline — chained/overlapping children with labels. tl.at(t)."""
    x0, y0, x1, y1 = r
    tl = anim.Timeline(loop=True, alternate=True)
    tl.add({"w": (0.0, 1.0)}, {"duration": 0.7, "ease": "outCubic"}, position=0.0)
    tl.add({"w": (0.0, 1.0)}, {"duration": 0.7, "ease": "outBack"}, position="-=0.45")
    tl.label("mid")
    tl.add({"w": (0.0, 1.0)}, {"duration": 0.7, "ease": "outElastic"}, position="mid+=0.1")
    tl.add({"w": (0.0, 1.0)}, {"duration": 0.7, "ease": "outQuint"}, position="-=0.35")
    snap = tl.at(t % tl.duration)
    rows = list(snap.items())
    rh = (y1 - y0) / len(rows)
    for k, (_cid, vals) in enumerate(rows):
        by0 = y0 + k * rh + 3
        by1 = y0 + (k + 1) * rh - 3
        w = (x1 - x0) * max(0.0, vals["w"])
        d.rrect_fill(x0, by0, x0 + max(2.0, w), by1, 3, anim.lerp_color(CYAN, MAG, k / len(rows)))
        d.rect(x0, by0, x1, by1, DIM, 1.0)


def demo_overshoot(d, r, t):
    """anime.js follow-through — back / elastic / spring settle to target."""
    x0, y0, x1, y1 = r
    dur = 2.2
    local = (t % DUR) % (dur + 0.6)
    sp = easing.spring(stiffness=120.0, damping=9.0)
    rows = [("back", easing.out_back, AMBER), ("elastic", easing.out_elastic, CYAN),
            ("spring", sp, GREEN)]
    rh = (y1 - y0) / len(rows)
    for k, (name, ez, col) in enumerate(rows):
        yy = y0 + (k + 0.5) * rh
        p = ez(min(1.0, local / dur))
        d.line(x0, yy, x1, yy, DIM, 1.0)
        d.disc(x0 + (x1 - x0 - 8) * p + 4, yy, 5.0, col)
        d.text(name, x0 + 2, yy - rh * 0.5 + 2, 10, LABEL)


def demo_loop_modes(d, r, t):
    """anime.js loop / alternate / reversed playback, expressed as pure timers."""
    x0, y0, x1, y1 = r
    rows = [
        ("loop", anim.Timer(1.2, loop=True)),
        ("alternate", anim.Timer(1.2, loop=True, alternate=True)),
        ("reversed", anim.Timer(1.2, loop=True, reversed=True)),
    ]
    rh = (y1 - y0) / len(rows)
    for k, (name, tm) in enumerate(rows):
        yy = y0 + (k + 0.5) * rh
        p = easing.in_out_quad(tm.at(t))
        d.line(x0, yy, x1, yy, DIM, 1.0)
        d.disc(x0 + (x1 - x0 - 8) * p + 4, yy, 5.0, anim.lerp_color(GREEN, AMBER, p))
        d.text(name, x0 + 2, yy - rh * 0.5 + 2, 10, LABEL)


def demo_signal_drag(d, r, t):
    """ScrollObserver → DriverFromSignal, and createDraggable → Draggable analogs."""
    x0, y0, x1, y1 = r
    midy = (y0 + y1) / 2
    # signal-driven gauge fill
    drv = DriverFromSignal(lo=-1.0, hi=1.0, ease="inOutSine")
    fill = drv.progress(math.sin(t * 0.9))
    d.text("SIGNAL", x0, y0, 10, LABEL)
    bx0, bx1 = x0, x1 - 4
    gy = y0 + 20
    d.rect(bx0, gy, bx1, gy + 14, DIM, 1.0)
    d.rrect_fill(bx0 + 1, gy + 1, bx0 + 1 + (bx1 - bx0 - 2) * fill, gy + 13, 2, CYAN)
    # drag handle following a Lissajous pointer (fresh per frame -> deterministic)
    d.text("DRAG", x0, midy + 6, 10, LABEL)
    dz = (x0, midy + 22, x1 - 4, y1 - 4)
    d.rect(*dz, DIM, 1.0)
    dcx, dcy = (dz[0] + dz[2]) / 2, (dz[1] + dz[3]) / 2
    ax, ay = (dz[2] - dz[0]) * 0.42, (dz[3] - dz[1]) * 0.4
    dg = Draggable((dcx, dcy), bounds=(dz[0] + 6, dz[1] + 6, dz[2] - 6, dz[3] - 6))
    dg.grab(dcx, dcy)
    dg.move(dcx + math.cos(t * 1.3) * ax, dcy + math.sin(t * 1.9) * ay)
    hx, hy = dg.value
    d.line(dcx, dcy, hx, hy, FAINT, 1.0)
    d.disc(hx, hy, 6.0, AMBER)
    d.ring(hx, hy, 10.0, CYAN, 1.5)


def demo_easing_showcase(d, r, t):
    """anime.js easing gallery — one racer per easing (incl. spring/elastic/bounce)."""
    x0, y0, x1, y1 = r
    d.text("EASING SHOWCASE", x0, y0 - 22, 13, LABEL)
    names = [
        "linear", "inOutQuad", "inOutCubic", "inOutQuart",
        "outQuint", "inOutSine", "inOutExpo", "inOutCirc",
        "outBack", "outElastic", "outBounce", "spring(1,120,10)",
        "inOutBack", "outCubic", "inQuad", "inOutBounce",
    ]
    prog = anim.Timer(2.0, loop=True, alternate=True).at(t)
    ncols = 2
    per_col = math.ceil(len(names) / ncols)
    cw = (x1 - x0) / ncols
    rh = (y1 - y0) / per_col
    for i, name in enumerate(names):
        col = i // per_col
        row = i % per_col
        lx = x0 + col * cw
        yy = y0 + (row + 0.5) * rh
        track0 = lx + 118
        track1 = lx + cw - 12
        ez = easing.get(name)
        p = ez(prog)
        dotx = track0 + (track1 - track0) * p
        d.line(track0, yy, track1, yy, DIM, 1.0)
        d.disc(dotx, yy, 3.2, anim.lerp_color(CYAN, MAG, min(1.0, max(0.0, p))))
        d.text(name, lx, yy - 6, 10, LABEL)


# ------------------------------------------------------------------- build
def _grid_rect(col, row, W, H):
    margin = 18
    top = 48
    strip_h = 150
    gap = 12
    gx0 = margin
    gx1 = W - margin
    gy0 = top
    gy1 = H - strip_h - margin
    pw = (gx1 - gx0 - 2 * gap) / 3
    ph = (gy1 - gy0 - 2 * gap) / 3
    x0 = gx0 + col * (pw + gap)
    y0 = gy0 + row * (ph + gap)
    return (x0, y0, x0 + pw, y0 + ph)


def build(d, W, H, t):
    """Render the whole gallery at time ``t`` onto drawing surface ``d``."""
    # title
    d.text("ARCV  ×  ANIME.JS  —  MOTION GALLERY", 20, 12, 20, CYAN)
    d.line(20, 40, W - 20, 40, BORDER, 1.5)
    d.text(f"t={t % DUR:04.1f}s", W - 130, 16, 13, LABEL)

    panels = [
        ((0, 0), "GRID STAGGER RIPPLE", demo_grid_ripple),
        ((1, 0), "SVG LINE DRAW-ON", demo_draw_on),
        ((2, 0), "SHAPE MORPH", demo_morph),
        ((0, 1), "MOTION PATH FOLLOWER", demo_motion_path),
        ((1, 1), "SPLIT TEXT STAGGER", demo_text_stagger),
        ((2, 1), "TIMELINE SEQUENCE", demo_timeline),
        ((0, 2), "OVERSHOOT / SETTLE", demo_overshoot),
        ((1, 2), "LOOP / ALT / REVERSED", demo_loop_modes),
        ((2, 2), "SIGNAL + DRAG ADAPTERS", demo_signal_drag),
    ]
    for (col, row), title, fn in panels:
        content = _panel(d, _grid_rect(col, row, W, H), title)
        fn(d, content, t)

    # full-width easing strip
    strip = (18, H - 150 + 22, W - 18, H - 18)
    d.rect(strip[0], strip[1] - 4, strip[2], strip[3], BORDER, 1.0)
    demo_easing_showcase(d, (strip[0] + 12, strip[1] + 8, strip[2] - 12, strip[3] - 10), t)
