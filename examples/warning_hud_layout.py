"""ARCV — yellow "WARNING // TARGET ACQUISITION" HUD, laid over the OpenCV feed.

A rebuild in the visual language of ``examples/refs/gallery/ref1_reference.webp``
(bright cadmium-yellow angular panels, black content, hazard stripes, mode
cells, barcode, warning triangle, 7-seg timecode, waveform) — repurposed to show
only the *useful* computer-vision telemetry.

The left and right sides are **dynamic card stacks**: each side is a column of
small angular cards that *spawn and collapse as needed* (e.g. a DEPTH card while
tracking, an ALERT card while the target is lost, a secondary-target card only
when there are 2+ targets). The column reflows to fill itself, so there's no dead
space. The bottom stays a single status bar.

Cards are drawn OPAQUE through :class:`arcv.overlay.FlatOverlay`, and the
darkened camera shows through the central OPTICAL FEED window where the target
brackets + reticle lock on.

``build(d, W, H, t, st)`` draws one frame. ``st`` is a :class:`HudState` — either
scripted by :func:`state_at` (the boot -> LOCKED -> TARGET LOST -> REACQUIRE
story) or derived from live detections by :func:`state_from_detections`.
``st.cards`` maps each card id to a 0..1 "shown" amount that drives its
spawn/collapse. Everything animates and all text is Share Tech Mono.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from arcv.overlay.anim import Sequencer, clamp01, linear, out_cubic

# ----------------------------------------------------------------- palette
YEL = (0.96, 0.88, 0.06, 1.0)      # bright cadmium yellow (panel fill / HUD strokes on cam)
YEL_D = (0.78, 0.72, 0.05, 1.0)    # darker yellow (shading)
YEL_HI = (1.0, 0.95, 0.35, 1.0)    # hot highlight yellow
BLK = (0.05, 0.05, 0.04, 1.0)      # near-black content / outline on yellow
CHAR = (0.12, 0.12, 0.10, 1.0)     # charcoal (mode cells, 7-seg box, pills)
CHAR_HI = (0.44, 0.40, 0.06, 1.0)  # active mode cell (olive)
AMBER = (1.0, 0.60, 0.06, 1.0)     # caution accent
RED = (1.0, 0.24, 0.16, 1.0)       # alert
GREEN = (0.55, 1.0, 0.32, 1.0)     # ok

# ---------------------------------------------------------------- timeline
T_BOOT = 2.4
T_LOST = 6.0
T_REACQ = 9.4
DUR = 13.0


def _a(c, alpha):
    """Scale a color's alpha."""
    return (c[0], c[1], c[2], c[3] * alpha)


def _win(t, t0, t1, e=0.4):
    """1 inside [t0, t1] with eased edges of width e, 0 outside."""
    return min(clamp01((t - t0) / e), clamp01((t1 - t) / e))


# =====================================================================
#  STATE
# =====================================================================
@dataclass
class HudState:
    phase: str                       # boot | locked | lost | reacquire
    locked: bool
    alert: bool
    target: Tuple[float, float]      # primary center, UV in the viewport [0,1]
    box: Tuple[float, float]         # primary half-size, UV in the viewport
    boxes: List[Tuple[float, float, float, float]] = field(default_factory=list)
    n_targets: int = 0
    label: str = "TGT-00"
    conf: float = 0.0
    dist: Optional[float] = None
    bearing: Optional[float] = None
    fps: float = 0.0
    frm: int = 0
    timecode: str = "00:00:00"
    rec_s: int = 0
    sweep: float = 0.0
    signal: float = 0.8
    stage: int = 0                   # CV pipeline stage reached (0..4)
    cards: Dict[str, float] = field(default_factory=dict)  # card id -> shown 0..1


def _timecode(t: float) -> str:
    base = 41 + int(t)
    return "%02d:%02d:%02d" % (base // 3600 % 24, base // 60 % 60, base % 60)


def _scripted_cards(t: float, alert: bool) -> Dict[str, float]:
    """Deterministic spawn/collapse amounts for every card (works for any t, so
    out-of-order stills render correctly)."""
    def boot(delay):
        return out_cubic(clamp01((t - delay) / 0.4))

    lock_gate = 1.0 - _win(t, T_LOST, T_REACQ, 0.4)   # 0 while the target is lost
    alert_gate = _win(t, T_LOST, T_REACQ, 0.4)         # 1 while lost
    return {
        "L.STATUS": boot(0.25),
        "L.TRACK": boot(0.50),
        "L.PIPE": boot(0.75),
        "L.DEPTH": min(boot(0.95), lock_gate),
        "L.ALERT": alert_gate,
        "R.TELEM": boot(0.55),
        "R.QUAL": boot(0.75),
        "R.SIGNAL": boot(0.95),
        "R.RADAR": min(boot(1.05), lock_gate),
        "R.SEARCH": alert_gate,                                     # replaces RADAR while lost
        "R.SEC": (_win(t, 3.6, 5.4, 0.35) if not alert else 0.0),   # secondary target blips in
    }


def state_at(t: float) -> HudState:
    """Scripted CV-tracking story (drives the GIF / MP4 / stills)."""
    lost = T_LOST <= t < T_REACQ
    reacq = T_REACQ <= t < (T_REACQ + 0.6)
    phase = "boot" if t < T_BOOT else ("lost" if lost else ("reacquire" if reacq else "locked"))
    locked = not lost

    if lost:
        target = (0.5 + 0.20 * math.sin(t * 2.3), 0.5 + 0.14 * math.cos(t * 1.7))
        box = (0.11 + 0.02 * math.sin(t * 6.0), 0.17 + 0.02 * math.sin(t * 6.0))
        dist = bearing = None
        conf, n, sweep = 0.0, 0, t * 3.4
    else:
        drift = 0.0 if t < T_BOOT else 1.0
        target = (0.5 + 0.05 * math.sin(t * 0.7) * drift, 0.5 + 0.04 * math.cos(t * 0.9) * drift)
        box = (0.115, 0.20)
        dist = 2.35 + 0.06 * math.sin(t * 3.1)
        bearing = 3.0 + 2.0 * math.sin(t * 1.3)
        conf = 0.90 + 0.06 * math.sin(t * 2.2)
        n = 2 if (3.6 <= t <= 5.4) else 1
        sweep = t * 1.5

    stage = 4 if t >= T_BOOT else min(4, int((t / T_BOOT) * 4) + 1)
    if lost:
        stage = 3

    return HudState(
        phase=phase, locked=locked, alert=lost,
        target=target, box=box, boxes=[(target[0], target[1], box[0], box[1])],
        n_targets=n, label="TGT-00", conf=conf, dist=dist, bearing=bearing,
        fps=59.0 + 2.0 * math.sin(t * 5.0), frm=int(t * 30),
        timecode=_timecode(t), rec_s=int(t), sweep=sweep,
        signal=0.55 + 0.4 * (0.5 + 0.5 * math.sin(t * 1.7)), stage=stage,
        cards=_scripted_cards(t, lost),
    )


def state_from_detections(t: float, det, fps: float) -> HudState:
    """Live state from an OpenCV :class:`~arcv.vision.types.DetectionFrame`. Card
    amounts are instant 0/1 targets here; the runner smooths them over time."""
    boxes_uv: List[Tuple[float, float, float, float]] = []
    primary = None
    if det is not None and det.boxes:
        for i, b in enumerate(det.boxes):
            boxes_uv.append((b.cx, 1.0 - b.cy, b.hw, b.hh))
            if i == det.primary:
                primary = b
    have = primary is not None
    if have:
        target = (primary.cx, 1.0 - primary.cy)
        box = (max(primary.hw, 0.03), max(primary.hh, 0.04))
        conf = float(primary.score)
        dist = max(0.4, 0.42 / max(primary.hh, 0.04))
        label = (primary.label or "TGT-00").upper()
    else:
        target, box = (0.5, 0.5), (0.12, 0.18)
        conf, dist, label = 0.0, None, "-- -- --"

    cards = {
        "L.STATUS": 1.0, "L.TRACK": 1.0, "L.PIPE": 1.0,
        "L.DEPTH": 1.0 if have else 0.0, "L.ALERT": 0.0 if have else 1.0,
        "R.TELEM": 1.0, "R.QUAL": 1.0, "R.SIGNAL": 1.0,
        "R.RADAR": 1.0 if have else 0.0, "R.SEARCH": 0.0 if have else 1.0,
        "R.SEC": 1.0 if len(boxes_uv) > 1 else 0.0,
    }
    return HudState(
        phase="locked" if have else "lost", locked=have, alert=not have,
        target=target, box=box, boxes=boxes_uv, n_targets=len(boxes_uv),
        label=label, conf=conf, dist=dist,
        bearing=(target[0] - 0.5) * 60.0 if have else None,
        fps=fps, frm=int(t * max(fps, 1.0)), timecode=_timecode(t), rec_s=int(t),
        sweep=t * (1.5 if have else 3.4), signal=conf if have else 0.2,
        stage=4 if have else 3, cards=cards,
    )


# =====================================================================
#  LOCAL PRIMITIVES  (ref1 vocabulary; convex so fills fade cleanly)
# =====================================================================
def _centroid(pts):
    n = len(pts)
    return (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n)


def fillp(d, pts, c):
    """Opaque convex-polygon fill via a centroid triangle fan (single layer, so
    partial alpha stays uniform for the materialize animation)."""
    cx, cy = _centroid(pts)
    n = len(pts)
    for i in range(n):
        d.tri_fill((cx, cy), pts[i], pts[(i + 1) % n], c)


def chamfer(x0, y0, x1, y1, tl=0.0, tr=0.0, br=0.0, bl=0.0):
    """A rectangle with per-corner 45deg chamfers (stays convex)."""
    pts = []
    pts.append((x0 + tl, y0)) if tl else pts.append((x0, y0))
    if tr:
        pts.append((x1 - tr, y0)); pts.append((x1, y0 + tr))
    else:
        pts.append((x1, y0))
    if br:
        pts.append((x1, y1 - br)); pts.append((x1 - br, y1))
    else:
        pts.append((x1, y1))
    if bl:
        pts.append((x0 + bl, y1)); pts.append((x0, y1 - bl))
    else:
        pts.append((x0, y1))
    if tl:
        pts.append((x0, y0 + tl))
    return pts


def corner_ticks(d, x0, y0, x1, y1, c, ln=12.0, inset=8.0, w=1.6):
    for (cx, sx) in ((x0 + inset, 1), (x1 - inset, -1)):
        for (cy, sy) in ((y0 + inset, 1), (y1 - inset, -1)):
            d.line(cx, cy, cx + sx * ln, cy, c, w)
            d.line(cx, cy, cx, cy + sy * ln, c, w)


def _clip_seg(x0, y0, x1, y1, cx0, cy0, cx1, cy1):
    dx, dy = x1 - x0, y1 - y0
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


def hazard_stripes(d, x0, y0, x1, y1, c, sw=9.0, gap=9.0, w=6.0):
    bh = y1 - y0
    x = x0 - bh
    while x < x1 + bh:
        seg = _clip_seg(x, y1, x + bh, y0, x0, y0, x1, y1)
        if seg:
            (a, b), (cc, dd) = seg
            d.line(a, b, cc, dd, c, w)
        x += sw + gap


def barcode(d, x0, y0, x1, y1, c, seed=1):
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
    p0, p1, p2 = (cx, cy - r), (cx - r * 0.9, cy + r * 0.72), (cx + r * 0.9, cy + r * 0.72)
    if fill is not None:
        d.tri_fill(p0, p1, p2, fill)
    d.tri(p0, p1, p2, c, w)
    d.rect(cx, cy - r * 0.28, cx, cy + r * 0.28, c, max(2.0, r * 0.16))
    d.disc(cx, cy + r * 0.48, max(1.6, r * 0.10), c)


def biohazard(d, cx, cy, r, c, bg):
    ang0 = -math.pi / 2
    d_lobe, Ro, Ri = r * 0.50, r * 0.58, r * 0.22
    for k in range(3):
        a = ang0 + k * (2 * math.pi / 3)
        d.disc(cx + math.cos(a) * d_lobe, cy + math.sin(a) * d_lobe, Ro, c)
    for k in range(3):
        a = ang0 + k * (2 * math.pi / 3)
        d.disc(cx + math.cos(a) * d_lobe, cy + math.sin(a) * d_lobe, Ri, bg)
    d.disc(cx, cy, r * 0.28, c)
    d.disc(cx, cy, r * 0.20, bg)
    d.disc(cx, cy, r * 0.12, c)


def hexagon(d, cx, cy, r, c, w=2.0):
    pts = [(cx + math.cos(math.pi / 6 + k * math.pi / 3) * r,
            cy + math.sin(math.pi / 6 + k * math.pi / 3) * r) for k in range(6)]
    d.poly(pts, c, w, closed=True)


def waveform(d, x0, x1, cy, c, n=54, amp=1.0, seed=3, w=2.0):
    dx = (x1 - x0) / n
    r = seed * 2246822519 & 0xFFFFFFFF
    for i in range(n):
        r = (1103515245 * r + 12345) & 0xFFFFFFFF
        env = math.sin(i / n * math.pi) ** 0.6
        h = (0.12 + ((r >> 16) % 100) / 100.0) * amp * env
        x = x0 + i * dx
        d.line(x, cy - h, x, cy + h, c, w)


def crescent_globe(d, cx, cy, r, c, bg, w=2.0):
    d.ring(cx, cy, r, c, w)
    for k in (-0.6, -0.3, 0.0, 0.3, 0.6):
        yy = cy + k * r
        hw = math.sqrt(max(0.0, r * r - (k * r) ** 2))
        d.line(cx - hw, yy, cx + hw, yy, c, w * 0.55)
        xx = cx + k * r
        hh = math.sqrt(max(0.0, r * r - (k * r) ** 2))
        d.line(xx, cy - hh, xx, cy + hh, c, w * 0.55)
    mr = r * 0.62
    d.disc(cx - r * 0.10, cy, mr, c)
    d.disc(cx - r * 0.10 + mr * 0.55, cy - mr * 0.08, mr * 0.95, bg)


def _dashes(d, x0, y0, x1, c, dash=8, gap=5, w=2.4):
    x = x0
    while x < x1:
        d.line(x, y0, min(x + dash, x1), y0, c, w)
        x += dash + gap


def _tick_strip(d, x0, y0, x1, c, n=22, w=1.4):
    dx = (x1 - x0) / n
    for i in range(n):
        h = 3 if i % 2 == 0 else 6
        x = x0 + i * dx
        d.line(x, y0 - h * 0.5, x, y0 + h * 0.5, c, w)


def seven_seg_box(d, x0, y0, x1, y1, text, s):
    pts = chamfer(x0, y0, x1, y1, tr=8)
    fillp(d, pts, CHAR)
    d.poly(pts, BLK, 1.6 * s, closed=True)
    d.text(text, (x0 + x1) * 0.5, y0 + (y1 - y0) * 0.24, (y1 - y0) * 0.52, YEL, align="center")


# =====================================================================
#  CARD STACK  (the dynamic left / right columns)
# =====================================================================
def _card_frame(d, x0, y0, x1, y1, op, s, title, accent, W, H):
    """A single angular card: yellow fill (alpha=op), drawn-on outline, and a
    slim header tab with its title. ``accent`` -> red header (alert cards)."""
    pts = chamfer(x0, y0, x1, y1, tr=14 * s, bl=14 * s)
    fillp(d, pts, _a(YEL, op))
    d.poly(pts, BLK, 2.0 * s, closed=True, reveal=op)
    if op < 0.45:
        return
    corner_ticks(d, x0 + 3 * s, y0 + 3 * s, x1 - 3 * s, y1 - 3 * s, _a(BLK, 0.8),
                 ln=8 * s, inset=6 * s, w=1.2 * s)
    hdr = 0.028 * H
    hpts = chamfer(x0, y0, x1, y0 + hdr, tr=14 * s)
    fillp(d, hpts, _a(RED if accent else BLK, op))
    d.text(title, x0 + 0.012 * W, y0 + 0.005 * H, 12 * s, YEL, mode="typeon", progress=op)


def _column(d, defs, x0, x1, y_top, y_bot, s, st, t, W, H):
    """Lay a stack of cards top->bottom, reflowing to fill the column height so
    disappearing cards leave no dead space. ``defs`` = list of
    (card_id, height_frac, title, content_fn, accent)."""
    gap0 = 0.014 * H
    vis = []
    for (cid, frac, title, cfn, accent) in defs:
        op = out_cubic(clamp01(st.cards.get(cid, 0.0)))
        if op <= 0.01:
            continue
        vis.append((cid, frac * H * op, title, cfn, accent, op))
    if not vis:
        return
    sum_h = sum(v[1] for v in vis)
    n = len(vis)
    avail = y_bot - y_top
    gap = min(0.08 * H, max(gap0, (avail - sum_h) / (n - 1))) if n > 1 else 0.0

    y = y_top
    hdr = 0.028 * H
    for (cid, h, title, cfn, accent, op) in vis:
        _card_frame(d, x0, y, x1, y + h, op, s, title, accent, W, H)
        cp = clamp01((op - 0.82) / 0.18)
        if cp > 0 and cfn is not None:
            cfn(d, x0 + 0.012 * W, y + hdr + 0.006 * H, x1 - 0.012 * W, cp, s, st, t, W, H)
        y += h + gap


# ------------------------------------------------------- left card contents
def _c_status(d, ix, iy, xr, cp, s, st, t, W, H):
    if st.phase == "boot":
        status, scol = "ACQUIRING", BLK
    elif st.locked:
        status, scol = "LOCKED", BLK
    else:
        status, scol = "TARGET LOST", RED
    d.text(status, ix, iy, 23 * s, scol, mode="decipher", t=t, progress=cp)
    d.text("SESSION 9B7 / 192D41", ix, iy + 0.040 * H, 9 * s, _a(BLK, 0.7))
    d.text("LOCK %02d:%02d" % (st.rec_s // 60, st.rec_s % 60), ix, iy + 0.058 * H, 11 * s, _a(BLK, 0.85))
    biohazard(d, xr - 0.02 * W, iy + 0.030 * H, 13 * s, BLK, YEL)


def _c_track(d, ix, iy, xr, cp, s, st, t, W, H):
    rows = [
        ("TARGETS", "%02d" % st.n_targets),
        ("PRIMARY", st.label),
        ("CONFIDENCE", "%3.0f%%" % (st.conf * 100)),
        ("DISTANCE", ("%.2f m" % st.dist) if st.dist is not None else "--.- m"),
    ]
    for i, (k, v) in enumerate(rows):
        yy = iy + i * 0.040 * H
        d.text(k, ix, yy, 10 * s, _a(BLK, 0.7))
        d.text(v, xr, yy, 14 * s, BLK, align="right", mode="typeon", progress=cp)
        _dashes(d, ix, yy + 0.020 * H, xr, _a(BLK, 0.4), dash=5 * s, gap=4 * s, w=1.2 * s)


def _c_pipeline(d, ix, iy, xr, cp, s, st, t, W, H):
    cells = ["CAM", "DET", "TRK", "LCK"]
    g = 6 * s
    cw = (xr - ix - 3 * g) / 4.0
    ch = 0.052 * H
    for i, lab in enumerate(cells):
        cx0 = ix + i * (cw + g)
        cx1 = cx0 + cw
        active = i < st.stage
        lost_lock = st.alert and lab == "LCK"
        cpts = chamfer(cx0, iy, cx1, iy + ch, br=7 * s, bl=7 * s)
        if lost_lock:
            fillp(d, cpts, _a(RED, 0.5 + 0.5 * (0.5 + 0.5 * math.sin(t * 9))))
            tcol = YEL
        elif active:
            fillp(d, cpts, CHAR_HI)
            tcol = YEL
        else:
            fillp(d, cpts, CHAR)
            tcol = _a(YEL_D, 0.6)
        d.poly(cpts, BLK, 1.5 * s, closed=True)
        d.text(lab, (cx0 + cx1) * 0.5, iy + ch * 0.28, 12 * s, tcol, align="center")


def _c_depth(d, ix, iy, xr, cp, s, st, t, W, H):
    active = st.locked
    for k in range(5):
        yy = iy + 0.006 * H + k * 0.018 * H
        base = (0.5 + 0.5 * math.sin(t * 2.0 + k * 0.7)) if active else 0.12
        wv = (0.25 + 0.7 * base) * (xr - ix - 0.06 * W)
        d.line(ix, yy, ix + wv, yy, _a(BLK, 0.6), 2.4 * s)
    biohazard(d, xr - 0.028 * W, iy + 0.040 * H, 14 * s, BLK, YEL)
    d.text("INPUT DATA · CV · 0x0A71", ix, iy + 0.098 * H, 8 * s, _a(BLK, 0.7))


def _c_alert(d, ix, iy, xr, cp, s, st, t, W, H):
    fl = 0.5 + 0.5 * math.sin(t * 9)
    d.text("SIGNAL LOST", ix, iy, 15 * s, _a(RED, 0.6 + 0.4 * fl), mode="decipher", t=t, progress=cp)
    d.text("REACQUIRE IN PROGRESS", ix, iy + 0.030 * H, 9 * s, _a(RED, 0.85))
    warning_triangle(d, xr - 0.03 * W, iy + 0.028 * H, 15 * s, RED, 2.0 * s, fill=_a(RED, 0.12 * fl))
    # red hazard strip
    hy = iy + 0.056 * H
    d.rect(ix, hy, xr, hy + 0.020 * H, RED, 1.4 * s)
    hazard_stripes(d, ix + 2 * s, hy + 2 * s, xr - 2 * s, hy + 0.020 * H - 2 * s,
                   _a(RED, 0.9), sw=7 * s, gap=7 * s, w=4 * s)


# ------------------------------------------------------ right card contents
def _c_telemetry(d, ix, iy, xr, cp, s, st, t, W, H):
    rows = [
        ("POS X", "%+.3f" % (st.target[0] * 2 - 1)),
        ("POS Y", "%+.3f" % (1 - st.target[1] * 2)),
        ("SIZE", "%.2f x %.2f" % (st.box[0] * 2, st.box[1] * 2)),
        ("BEARING", ("%+.1f deg" % st.bearing) if st.bearing is not None else "--.-"),
    ]
    for i, (k, v) in enumerate(rows):
        yy = iy + i * 0.038 * H
        d.text(k, ix, yy, 10 * s, _a(BLK, 0.7))
        d.text(v, xr, yy, 13 * s, BLK, align="right", mode="typeon", progress=cp)
        _dashes(d, ix, yy + 0.019 * H, xr, _a(BLK, 0.4), dash=5 * s, gap=4 * s, w=1.2 * s)


def _c_signal(d, ix, iy, xr, cp, s, st, t, W, H):
    seed = 3 + int(t * 3) % 11
    waveform(d, ix, xr, iy + 0.028 * H, BLK, n=42,
             amp=0.026 * H * (0.5 + st.signal), seed=seed, w=2.0 * s)


def _c_quality(d, ix, iy, xr, cp, s, st, t, W, H):
    segs = 12
    swid = (xr - ix) / segs
    lit = int(st.signal * segs) if st.locked else 2
    for i in range(segs):
        sx0 = ix + i * swid
        if i < lit:
            d.rect(sx0 + swid * 0.5, iy + 0.006 * H, sx0 + swid * 0.5, iy + 0.026 * H, BLK, swid * 0.62)
        else:
            d.rect(sx0 + 1 * s, iy + 0.006 * H, sx0 + swid - 2 * s, iy + 0.026 * H, _a(BLK, 0.45), 1.2 * s)
    d.text("LINK %3.0f%%" % (st.signal * 100), ix, iy + 0.034 * H, 9 * s, _a(BLK, 0.7))


def _c_radar(d, ix, iy, xr, cp, s, st, t, W, H):
    cx, cy, r = (ix + xr) * 0.5, iy + 0.075 * H, 0.052 * W
    d.ring(cx, cy, r, BLK, 1.6 * s)
    d.ring(cx, cy, r * 0.6, _a(BLK, 0.6), 1.0 * s)
    d.line(cx - r, cy, cx + r, cy, _a(BLK, 0.6), 1.0 * s)
    d.line(cx, cy - r, cx, cy + r, _a(BLK, 0.6), 1.0 * s)
    for k in range(5):
        a = st.sweep - k * 0.12
        d.line(cx, cy, cx + math.cos(a) * r, cy + math.sin(a) * r, _a(BLK, 0.5 * (1 - k / 5.0)), 1.6 * s)
    if st.locked:
        ba = math.radians((st.bearing or 0) - 90)
        bx, by2 = cx + math.cos(ba) * r * 0.7, cy + math.sin(ba) * r * 0.7
        pulse = 2.5 * s + 1.5 * s * (0.5 + 0.5 * math.sin(t * 6))
        d.disc(bx, by2, pulse, BLK)
    d.text("XT16 · FWD 1", cx, cy + r + 0.010 * H, 8 * s, _a(BLK, 0.7), align="center")


def _c_secondary(d, ix, iy, xr, cp, s, st, t, W, H):
    d.text("CLASS  DYNAMIC", ix, iy, 10 * s, _a(BLK, 0.7))
    d.text("CONF   82%", ix, iy + 0.020 * H, 12 * s, BLK, mode="typeon", progress=cp)
    d.text("TRACK  ASSIST", ix, iy + 0.040 * H, 10 * s, _a(BLK, 0.7))


def _c_search(d, ix, iy, xr, cp, s, st, t, W, H):
    d.text("LAST KNOWN", ix, iy, 9 * s, _a(RED, 0.8))
    d.text("X %+.2f  Y %+.2f" % (st.target[0] * 2 - 1, 1 - st.target[1] * 2),
           ix, iy + 0.017 * H, 11 * s, _a(RED, 0.9), mode="typeon", progress=cp)
    d.text("ELAPSED %02ds" % max(0, st.rec_s - int(T_LOST)), ix, iy + 0.040 * H, 9 * s, _a(RED, 0.8))
    hy = iy + 0.058 * H
    d.rect(ix, hy, xr, hy + 0.018 * H, RED, 1.4 * s)
    sweepx = ix + (xr - ix) * ((t * 0.5) % 1.0)
    d.line(sweepx, hy, sweepx, hy + 0.018 * H, _a(RED, 0.9), 2.2 * s)


LEFT_CARDS = [
    ("L.STATUS", 0.135, "TRACK · STATUS", _c_status, False),
    ("L.TRACK", 0.185, "TARGET", _c_track, False),
    ("L.PIPE", 0.100, "CV PIPELINE", _c_pipeline, False),
    ("L.DEPTH", 0.150, "DEPTH SCAN", _c_depth, False),
    ("L.ALERT", 0.135, "! ALERT", _c_alert, True),
]

RIGHT_CARDS = [
    ("R.TELEM", 0.165, "TELEMETRY", _c_telemetry, False),
    ("R.SIGNAL", 0.075, "SIGNAL", _c_signal, False),
    ("R.QUAL", 0.080, "LINK QUALITY", _c_quality, False),
    ("R.RADAR", 0.175, "BEARING", _c_radar, False),
    ("R.SEARCH", 0.135, "! SEARCH", _c_search, True),
    ("R.SEC", 0.090, "TGT-01", _c_secondary, False),
]


# =====================================================================
#  BUILD
# =====================================================================
VP = (0.263, 0.150, 0.737, 0.828)   # viewport rect (the panel-free camera window)


def build(d, W, H, t=0.0, st: Optional[HudState] = None):
    if st is None:
        st = state_at(t)
    s = H / 720.0

    def X(f):
        return f * W

    def Y(f):
        return f * H

    _viewport(d, W, H, s, X, Y, t, Sequencer(t), st)
    _topbar(d, W, H, s, X, Y, t, Sequencer(t), st)
    _column(d, LEFT_CARDS, X(0.018), X(0.250), Y(0.120), Y(0.828), s, st, t, W, H)
    _column(d, RIGHT_CARDS, X(0.750), X(0.982), Y(0.120), Y(0.828), s, st, t, W, H)
    _bottom(d, W, H, s, X, Y, t, Sequencer(t), st)
    if st.alert:
        _alert_border(d, W, H, s, X, Y, t)


# ---------------------------------------------------------------- top bar
def _topbar(d, W, H, s, X, Y, t, q, st):
    p = q.at(0.0, 0.45)
    if p <= 0:
        return
    x0, y0, x1, y1 = X(0.018), Y(0.028), X(0.982), Y(0.100)
    pts = chamfer(x0, y0, x1, y1, tr=16, br=10)
    fillp(d, pts, _a(BLK, 0.92 * p))
    d.poly(pts, _a(YEL, p), 2.0 * s, closed=True, reveal=q.at(0.0, 0.5, linear))
    ix = x0 + 0.014 * W
    if q.at(0.1, 0.4) > 0:
        biohazard(d, ix + 12 * s, (y0 + y1) * 0.5, 13 * s, YEL, BLK)
    title = "! WARNING  //  TARGET LOST" if st.alert else "ARCV  //  OPTICAL TARGET ACQUISITION"
    tcol = _a(RED, 0.5 + 0.5 * (0.5 + 0.5 * math.sin(t * 9))) if st.alert else YEL
    d.text(title, ix + 30 * s, y0 + 0.012 * H, 20 * s, tcol, mode="decipher", t=t, progress=q.at(0.15, 0.6))
    d.text("SYS 17-WW-22-000  ·  LINK OK  ·  CV PIPELINE ACTIVE", ix + 30 * s, y0 + 0.048 * H,
           10 * s, _a(YEL_D, p))
    if q.at(0.2, 0.5) > 0:
        blink = (t % 1.0) < 0.5
        rx = X(0.70)
        d.disc(rx, (y0 + y1) * 0.5 - 3 * s, 4 * s, RED if blink else _a(RED, 0.35))
        d.text("REC", rx + 10 * s, y0 + 0.012 * H, 15 * s, YEL)
        d.text("T %s" % st.timecode, rx + 10 * s, y0 + 0.050 * H, 10 * s, _a(YEL_D, 1))
        d.text("FRM %05d" % st.frm, X(0.815), y0 + 0.012 * H, 13 * s, YEL)
        d.text("%4.1f FPS" % st.fps, X(0.815), y0 + 0.050 * H, 10 * s, _a(YEL_D, 1))
        gx, gy = X(0.905), (y0 + y1) * 0.5
        d.tri_fill((gx, gy), (gx + 8 * s, gy - 5 * s), (gx + 8 * s, gy + 5 * s), YEL)
        d.rect(gx + 13 * s, gy - 5 * s, gx + 23 * s, gy + 5 * s, YEL, 1.4 * s)
        d.tri_fill((gx + 46 * s, gy), (gx + 38 * s, gy - 5 * s), (gx + 38 * s, gy + 5 * s), YEL)


# ---------------------------------------------------------------- viewport
def _viewport(d, W, H, s, X, Y, t, q, st):
    fx0, fy0, fx1, fy1 = X(VP[0]), Y(VP[1]), X(VP[2]), Y(VP[3])
    accent = RED if st.alert else YEL
    lw = 2.0 * s

    cl = 0.03 * W
    for i, (ox, sx, oy, sy) in enumerate(
        ((fx0, 1, fy0, 1), (fx1, -1, fy0, 1), (fx0, 1, fy1, -1), (fx1, -1, fy1, -1))
    ):
        pc = q.stagger(i, 0.2, 0.05, 0.4, linear)
        d.poly([(ox, oy + sy * cl), (ox, oy), (ox + sx * cl, oy)], YEL, lw, reveal=pc)
    d.rect(fx0, fy0, fx1, fy1, _a(YEL, 0.25), 1.0 * s, reveal=q.at(0.35, 0.4, linear))

    if q.at(0.3, 0.4) > 0:
        d.text("OPTICAL FEED · CV-01", fx0 + 6 * s, fy0 + 6 * s, 10 * s, _a(YEL, 0.8))
        _tick_strip(d, fx0 + 0.14 * W, fy0 + 12 * s, fx1 - 6 * s, _a(YEL, 0.6), n=30, w=1.2 * s)

    if st.locked and q.at(0.6, 0.4) > 0:
        sy = fy0 + (fy1 - fy0) * ((t * 0.35) % 1.0)
        d.line(fx0 + 2 * s, sy, fx1 - 2 * s, sy, _a(YEL, 0.35), 1.4 * s)

    for k, (cx, cy, hw, hh) in enumerate(st.boxes[1:], start=1):
        bx, by = fx0 + (fx1 - fx0) * cx, fy0 + (fy1 - fy0) * cy
        bw, bh = hw * (fx1 - fx0), hh * (fy1 - fy0)
        for (sx, sy2) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            cx0, cy0 = bx + sx * bw, by + sy2 * bh
            aa = 0.3 * min(bw, bh)
            d.poly([(cx0 - sx * aa, cy0), (cx0, cy0), (cx0, cy0 - sy2 * aa)], _a(YEL, 0.6), 1.4 * s)
        d.text("TGT-%02d" % k, bx - bw, by - bh - 0.016 * H, 8 * s, _a(YEL, 0.6))

    pr = q.at(0.6, 0.45)
    if pr <= 0:
        return
    tx = fx0 + (fx1 - fx0) * st.target[0]
    ty = fy0 + (fy1 - fy0) * st.target[1]
    bw = st.box[0] * (fx1 - fx0)
    bh = st.box[1] * (fy1 - fy0)
    a = 0.42 * min(bw, bh)
    if st.alert:
        a *= 1.0 + 0.2 * math.sin(t * 8)
    for (sx, sy2) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        cx0, cy0 = tx + sx * bw, ty + sy2 * bh
        d.poly([(cx0 - sx * a, cy0), (cx0, cy0), (cx0, cy0 - sy2 * a)], accent, 2.0 * s, reveal=pr)

    if st.locked:
        r = min(bw, bh) * 0.5
        d.ring(tx, ty, r, accent, 1.5 * s, reveal=pr)
        g = r * 0.45
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            d.line(tx + dx * g, ty + dy * g, tx + dx * r * 1.7, ty + dy * r * 1.7, accent, 1.4 * s, reveal=pr)
        for k in range(6):
            ang = t * 0.8 + k * math.pi / 3
            d.line(tx + math.cos(ang) * r * 1.2, ty + math.sin(ang) * r * 1.2,
                   tx + math.cos(ang) * r * 1.34, ty + math.sin(ang) * r * 1.34, _a(accent, 0.7), 1.0 * s)
        vstate = "ACQUIRING" if st.phase == "boot" else "LOCKED"
        d.text("%s · %s" % (st.label, vstate), tx - bw, ty - bh - 0.020 * H, 11 * s, accent)
        rx = tx + bw + 0.010 * W
        d.text("DIST", rx, ty - bh, 9 * s, _a(YEL, 0.7))
        d.text("%.2f m" % (st.dist or 0), rx, ty - bh + 0.016 * H, 13 * s, YEL)
        d.text("CONF", rx, ty - bh + 0.044 * H, 9 * s, _a(YEL, 0.7))
        d.text("%3.0f%%" % (st.conf * 100), rx, ty - bh + 0.060 * H, 13 * s, YEL)
    else:
        rr = min(bw, bh) * (0.6 + 0.25 * math.sin(t * 3.0))
        for k in range(6):
            a0 = t * 2.0 + k * math.pi / 3
            d.ring(tx, ty, rr, _a(RED, 0.8), 1.6 * s, a0=a0, a1=a0 + 0.5)
        sweep_y = ty - bh + (2 * bh) * ((t * 0.8) % 1.0)
        d.line(tx - bw, sweep_y, tx + bw, sweep_y, _a(RED, 0.7), 1.4 * s)
        fl = 0.5 + 0.5 * math.sin(t * 10)
        d.text("! SEARCHING — TARGET LOST", (fx0 + fx1) * 0.5, fy0 + (fy1 - fy0) * 0.5 - 0.10 * H,
               13 * s, _a(RED, 0.5 + 0.5 * fl), align="center")


# ---------------------------------------------------------------- bottom bar
def _bottom(d, W, H, s, X, Y, t, q, st):
    p = q.at(0.9, 0.5)
    if p <= 0:
        return
    x0, y0, x1, y1 = X(0.018), Y(0.858), X(0.982), Y(0.966)
    pts = chamfer(x0, y0, x1, y1, tl=12, tr=12)
    fillp(d, pts, _a(YEL, p))
    d.poly(pts, BLK, 2.2 * s, closed=True, reveal=q.at(0.9, 0.55, linear))
    ix = x0 + 0.016 * W

    barcode(d, ix, y0 + 0.018 * H, ix + 0.14 * W, y1 - 0.030 * H, BLK, seed=7)
    d.text("744-NRC-445 REV A1  ·  DATA STREAM", ix, y1 - 0.026 * H, 9 * s, _a(BLK, 0.7))

    pbx0, pby0, pbx1, pby1 = X(0.185), y0 + 0.028 * H, X(0.520), y0 + 0.058 * H
    d.rect(pbx0, pby0, pbx1, pby1, BLK, 1.6 * s)
    fillv = st.conf if st.locked else (0.5 + 0.5 * math.sin(t * 3)) * 0.4
    fx = pbx0 + (pbx1 - pbx0) * fillv
    aw = max(d.text_width("* ", (pby1 - pby0) * 0.6), 1)
    ncnt = max(1, int((fx - pbx0 - 4 * s) / aw))
    d.text("* " * ncnt, pbx0 + 3 * s, pby0 + 2 * s, (pby1 - pby0) * 0.6, BLK)
    d.line(fx, pby0, fx, pby1, BLK, 2.0 * s)
    d.text("SCAN %3.0f%%" % (fillv * 100), pbx0, pby1 + 0.006 * H, 9 * s, _a(BLK, 0.7))
    _dashes(d, X(0.185), y1 - 0.024 * H, X(0.520), _a(BLK, 0.6), dash=9 * s, gap=5 * s, w=2.0 * s)

    tb0, tby0, tb1, tby1 = X(0.560), y0 + 0.026 * H, X(0.700), y0 + 0.078 * H
    seven_seg_box(d, tb0, tby0, tb1, tby1, st.timecode, s)
    if st.alert:
        warning_triangle(d, tb1 + 0.020 * W, (tby0 + tby1) * 0.5, 14 * s, RED, 2.0 * s, fill=_a(RED, 0.15))
    else:
        warning_triangle(d, tb1 + 0.020 * W, (tby0 + tby1) * 0.5, 14 * s, BLK, 2.0 * s)

    crescent_globe(d, X(0.775), (y0 + y1) * 0.5, 0.030 * W, BLK, YEL, 1.8 * s)
    d.text("002_SYSTEM", X(0.815), y0 + 0.020 * H, 12 * s, BLK)
    d.text("CODE · 17-WW-22-000", x1 - 0.016 * W, y0 + 0.020 * H, 11 * s, BLK, align="right")
    eb0, eby0, eb1, eby1 = X(0.860), y1 - 0.044 * H, x1 - 0.016 * W, y1 - 0.010 * H
    epts = chamfer(eb0, eby0, eb1, eby1, tl=12, br=12)
    fillp(d, epts, CHAR if not st.alert else _a(RED, 0.6 + 0.4 * (0.5 + 0.5 * math.sin(t * 9))))
    d.poly(epts, BLK, 1.8 * s, closed=True)
    d.text("ERROR" if st.alert else "NOMINAL", (eb0 + eb1) * 0.5, eby0 + 0.006 * H,
           13 * s, YEL, align="center")


# ---------------------------------------------------------------- alert border
def _alert_border(d, W, H, s, X, Y, t):
    fl = 0.30 + 0.45 * (0.5 + 0.5 * math.sin(t * 9))
    m = 0.006 * W
    d.rect(X(0.0) + m, Y(0.0) + m, X(1.0) - m, Y(1.0) - m, _a(RED, fl), 2.5 * s)
    for (cx, cy) in ((X(0.03), Y(0.05)), (X(0.97), Y(0.05)), (X(0.03), Y(0.95)), (X(0.97), Y(0.95))):
        d.line(cx - 14 * s, cy, cx + 14 * s, cy, _a(RED, fl), 2.0 * s)
        d.line(cx, cy - 14 * s, cx, cy + 14 * s, _a(RED, fl), 2.0 * s)
