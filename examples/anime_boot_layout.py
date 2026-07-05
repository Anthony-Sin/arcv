"""Layout for examples/anime_boot.py — the SAME target-scan HUD booting two ways.

LEFT  = the OLD motion layer only (arcv.overlay.anim.Sequencer): uniform staggered
        enter, arc-length ``reveal`` draw-on, whole-string decipher/type-on, one font.
RIGHT = the NEW anime.js model: a Timeline, grid ``stagger``, per-char/word
        ``text_entrance`` split text, spring/elastic/back overshoot, shape ``morph``,
        a ``sample_path`` motion-path sweep, and MULTIPLE fonts.

Both halves share the same skeleton positions (``_skel``) so the *assembly style*
is what differs. Everything is a pure function of ``t`` — the same build drives the
still, the GIF and the window.
"""

from __future__ import annotations

import math

from arcv import easing
from arcv.overlay import anim
from arcv.overlay.anim import Timer, Timeline, Stagger

TAU = math.pi * 2.0

# palettes: the old side is deliberately monochrome; the new side is richer.
OLD_C = (0.35, 0.85, 0.95, 1.0)
OLD_DIM = (0.2, 0.45, 0.55, 0.6)
NEW_C = (0.3, 0.95, 1.0, 1.0)
NEW_A = (1.0, 0.72, 0.24, 1.0)     # amber accent
NEW_M = (1.0, 0.4, 0.72, 1.0)      # magenta accent
NEW_G = (0.5, 1.0, 0.66, 1.0)      # green accent
DIM = (0.22, 0.45, 0.55, 0.5)
FAINT = (0.28, 0.5, 0.6, 0.35)

ROWS = [("RANGE", "128.4 M"), ("BEARING", "057.2"), ("LOCK", "98 PCT")]


def _clamp01(x):
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def _skel(R):
    """Shared layout skeleton (positions) derived from a half-rect ``R``."""
    x0, y0, x1, y1 = R
    w, h = x1 - x0, y1 - y0
    return {
        "frame": (x0 + 14, y0 + 30, x1 - 14, y1 - 14),
        "title": (x0 + 22, y0 + 6),
        "retic": (x0 + w * 0.30, y0 + h * 0.44),
        "retic_r": min(w, h) * 0.14,
        "grid": (x0 + w * 0.52, y0 + h * 0.26, x1 - 24, y0 + h * 0.56),
        "rows_x": x0 + w * 0.52,
        "rows_y": y0 + h * 0.64,
        "row_h": h * 0.1,
        "logo": (x0 + w * 0.24, y0 + h * 0.74),
        "logo_r": min(w, h) * 0.09,
        "bar": (x0 + 14, y1 - 22, x1 - 14, y1 - 14),
    }


def _hexagon(cx, cy, r, rot=0.0):
    return [(cx + r * math.cos(rot + TAU * i / 6), cy + r * math.sin(rot + TAU * i / 6)) for i in range(6)]


def _star(cx, cy, r, points=5, inner=0.46, rot=-math.pi / 2):
    pts = []
    for i in range(points * 2):
        rr = r if i % 2 == 0 else r * inner
        a = rot + math.pi * i / points
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


# =========================================================================
#  OLD — Sequencer + reveal + whole-string decipher/typeon, one font
# =========================================================================
def build_old(d, R, t):
    S = _skel(R)
    q = anim.Sequencer(t)
    C, DIMC = OLD_C, OLD_DIM

    fr = q.at(0.1, 0.8, anim.out_cubic)
    d.rrect(*S["frame"], 10, C, 1.5, reveal=fr)

    tp = q.at(0.6, 0.7, anim.linear)
    d.text("TARGET ACQUISITION", S["title"][0], S["title"][1], 17, C, mode="decipher", t=t, progress=tp)

    # reticle: ring + crosshair, uniform reveal
    cx, cy = S["retic"]
    rr = S["retic_r"]
    rp = q.at(0.9, 0.6, anim.out_cubic)
    d.ring(cx, cy, rr, C, 1.5, reveal=rp)
    ln = rr * 1.5 * rp
    d.line(cx - ln, cy, cx + ln, cy, C, 1.0)
    d.line(cx, cy - ln, cx, cy + ln, C, 1.0)
    d.disc(cx, cy, 2.5 * rp, C)

    # scanner grid — uniform linear stagger, dot radius scales with progress
    gx0, gy0, gx1, gy1 = S["grid"]
    cols, rows = 7, 4
    for j in range(rows):
        for i in range(cols):
            idx = j * cols + i
            p = q.stagger(idx, 1.2, 0.025, 0.4, anim.out_cubic)
            px = gx0 + (i + 0.5) * (gx1 - gx0) / cols
            py = gy0 + (j + 0.5) * (gy1 - gy0) / rows
            d.disc(px, py, 3.4 * p, DIMC if (idx % 3) else C)

    # readout rows — whole-string type-on
    for k, (lab, val) in enumerate(ROWS):
        p = q.at(1.6 + k * 0.2, 0.5, anim.linear)
        ry = S["rows_y"] + k * S["row_h"]
        d.text(lab, S["rows_x"], ry, 12, DIMC, mode="typeon", progress=p)
        d.text(val, S["rows_x"] + 110, ry, 12, C, mode="typeon", progress=p)

    # logo — static hexagon draw-on
    lx, ly = S["logo"]
    lp = q.at(1.4, 0.6, anim.out_cubic)
    d.poly(_hexagon(lx, ly, S["logo_r"]), C, 1.5, closed=True, reveal=lp)

    # scan bar
    bx0, by0, bx1, by1 = S["bar"]
    bp = q.at(2.0, 0.8, anim.out_cubic)
    d.rect(bx0, by0, bx1, by1, DIMC, 1.0)
    if bp > 0:
        d.rrect_fill(bx0 + 1, by0 + 1, bx0 + 1 + (bx1 - bx0 - 2) * bp, by1 - 1, 2, C)


# =========================================================================
#  NEW — Timeline + stagger + split-text + spring/elastic + morph + fonts
# =========================================================================
def build_new(d, R, t):
    S = _skel(R)
    C = NEW_C

    # frame + bar sequenced on a Timeline (labels/relative positions)
    tl = Timeline()
    tl.add({"reveal": (0.0, 1.0)}, {"duration": 0.8, "ease": "outCubic"}, position=0.1)
    tl.label("bar")
    tl.add({"w": (0.0, 1.0)}, {"duration": 0.9, "ease": "outElastic"}, position="bar+=1.9")
    snap = tl.at(t)
    frame_rev = snap["a0"]["reveal"]
    bar_w = _clamp01(snap["a1"]["w"])
    d.rrect(*S["frame"], 10, C, 1.5, reveal=frame_rev)

    # motion-path sweep: a chevron rides the frame perimeter facing travel
    if frame_rev >= 1.0:
        fr = S["frame"]
        perim = [(fr[0], fr[1]), (fr[2], fr[1]), (fr[2], fr[3]), (fr[0], fr[3])]
        u = (t * 0.45) % 1.0
        px, py, ang = anim.sample_path(perim, u, closed=True)
        d.marker(px, py, anim.shape_chevron(), NEW_A, angle=ang, scale=7.0, w=2.0)

    # title — per-CHARACTER split-text entrance, condensed DISPLAY font
    per = anim.text_entrance("TARGET ACQUISITION", t - 0.5, by="chars",
                             stagger=0.03, duration=0.4, ease="outBack",
                             slide=9.0, scale_from=0.35)
    d.text_fx("TARGET ACQUISITION", S["title"][0], S["title"][1], 18, C, per_char=per, font="display")

    # reticle — ring reveal + SPRING snap-in crosshair (overshoots, settles)
    cx, cy = S["retic"]
    rr = S["retic_r"]
    ring_rev = easing.out_cubic(_clamp01((t - 0.8) / 0.5))
    d.ring(cx, cy, rr, C, 1.5, reveal=ring_rev)
    sp = easing.spring(stiffness=190.0, damping=9.0)
    snap_p = sp(_clamp01((t - 1.1) / max(sp.duration, 1e-3)))
    ln = rr * 1.5 * snap_p
    d.line(cx - ln, cy, cx + ln, cy, NEW_A, 1.2)
    d.line(cx, cy - ln, cx, cy + ln, NEW_A, 1.2)
    d.disc(cx, cy, 2.6 * _clamp01(snap_p), NEW_M)

    # scanner grid — grid stagger from centre, each cell POPS in (outBack overshoot)
    gx0, gy0, gx1, gy1 = S["grid"]
    cols, rows = 7, 4
    delays = Stagger(0.05, grid=(cols, rows), from_="center").values(cols * rows)
    for idx in range(cols * rows):
        i, j = idx % cols, idx // cols
        p = easing.out_back(_clamp01((t - 1.2 - delays[idx]) / 0.45))
        px = gx0 + (i + 0.5) * (gx1 - gx0) / cols
        py = gy0 + (j + 0.5) * (gy1 - gy0) / rows
        col = anim.lerp_color(NEW_C, NEW_M, delays[idx] / (max(delays) or 1))
        d.disc(px, py, 3.6 * _clamp01(p) * (0.85 + 0.15 * p), col)

    # readout rows — per-WORD entrance labels (DIN) + value pop-in (TERM font)
    for k, (lab, val) in enumerate(ROWS):
        ry = S["rows_y"] + k * S["row_h"]
        perw = anim.text_entrance(lab, t - (1.6 + k * 0.15), by="words",
                                  stagger=0.12, duration=0.4, slide=5.0)
        d.text_fx(lab, S["rows_x"], ry, 12, DIM, per_char=perw, font="din")
        vp = anim.text_entrance(val, t - (1.72 + k * 0.15), by="chars",
                                stagger=0.02, duration=0.35, ease="outBack",
                                slide=4.0, scale_from=0.4)
        d.text_fx(val, S["rows_x"] + 110, ry, 12, NEW_A, per_char=vp, font="term")

    # logo — draw-on, then MORPH hexagon <-> star (a capability the old side lacks)
    lx, ly = S["logo"]
    lr = S["logo_r"]
    lp = _clamp01((t - 1.4) / 0.6)
    if lp < 1.0:
        d.poly(_hexagon(lx, ly, lr), NEW_G, 1.5, closed=True, reveal=easing.out_cubic(lp))
    else:
        m = 0.5 + 0.5 * math.sin((t - 2.0) * 1.6)
        pts = anim.morph(_hexagon(lx, ly, lr), _star(lx, ly, lr, 5), m, samples=48, closed=True)
        d.poly(pts, NEW_G, 1.5, closed=True)

    # scan bar — elastic settle
    bx0, by0, bx1, by1 = S["bar"]
    d.rect(bx0, by0, bx1, by1, DIM, 1.0)
    if bar_w > 0:
        d.rrect_fill(bx0 + 1, by0 + 1, bx0 + 1 + (bx1 - bx0 - 2) * bar_w, by1 - 1, 2, NEW_C)
