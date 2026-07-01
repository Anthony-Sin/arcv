"""Autonomous quadruped "follow the human" HUD overlay (ARCV only).

Uses exactly the telemetry provided, laid out for the use case and inspired by
the reference HUDs. Scripted over time to show the loading/boot, the LOCKED
follow state, a TARGET LOST alert with a searching effect, and REACQUIRE.

`build(d, W, H, t)` draws it through an ArcvAdapter. No real tracking — the
target position and states are simulated from `t` so the effects are visible.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

from arcv.overlay.anim import Sequencer, flicker, linear, out_cubic

# palette (cold robot/tactical cyan + red alert + amber caution + green ok)
CYAN = (0.35, 0.92, 1.0, 1.0)
CYAN_DIM = (0.55, 0.88, 1.0, 0.9)
CYAN_FAINT = (0.45, 0.82, 0.98, 0.5)
WHITE = (0.90, 0.98, 1.0, 1.0)
RED = (1.0, 0.28, 0.30, 1.0)
RED_DIM = (1.0, 0.32, 0.34, 0.55)
AMBER = (1.0, 0.72, 0.20, 1.0)
GREEN = (0.42, 1.0, 0.60, 1.0)
PANEL_FILL = (0.30, 0.72, 0.92, 0.05)

HEX = "A4 F2 08 3E 0A 71 86 16 10 17 48 D1 82 21 79 91"

# timeline (seconds)
T_BOOT = 2.2
T_LOST = 6.0
T_REACQ = 9.4


@dataclass
class RobotState:
    phase: str          # boot | locked | lost | reacquire
    locked: bool
    alert: bool
    target: Tuple[float, float]     # UV center of the tracked person (screen)
    box: Tuple[float, float]        # half-size UV of the bounding box
    dist: Optional[float]
    bearing: Optional[float]
    cmd: Tuple[float, float]
    gait: float                     # gait phase
    radar_sweep: float
    blip: Optional[Tuple[float, float]]  # (bearing_deg, dist_m)
    timecode: str
    rec_s: int
    frm: int


def _fade(c, a):
    return (c[0], c[1], c[2], c[3] * a)


def state_at(t: float) -> RobotState:
    lost = T_LOST <= t < T_REACQ
    reacq = T_REACQ <= t < (T_REACQ + 0.6)
    phase = "boot" if t < T_BOOT else ("lost" if lost else ("reacquire" if reacq else "locked"))
    locked = not lost

    # base timecode 13:50:41 + elapsed
    base = 13 * 3600 + 50 * 60 + 41 + int(t)
    tc = "%02d:%02d:%02d" % (base // 3600 % 24, base // 60 % 60, base % 60)

    if lost:
        # searching scan pattern (expanding lissajous) while target is lost
        sx = 0.5 + 0.16 * math.sin(t * 2.3)
        sy = 0.5 + 0.11 * math.cos(t * 1.7)
        target = (sx, sy)
        box = (0.10 + 0.03 * math.sin(t * 6.0), 0.15 + 0.03 * math.sin(t * 6.0))
        dist = bearing = None
        blip = None
        sweep = t * 3.2  # faster sweep while searching
    else:
        drift = 0.0 if t < T_BOOT else 1.0
        target = (0.5 + 0.03 * math.sin(t * 0.7) * drift, 0.5 + 0.02 * math.cos(t * 0.9) * drift)
        box = (0.085, 0.16)
        dist = 0.98 + 0.02 * math.sin(t * 3.1)
        bearing = 40.0 + 1.5 * math.sin(t * 1.3)
        blip = (bearing, dist)
        sweep = t * 1.4

    return RobotState(
        phase=phase, locked=locked, alert=lost,
        target=target, box=box, dist=dist, bearing=bearing,
        cmd=(50.00 + 0.4 * math.sin(t * 4.0), 40.10 + 0.3 * math.cos(t * 3.3)),
        gait=t * 2.4, radar_sweep=sweep, blip=blip,
        timecode=tc, rec_s=11 + int(t), frm=51 + int(t * 30),
    )


def build(d, W, H, t=0.0):
    s = H / 600.0
    q = Sequencer(t)
    st = state_at(t)
    accent = RED if st.alert else CYAN

    def X(f):
        return f * W

    def Y(f):
        return f * H

    _topbar(d, W, H, s, X, Y, t, q, st)
    _left_system(d, W, H, s, X, Y, t, q, st)
    _center_track(d, W, H, s, X, Y, t, q, st, accent)
    _right_panels(d, W, H, s, X, Y, t, q, st)
    _locomotion(d, W, H, s, X, Y, t, q, st)
    _actions(d, W, H, s, X, Y, t, q, st)
    _radar(d, W, H, s, X, Y, t, q, st, accent)
    _datastream(d, W, H, s, X, Y, t, q, st)
    if st.alert:
        _alert_border(d, W, H, s, X, Y, t)


# ---------------------------------------------------------------- top bar
def _topbar(d, W, H, s, X, Y, t, q, st):
    p = q.at(0.0, 0.4, linear)
    d.line(X(0.02), Y(0.055), X(0.98), Y(0.055), CYAN_FAINT, 1.0 * s, reveal=p)
    # logo mark
    if q.at(0.0, 0.3) > 0:
        d.rect(X(0.022), Y(0.020), X(0.052), Y(0.050), CYAN, 1.6 * s, reveal=p)
        d.line(X(0.027), Y(0.025), X(0.037), Y(0.045), CYAN, 1.6 * s, reveal=p)
        d.line(X(0.037), Y(0.045), X(0.047), Y(0.025), CYAN, 1.6 * s, reveal=p)
    if q.at(0.1, 0.6) > 0:
        d.text("G02-0001  OPTICAL FEED // SINGLE", X(0.060), Y(0.024), 12 * s, WHITE,
               mode="decipher", t=t, progress=q.at(0.1, 0.6))
        d.text("G02 OPTICAL FEED  ·  SYSTEM  ·  LINK OK", X(0.060), Y(0.040), 10 * s, CYAN_DIM)
    # right: REC + frame counters
    if q.at(0.15, 0.5) > 0:
        blink = (t % 1.0) < 0.5
        d.disc(X(0.815), Y(0.032), 4 * s, RED if blink else RED_DIM)
        d.text("REC %04ds" % st.rec_s, X(0.830), Y(0.024), 13 * s, WHITE)
        d.text("FRM %05d  ·  %s" % (st.frm, st.timecode), X(0.830), Y(0.040), 10 * s, CYAN_DIM)
        d.text("LINK OK", X(0.945), Y(0.024), 10 * s, GREEN)


# ------------------------------------------------------------- left column
def _left_system(d, W, H, s, X, Y, t, q, st):
    x = X(0.024)
    rows = [
        ("SYSTEM", "LINK OK", GREEN),
        ("SESSION", "9B7/192D41-Am", WHITE),
        ("GAIN", "+2/+1", CYAN_DIM),
        ("BASELINE", "0.26 m", WHITE),
        ("EXPOSURE", "1BF8GHT", CYAN_DIM),
    ]
    for i, (k, v, col) in enumerate(rows):
        p = q.stagger(i, 0.3, 0.07, 0.4)
        if p <= 0:
            continue
        y = Y(0.11) + i * 0.038 * H
        d.text(k, x, y, 10 * s, CYAN_DIM)
        d.text(v, x, y + 0.015 * H, 12 * s, col, mode="typeon", progress=p)

    # depth/thermal scan box
    p = q.at(0.7, 0.5)
    if p > 0:
        bx0, by0, bx1, by1 = X(0.024), Y(0.30), X(0.175), Y(0.52)
        d.rrect_fill(bx0, by0, bx1, by1, 6 * s, _fade(PANEL_FILL, p))
        d.rect(bx0, by0, bx1, by1, CYAN, 1.4 * s, reveal=q.at(0.7, 0.5, linear))
        # corner ticks
        for cxx in (bx0, bx1):
            d.line(cxx, by0, cxx, by0 + 0.02 * H, CYAN, 2.0 * s, reveal=p)
        d.text("DEPTH · SCAN", bx0 + 0.008 * W, by0 + 0.010 * H, 10 * s, CYAN_DIM)
        # animated depth bands
        for k in range(6):
            yy = by0 + 0.05 * H + k * 0.026 * H
            w = (0.5 + 0.5 * math.sin(t * 2.0 + k)) * (bx1 - bx0 - 0.02 * W)
            d.line(bx0 + 0.01 * W, yy, bx0 + 0.01 * W + w, yy, _fade(CYAN, 0.5), 2.0 * s, reveal=p)
        d.text("INPUT DATA", bx0 + 0.008 * W, by1 - 0.022 * H, 10 * s, CYAN_DIM)

    # left connector ticks (like ref)
    for i, lbl in enumerate(("552-96", "354-56")):
        yy = Y(0.20) + i * 0.14 * H
        if q.at(0.5, 0.4) > 0:
            d.text(lbl, X(0.024), yy, 10 * s, CYAN_FAINT)
            d.line(X(0.06), yy + 0.004 * H, X(0.22), yy + 0.02 * H, CYAN_FAINT, 1.0 * s, reveal=q.at(0.6, 0.5, linear))


# ------------------------------------------------------------ center track
def _center_track(d, W, H, s, X, Y, t, q, st, accent):
    # large central camera-feed region (this is where the tracked person shows)
    fx0, fy0, fx1, fy1 = X(0.232), Y(0.105), X(0.668), Y(0.725)
    cl = 0.026 * W
    lw = 2.0 * s

    # scan frame corners
    corners = [(fx0, 1, fy0, 1), (fx1, -1, fy0, 1), (fx0, 1, fy1, -1), (fx1, -1, fy1, -1)]
    for i, (ox, sx, oy, sy) in enumerate(corners):
        pc = q.stagger(i, 0.2, 0.05, 0.4, linear)
        d.poly([(ox, oy + sy * cl), (ox, oy), (ox + sx * cl, oy)], CYAN, lw, reveal=pc)
    d.rect(fx0, fy0, fx1, fy1, CYAN_FAINT, 1.0 * s, reveal=q.at(0.4, 0.4, linear))

    # banner
    if q.at(0.3, 0.4) > 0:
        if st.alert:
            fl = 1.0 if (t % 0.5) < 0.3 else 0.25
            d.text("! TARGET LOST // REACQUIRING", (fx0 + fx1) * 0.5, fy0 - 0.028 * H,
                   11 * s, _fade(RED, fl), align="center")
        else:
            d.text("• TARGET LOCKED  ·  PERSON / %.2fm" % (st.dist or 0),
                   (fx0 + fx1) * 0.5, fy0 - 0.028 * H, 10 * s, GREEN, align="center",
                   mode="decipher", t=t, progress=q.at(0.3, 0.5))

    # tracked target box + reticle
    tx = fx0 + (fx1 - fx0) * st.target[0]
    ty = fy0 + (fy1 - fy0) * st.target[1]
    bw = st.box[0] * (fx1 - fx0)
    bh = st.box[1] * (fy1 - fy0)
    pr = q.at(0.6, 0.4)
    if pr > 0:
        _target_box(d, tx, ty, bw, bh, accent, s, t, st, H, reveal=pr)
        # DIST / BEARING readouts
        if st.dist is not None:
            d.text("DIST", tx + bw + 0.008 * W, ty - bh, 10 * s, CYAN_DIM)
            d.text("%.2f m" % st.dist, tx + bw + 0.008 * W, ty - bh + 0.013 * H, 12 * s, WHITE)
            d.text("BEARING", tx + bw + 0.008 * W, ty - bh + 0.035 * H, 10 * s, CYAN_DIM)
            d.text("%.1f°" % st.bearing, tx + bw + 0.008 * W, ty - bh + 0.048 * H, 12 * s, WHITE)
            d.text("3%", tx - bw, ty + bh + 0.012 * H, 10 * s, CYAN_DIM)
        else:
            d.text("DIST --.- m", tx + bw + 0.008 * W, ty - bh, 10 * s, RED_DIM)
            d.text("BEARING --.-°", tx + bw + 0.008 * W, ty - bh + 0.02 * H, 10 * s, RED_DIM)

    # inner feed frame ticks along top/bottom edges (subtle instrumentation)
    if q.at(0.5, 0.5) > 0:
        pv = q.at(0.5, 0.5, linear)
        for k in range(1, 8):
            fxk = fx0 + (fx1 - fx0) * (k / 8.0)
            d.line(fxk, fy1, fxk, fy1 - 0.012 * H, CYAN_FAINT, 1.0 * s, reveal=pv)
            d.line(fxk, fy0, fxk, fy0 + 0.010 * H, CYAN_FAINT, 1.0 * s, reveal=pv)

    # vertical side label
    if q.at(0.55, 0.5) > 0:
        for i, ch in enumerate("OPTICAL LOCK"):
            if ch == " ":
                continue
            d.text(ch, fx0 - 0.018 * W, fy0 + 0.05 * H + i * 0.030 * H, 11 * s, CYAN_FAINT)


def _target_box(d, tx, ty, bw, bh, accent, s, t, st, H, reveal=1.0):
    lw = 1.8 * s
    # animated corner brackets on the person
    a = 0.4 * min(bw, bh) if not st.alert else (0.4 + 0.15 * math.sin(t * 8)) * min(bw, bh)
    for (sx, sy) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        cx0 = tx + sx * bw
        cy0 = ty + sy * bh
        d.poly([(cx0 - sx * a, cy0), (cx0, cy0), (cx0, cy0 - sy * a)], accent, lw, reveal=reveal)
    if st.locked:
        # crosshair + inner ring locked on
        r = min(bw, bh) * 0.45
        d.ring(tx, ty, r, accent, 1.4 * s, reveal=reveal)
        g = r * 0.4
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            d.line(tx + dx * g, ty + dy * g, tx + dx * r * 1.6, ty + dy * r * 1.6, accent, 1.3 * s, reveal=reveal)
        for k in range(6):
            ang = t * 0.8 + k * math.pi / 3
            d.line(tx + math.cos(ang) * r * 1.15, ty + math.sin(ang) * r * 1.15,
                   tx + math.cos(ang) * r * 1.3, ty + math.sin(ang) * r * 1.3, _fade(accent, 0.7), 1.0 * s)
        d.text("PERSON #01  ! LOCKED", tx - bw, ty - bh - 0.018 * H, 11 * s, accent)
    else:
        # searching sweep line inside the box
        d.text("SEARCHING...", tx - bw, ty - bh - 0.018 * H, 11 * s, _fade(RED, 0.6 + 0.4 * math.sin(t * 10)))
        sweep_y = ty - bh + (2 * bh) * ((t * 0.8) % 1.0)
        d.line(tx - bw, sweep_y, tx + bw, sweep_y, _fade(RED, 0.7), 1.4 * s)


# ------------------------------------------------------------ right panels
def _right_panels(d, W, H, s, X, Y, t, q, st):
    x0, x1 = X(0.715), X(0.945)   # narrower — was much too wide

    # TRACK panel
    p = q.at(0.5, 0.5)
    if p > 0:
        py0, py1 = Y(0.105), Y(0.435)
        d.rrect_fill(x0, py0, x1, py1, 6 * s, _fade(PANEL_FILL, p))
        d.rrect(x0, py0, x1, py1, 6 * s, CYAN, 1.5 * s, reveal=q.at(0.5, 0.5, linear))
        ix = x0 + 0.014 * W
        d.text("T TAG · TRACK", ix, py0 + 0.016 * H, 11 * s, CYAN_DIM)
        rows = [
            ("ENTITY", "PERSON #01", WHITE),
            ("TRACK STATE", "! LOCKED" if st.locked else "! LOST", GREEN if st.locked else RED),
            ("CLASS", "DYNAMIC ENTITY · PATIENT", WHITE),
            ("BUILD ARCH", "TALL / FEM", CYAN_DIM),
            ("TASK", "FOLLOW + ASSIST UP STAIRS", WHITE),
        ]
        for i, (k, v, col) in enumerate(rows):
            pi = q.stagger(i, 0.7, 0.06, 0.35)
            if pi <= 0:
                continue
            yy = py0 + 0.050 * H + i * 0.050 * H
            d.text(k, ix, yy, 11 * s, CYAN_DIM)
            d.text(v, ix, yy + 0.019 * H, 13 * s, col, mode="typeon", progress=pi)

    # FUSION panel
    p = q.at(0.9, 0.5)
    if p > 0:
        py0, py1 = Y(0.455), Y(0.640)
        d.rrect_fill(x0, py0, x1, py1, 6 * s, _fade(PANEL_FILL, p))
        d.rrect(x0, py0, x1, py1, 6 * s, CYAN, 1.5 * s, reveal=q.at(0.9, 0.5, linear))
        ix = x0 + 0.014 * W
        d.text("SENSOR FUSION", ix, py0 + 0.016 * H, 11 * s, CYAN_DIM)
        for i, (name, val, ok) in enumerate((("CAM", 0.92, True), ("LIDAR", 0.78, True), ("IMU", 0.85, True))):
            pi = q.stagger(i, 1.0, 0.06, 0.3)
            yy = py0 + 0.050 * H + i * 0.034 * H
            d.text(name, ix, yy, 13 * s, WHITE)
            bx0 = ix + 0.055 * W
            bx1 = x1 - 0.016 * W
            d.line(bx0, yy + 0.009 * H, bx1, yy + 0.009 * H, CYAN_FAINT, 3.0 * s)
            d.line(bx0, yy + 0.009 * H, bx0 + (bx1 - bx0) * val * pi, yy + 0.009 * H, GREEN, 3.0 * s)
        fl = 1.0 if (t % 0.7) < 0.4 else 0.4
        d.text("! DEPTH DISAGREE", ix, py1 - 0.028 * H, 13 * s, _fade(AMBER, fl))

    # CMD V/V
    p = q.at(1.1, 0.4)
    if p > 0:
        yy = Y(0.665)
        d.text("CMD  V / V", x0, yy, 10 * s, CYAN_DIM)
        d.text("%.2f / %.2f" % st.cmd, x0 + 0.075 * W, yy, 15 * s, WHITE)


# ------------------------------------------------------------- locomotion
def _locomotion(d, W, H, s, X, Y, t, q, st):
    p = q.at(1.0, 0.5)
    if p <= 0:
        return
    x0, y0, x1, y1 = X(0.245), Y(0.78), X(0.545), Y(0.955)
    d.rrect(x0, y0, x1, y1, 6 * s, CYAN, 1.4 * s, reveal=q.at(1.0, 0.5, linear))
    ix = x0 + 0.012 * W
    d.text("LOCOMOTION · pgtt_go2_lev · 1ED0", ix, y0 + 0.012 * H, 10 * s, CYAN_DIM)
    for i, (k, v) in enumerate((("MODE", "FLAT FOLLOW"), ("GAIT", "DIAGONAL F"), ("STEP", "0.06 m / 0.06"), ("SLIP", "OFF"))):
        yy = y0 + 0.040 * H + i * 0.024 * H
        d.text(k, ix, yy, 10 * s, CYAN_DIM)
        d.text(v, ix + 0.06 * W, yy, 11 * s, WHITE, mode="typeon", progress=q.stagger(i, 1.1, 0.05, 0.3))

    # quadruped gait diagram (top-down): body + 4 legs stance/swing
    gx, gy = X(0.485), Y(0.87)
    bw, bh = 0.022 * W, 0.045 * H
    d.rrect(gx - bw, gy - bh, gx + bw, gy + bh, 4 * s, CYAN_DIM, 1.2 * s)
    legs = [(-1, -1, "FL"), (1, -1, "FR"), (-1, 1, "RL"), (1, 1, "RR")]
    for i, (sx, sy, name) in enumerate(legs):
        # trot: diagonal pairs (FL+RR) vs (FR+RL) alternate
        pair = 0 if (sx * sy < 0) else 1
        stance = math.sin(st.gait + pair * math.pi) > 0
        lx = gx + sx * (bw + 0.012 * W)
        ly = gy + sy * (bh * 0.6)
        if stance:
            d.disc(lx, ly, 4 * s, GREEN)
        else:
            d.ring(lx, ly, 4 * s, AMBER, 1.4 * s)
        d.text(name, lx - 6 * s, ly + 0.02 * H, 6 * s, CYAN_FAINT)
    d.text("STANCE", gx - bw - 0.03 * W, gy - bh, 6 * s, GREEN)
    d.text("SWING", gx + bw + 0.005 * W, gy - bh, 6 * s, AMBER)


# ---------------------------------------------------------------- actions
def _actions(d, W, H, s, X, Y, t, q, st):
    labels = [("REASSURED", GREEN), ("CAUTION", AMBER), ("PAUSE", CYAN), ("QUIT", RED)]
    x = X(0.560)
    for i, (lbl, col) in enumerate(labels):
        p = q.stagger(i, 1.2, 0.08, 0.3)
        if p <= 0:
            continue
        y = Y(0.80) + i * 0.036 * H
        # CAUTION active (amber pulse) while alert
        active = st.alert and lbl == "CAUTION"
        c = _fade(col, 1.0 if not active else (0.6 + 0.4 * abs(math.sin(t * 6))))
        r = 0.007 * W
        d.ring(x, y + 0.006 * H, r, c, 1.5 * s, reveal=p)
        if p >= 1.0:
            d.disc(x, y + 0.006 * H, r * 0.4, c) if active else None
        d.text(lbl, x + r + 0.01 * W, y, 13 * s, c if active else WHITE, mode="typeon", progress=p)


# ------------------------------------------------------------------ radar
def _radar(d, W, H, s, X, Y, t, q, st, accent):
    p = q.at(1.3, 0.5)
    if p <= 0:
        return
    cx, cy, r = X(0.85), Y(0.865), 0.06 * W
    d.text("XT16 RADAR · FWD 1", cx - r, cy - r - 0.03 * H, 10 * s, CYAN_DIM)
    d.ring(cx, cy, r, CYAN, 1.4 * s, reveal=q.at(1.3, 0.5, linear))
    d.ring(cx, cy, r * 0.66, CYAN_FAINT, 1.0 * s, reveal=p)
    d.ring(cx, cy, r * 0.33, CYAN_FAINT, 1.0 * s, reveal=p)
    d.line(cx - r, cy, cx + r, cy, CYAN_FAINT, 1.0 * s, reveal=p)
    d.line(cx, cy - r, cx, cy + r, CYAN_FAINT, 1.0 * s, reveal=p)
    # sweep line + fading trail
    for k in range(6):
        a = st.radar_sweep - k * 0.12
        d.line(cx, cy, cx + math.cos(a) * r, cy + math.sin(a) * r,
               _fade(accent, 0.5 * (1 - k / 6.0)), 1.6 * s)
    # blip
    if st.blip is not None:
        ba = math.radians(st.blip[0] - 90.0)
        br = r * min(st.blip[1] / 3.0, 0.95)
        bx, by = cx + math.cos(ba) * br, cy + math.sin(ba) * br
        pulse = 2.0 * s + 1.5 * s * (0.5 + 0.5 * math.sin(t * 6))
        d.disc(bx, by, pulse, GREEN)
        d.ring(bx, by, pulse + 3 * s, _fade(GREEN, 0.5), 1.0 * s)


# ------------------------------------------------------------- data stream
def _datastream(d, W, H, s, X, Y, t, q, st):
    p = q.at(1.4, 0.5)
    if p <= 0:
        return
    y = Y(0.975)
    d.line(X(0.02), y - 0.012 * H, X(0.98), y - 0.012 * H, CYAN_FAINT, 1.0 * s, reveal=q.at(1.4, 0.5, linear))
    # scrolling/flickering hex
    off = int(t * 6) % 3
    txt = (HEX + "   ") * 2
    d.text(txt[off:off + 70], X(0.02), y, 10 * s, CYAN_FAINT)
    d.text("744-NRC-445 REV A1  ·  DATA STREAM  ·  744-NRY-284 REV A3",
           X(0.98), y, 10 * s, CYAN_FAINT, align="right")


# ------------------------------------------------------------- alert border
def _alert_border(d, W, H, s, X, Y, t):
    fl = 0.3 + 0.4 * (0.5 + 0.5 * math.sin(t * 9))
    m = 0.008 * W
    d.rect(X(0.0) + m, Y(0.0) + m, X(1.0) - m, Y(1.0) - m, _fade(RED, fl), 2.5 * s)
