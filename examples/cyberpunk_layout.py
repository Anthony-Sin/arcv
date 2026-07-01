"""The Cyberpunk-2077-style scanner HUD, authored once against the adapter
interface so the exact same layout renders through both OpenCV and ARCV.

Animation-aware: pass increasing `t` and the whole HUD *assembles* like Arwes —
strokes draw on, text deciphers/types, panels fade, elements stagger in, with a
loading spinner + analysis progress bar and idle motion once settled.

Coordinates are fractions of (W, H); sizes scale with H. `d` is an adapter.
"""

from __future__ import annotations

import math

from arcv.overlay import anim
from arcv.overlay.anim import Sequencer, flicker, linear, out_cubic

GREEN = (0.40, 0.97, 0.66, 1.0)
GREEN_DIM = (0.42, 0.86, 0.66, 0.65)
GREEN_FAINT = (0.42, 0.86, 0.66, 0.30)
WHITE = (0.88, 1.0, 0.94, 1.0)
RED = (1.0, 0.27, 0.27, 1.0)
RED_DIM = (1.0, 0.30, 0.30, 0.6)
YELLOW = (1.0, 0.82, 0.22, 1.0)
PANEL_FILL = (0.40, 0.95, 0.70, 0.06)


def _fade(c, a):
    return (c[0], c[1], c[2], c[3] * a)


def build(d, W, H, t=0.0):
    s = H / 600.0
    q = Sequencer(t)

    def X(fx):
        return fx * W

    def Y(fy):
        return fy * H

    _title(d, W, H, s, X, Y, t, q)
    _face_matching(d, W, H, s, X, Y, t, q)
    _scanner(d, W, H, s, X, Y, t, q)
    _threat_panel(d, W, H, s, X, Y, t, q)
    _terminal(d, W, H, s, X, Y, t, q)
    _actions(d, W, H, s, X, Y, t, q)
    _antenna(d, W, H, s, X, Y, t, q)


def _title(d, W, H, s, X, Y, t, q):
    x = X(0.205)
    p = q.at(0.0, 0.4, linear)
    d.line(X(0.197), Y(0.052), X(0.197), Y(0.098), GREEN, 2.0 * s, reveal=p)
    for i in range(3):
        if q.at(0.05 + i * 0.05, 0.2) > 0.5:
            d.rect(X(0.205) + i * 9 * s, Y(0.040), X(0.205) + i * 9 * s + 5 * s, Y(0.046), GREEN_DIM, 1.0 * s)
    if q.at(0.05, 0.3) > 0:
        d.text("TARGET // SUBSYSTEM", x, Y(0.052), 9 * s, GREEN_DIM)
    pt = q.at(0.1, 0.7)
    if pt > 0:
        d.text("Corporate Agent near Terminal #234", x, Y(0.070), 18 * s, WHITE, mode="decipher", t=t, progress=pt)


def _face_matching(d, W, H, s, X, Y, t, q):
    p = q.at(0.3, 0.5)
    if p <= 0:
        return
    a = flicker(p, t, seed=2.0)
    d.text("FACE", X(0.052), Y(0.395), 22 * s, _fade(RED, a))
    d.text("MATCHING", X(0.052), Y(0.430), 22 * s, _fade(RED, a))
    d.line(X(0.052), Y(0.470), X(0.052) + d.text_width("MATCHING", 22 * s), Y(0.470), _fade(RED_DIM, a), 1.0 * s, reveal=p)


def _scanner(d, W, H, s, X, Y, t, q):
    fx0, fy0, fx1, fy1 = X(0.305), Y(0.185), X(0.585), Y(0.560)
    cx, cy = (fx0 + fx1) * 0.5, (fy0 + fy1) * 0.5
    cl = 0.030 * W
    lw = 2.0 * s

    # glowing top-center highlight bar
    pb = q.at(0.2, 0.3, linear)
    d.line(cx - 0.07 * W, fy0 - 0.012 * H, cx + 0.07 * W, fy0 - 0.012 * H, GREEN, 3.2 * s, reveal=pb)
    d.line(cx - 0.05 * W, fy0 - 0.012 * H, cx + 0.05 * W, fy0 - 0.012 * H, WHITE, 1.4 * s, reveal=pb)

    # outer corner brackets (staggered)
    corners = [(fx0, 1, fy0, 1), (fx1, -1, fy0, 1), (fx0, 1, fy1, -1), (fx1, -1, fy1, -1)]
    for i, (ox, sx, oy, sy) in enumerate(corners):
        pc = q.stagger(i, 0.25, 0.05, 0.4, linear)
        d.poly([(ox, oy + sy * cl), (ox, oy), (ox + sx * cl, oy)], GREEN, lw, reveal=pc)

    # thin inner frame
    d.rect(fx0 + 0.018 * W, fy0 + 0.03 * H, fx1 - 0.018 * W, fy1 - 0.03 * H, GREEN_FAINT, 1.0 * s,
           reveal=q.at(0.45, 0.4, linear))

    # side wings with tick marks
    pw = q.at(0.4, 0.4, linear)
    for sx, edge in ((1, fx0), (-1, fx1)):
        bar = edge + sx * 0.014 * W
        d.line(bar, cy - 0.12 * H, bar, cy + 0.12 * H, GREEN_DIM, 1.2 * s, reveal=pw)
        for k in range(-3, 4):
            ty = cy + k * 0.03 * H
            d.line(bar, ty, bar + sx * 0.012 * W, ty, GREEN_DIM, 1.0 * s, reveal=q.at(0.5, 0.4))
        d.poly([(edge, cy - 0.07 * H), (edge - sx * 0.022 * W, cy - 0.04 * H),
                (edge - sx * 0.022 * W, cy + 0.04 * H), (edge, cy + 0.07 * H)], GREEN, lw, reveal=pw)

    # center reticle
    r = 0.045 * W
    pr = q.at(0.6, 0.4, linear)
    d.ring(cx, cy, r, GREEN, lw, reveal=pr)
    d.ring(cx, cy, r * 0.55, GREEN_DIM, 1.2 * s, reveal=pr)
    gap = r * 0.4
    pc2 = q.at(0.7, 0.3, linear)
    for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        d.line(cx + dx * gap, cy + dy * gap, cx + dx * r * 1.5, cy + dy * r * 1.5, GREEN, lw, reveal=pc2)
    if pr >= 1.0:  # idle: rotating ticks once assembled
        for k in range(8):
            a = k * math.pi / 4 + t * 0.5
            d.line(cx + math.cos(a) * r * 1.15, cy + math.sin(a) * r * 1.15,
                   cx + math.cos(a) * r * 1.32, cy + math.sin(a) * r * 1.32, GREEN_DIM, 1.0 * s)

    # loading spinner (top-right inside frame)
    if q.at(0.55, 0.2) > 0:
        spx, spy, spr = fx1 - 0.035 * W, fy0 + 0.055 * H, 0.013 * W
        d.ring(spx, spy, spr, GREEN_FAINT, 1.2 * s)
        a0 = t * 4.0
        d.ring(spx, spy, spr, GREEN, 1.8 * s, a0=a0, a1=a0 + math.pi * 1.3)

    # red scan target box (flicker-in)
    pbox = q.at(0.85, 0.3)
    if pbox > 0:
        ab = flicker(pbox, t, seed=5.0)
        d.rect(cx - 0.05 * W, cy - 0.06 * H, cx + 0.005 * W, cy + 0.0 * H, _fade(RED, ab), 1.6 * s, reveal=pbox)
        if pbox > 0.6:
            d.text("LOCK", cx - 0.05 * W, cy - 0.085 * H, 8 * s, _fade(RED, ab))

    # vertical "SCANNING" text (type-on)
    psc = q.at(0.6, 0.7)
    if psc > 0:
        word = "SCANNING"
        shown = int(round(psc * len(word)))
        for i, ch in enumerate(word[:shown]):
            d.text(ch, fx0 - 0.022 * W, fy0 + 0.06 * H + i * 0.028 * H, 11 * s, GREEN_DIM)

    # corner readouts + analysis progress bar (loading)
    if q.at(0.7, 0.4) > 0:
        d.text("00.348 / 12.6", fx0, fy1 + 0.012 * H, 8 * s, GREEN_DIM)
        d.text("// NEURAL SCAN ACTIVE", cx, fy0 - 0.035 * H, 8 * s, GREEN_DIM,
               align="center", mode="decipher", t=t, progress=q.at(0.7, 0.4))
    load = q.at(0.8, 1.4, linear)
    if load > 0:
        bx0, bx1, by = cx - 0.055 * W, cx + 0.055 * W, fy1 - 0.006 * H
        d.rect(bx0, by, bx1, by + 0.012 * H, GREEN_DIM, 1.0 * s)
        if load > 0.02:
            d.rect(bx0 + 1, by + 1, bx0 + (bx1 - bx0) * load, by + 0.012 * H - 1, GREEN, 1.0 * s)
            d.tri_fill((bx0, by + 1), (bx0, by + 0.012 * H - 1),
                       (bx0 + (bx1 - bx0) * load, by + 0.006 * H), _fade(GREEN, 0.4))
        d.text("ANALYSIS %d%%" % int(load * 87), bx1 + 0.01 * W, by - 0.002 * H, 8 * s, GREEN_DIM)


def _wtri(d, cx, cy, sz, color, s, reveal=1.0):
    d.tri((cx, cy - sz), (cx - sz, cy + sz), (cx + sz, cy + sz), color, 1.4 * s, reveal=reveal)
    d.line(cx, cy - sz * 0.2, cx, cy + sz * 0.45, color, 1.4 * s, reveal=reveal)
    if reveal >= 1.0:
        d.disc(cx, cy + sz * 0.72, max(1.2 * s, 1.0), color)


def _threat_panel(d, W, H, s, X, Y, t, q):
    px0, py0, px1, py1 = X(0.660), Y(0.345), X(0.815), Y(0.600)
    pfill = q.at(0.8, 0.5)
    if pfill <= 0:
        return
    d.rrect_fill(px0, py0, px1, py1, 14 * s, _fade(PANEL_FILL, pfill))
    d.rrect(px0, py0, px1, py1, 14 * s, GREEN, 1.8 * s, reveal=q.at(0.8, 0.5, linear))

    ix = px0 + 0.014 * W
    if q.at(1.0, 0.3) > 0:
        d.text("PROJECTED THREAT", ix, py0 + 0.022 * H, 8 * s, GREEN_DIM)
        d.text("MEDIUM", ix, py0 + 0.040 * H, 17 * s, WHITE, mode="decipher", t=t, progress=q.at(1.0, 0.4))
    d.line(px0 + 0.01 * W, py0 + 0.085 * H, px1 - 0.01 * W, py0 + 0.085 * H, GREEN_FAINT, 1.0 * s,
           reveal=q.at(1.05, 0.3, linear))
    if q.at(1.1, 0.3) > 0:
        d.text("DAMAGE TYPE", ix, py0 + 0.100 * H, 8 * s, GREEN_DIM)
        pa = q.at(1.15, 0.3)
        _wtri(d, ix + 0.010 * W, py0 + 0.140 * H, 0.013 * W, RED, s, reveal=pa)
        d.text("POISON", ix + 0.030 * W, py0 + 0.128 * H, 14 * s, RED, mode="decipher", t=t, progress=pa)
    for k in range(4):
        pk = q.stagger(k, 1.25, 0.08, 0.3)
        _wtri(d, ix + 0.012 * W + k * 0.030 * W, py0 + 0.195 * H, 0.011 * W, GREEN, s, reveal=pk)


def _icon_box(d, x, y, sz, s, reveal=1.0):
    d.rrect(x, y, x + sz, y + sz, 3 * s, GREEN_DIM, 1.2 * s, reveal=reveal)
    if reveal >= 1.0:
        d.tri_fill((x + sz * 0.32, y + sz * 0.3), (x + sz * 0.32, y + sz * 0.7), (x + sz * 0.68, y + sz * 0.5), GREEN)


def _terminal(d, W, H, s, X, Y, t, q):
    ph = q.at(1.0, 0.4)
    if ph <= 0:
        return
    d.text("Terminal #234", X(0.205), Y(0.660), 17 * s, WHITE, mode="decipher", t=t, progress=ph)
    ux0, ux1, uy = X(0.205), X(0.205) + d.text_width("Terminal #234", 17 * s) + 0.01 * W, Y(0.690)
    d.poly([(ux0, uy), (ux1 - 0.012 * W, uy), (ux1, uy - 0.012 * H)], GREEN, 1.6 * s, reveal=q.at(1.1, 0.3, linear))

    rows = [("GENERATES DEAFENING AUDIO", "DISTRACTION"),
            ("NETWORK ACCESS REQUIRED", "HACK VOLUME CONTROL")]
    for i, (sub, main) in enumerate(rows):
        pr = q.stagger(i, 1.2, 0.18, 0.4)
        if pr <= 0:
            continue
        y = Y(0.720) + i * 0.060 * H
        _icon_box(d, X(0.205), y, 0.020 * W, s, reveal=pr)
        tx = X(0.205) + 0.030 * W
        d.text(sub, tx, y, 8 * s, GREEN_DIM)
        d.text(main, tx, y + 0.022 * H, 13 * s, WHITE, mode="typeon", progress=pr)


def _button_circle(d, cx, cy, r, letter, color, s, reveal=1.0):
    d.ring(cx, cy, r, color, 1.6 * s, reveal=reveal)
    if reveal >= 1.0:
        d.text(letter, cx, cy - r * 0.62, r * 1.15, color, align="center")


def _actions(d, W, H, s, X, Y, t, q):
    y = Y(0.700)
    th = 13 * s
    r = 0.015 * W
    cy = y + 0.017 * H

    p0 = q.stagger(0, 1.4, 0.12, 0.3)
    if p0 > 0:
        bx0, bx1 = X(0.405), X(0.437)
        d.rrect(bx0, y, bx1, y + 0.034 * H, 5 * s, GREEN, 1.5 * s, reveal=p0)
        if p0 >= 1.0:
            d.text("LS", (bx0 + bx1) * 0.5, y + 0.006 * H, 11 * s, GREEN, align="center")
        d.text("Tag", bx1 + 0.009 * W, y + 0.005 * H, th, WHITE, mode="typeon", progress=p0)

    p1 = q.stagger(1, 1.4, 0.12, 0.3)
    if p1 > 0:
        cx = X(0.500)
        _button_circle(d, cx, cy, r, "X", RED, s, reveal=p1)
        d.text("Jam Agent's weapon", cx + r + 0.009 * W, y + 0.005 * H, th, WHITE, mode="typeon", progress=p1)

    p2 = q.stagger(2, 1.4, 0.12, 0.3)
    if p2 > 0:
        cx2 = X(0.745)
        _button_circle(d, cx2, cy, r, "Y", YELLOW, s, reveal=p2)
        d.text("Suicide!", cx2 + r + 0.009 * W, y + 0.005 * H, th, WHITE, mode="typeon", progress=p2)


def _antenna(d, W, H, s, X, Y, t, q):
    pa = q.at(1.5, 0.5)
    if pa <= 0:
        return
    d.text("ANTENNA SIGNAL STRENGTH", X(0.745), Y(0.660), 8 * s, GREEN_DIM)
    A = (X(0.755), Y(0.790))
    B = (X(0.875), Y(0.750))
    C = (X(0.915), Y(0.815))
    D = (X(0.795), Y(0.855))
    pp = q.at(1.5, 0.5, linear)
    d.poly([A, B, C, D], GREEN_DIM, 1.4 * s, closed=True, reveal=pp)

    def lerp(p, qy, u):
        return (p[0] + (qy[0] - p[0]) * u, p[1] + (qy[1] - p[1]) * u)

    pg = q.at(1.7, 0.4, linear)
    for k in range(1, 4):
        u = k / 4.0
        d.line(*lerp(A, D, u), *lerp(B, C, u), GREEN_FAINT, 1.0 * s, reveal=pg)
        d.line(*lerp(A, B, u), *lerp(D, C, u), GREEN_FAINT, 1.0 * s, reveal=pg)

    pts = [(0.30, 0.25), (0.55, 0.45), (0.42, 0.7), (0.7, 0.6), (0.8, 0.35), (0.25, 0.55)]
    for i, (uu, vv) in enumerate(pts):
        if q.stagger(i, 1.8, 0.05, 0.2) >= 1.0:
            top, bot = lerp(A, B, uu), lerp(D, C, uu)
            p = lerp(top, bot, vv)
            d.disc(p[0], p[1], 2.0 * s, GREEN)

    for i, lbl in enumerate(("150", "100", "050")):
        d.text(lbl, X(0.728), Y(0.770) + i * 0.030 * H, 8 * s, GREEN_DIM)
