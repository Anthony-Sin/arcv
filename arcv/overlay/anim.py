"""Animation helpers for the overlay kit: easings, a small sequencer for
staggered enter/loading orchestration, arc-length stroke reveal, and flicker.

These mirror the Arwes motion model (staggered enter, frame draw-on, flicker-in)
for hand-laid-out HUDs.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

Point = Tuple[float, float]


# -- easings -----------------------------------------------------------------
def clamp01(t: float) -> float:
    return 0.0 if t < 0.0 else 1.0 if t > 1.0 else t


def linear(t: float) -> float:
    return clamp01(t)


def out_cubic(t: float) -> float:
    t = clamp01(t)
    f = t - 1.0
    return f * f * f + 1.0


def in_out_cubic(t: float) -> float:
    t = clamp01(t)
    if t < 0.5:
        return 4.0 * t * t * t
    f = 2.0 * t - 2.0
    return 0.5 * f * f * f + 1.0


def out_back(t: float) -> float:
    t = clamp01(t)
    c1, c3 = 1.70158, 2.70158
    f = t - 1.0
    return 1.0 + c3 * f * f * f + c1 * f * f


# -- sequencer ---------------------------------------------------------------
class Sequencer:
    """Maps the current time to per-element progress with delays/durations, so a
    whole HUD can assemble with staggered timing (Arwes-style)."""

    def __init__(self, time: float) -> None:
        self.time = time

    def at(self, delay: float, duration: float, ease=out_cubic) -> float:
        if duration <= 0.0:
            return 1.0 if self.time >= delay else 0.0
        return ease(clamp01((self.time - delay) / duration))

    def stagger(self, index: int, delay: float, step: float, duration: float, ease=out_cubic) -> float:
        return self.at(delay + index * step, duration, ease)


def flicker(progress: float, time: float, seed: float = 0.0) -> float:
    """Flicker-in alpha multiplier: blinks while entering, steady once entered."""
    if progress <= 0.0:
        return 0.0
    if progress >= 1.0:
        return 1.0
    phase = (time * 17.0 + seed * 3.7) % 1.0
    # more "off" time early in the transition
    if phase < 0.42 * (1.0 - progress):
        return 0.0
    return progress


# -- geometry ----------------------------------------------------------------
def arc_points(cx, cy, r, a0, a1, segments=48) -> List[Point]:
    pts = []
    for i in range(segments + 1):
        t = a0 + (a1 - a0) * i / segments
        pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return pts


def rrect_points(x0, y0, x1, y1, rad, seg=6) -> List[Point]:
    rad = min(rad, (x1 - x0) * 0.5, (y1 - y0) * 0.5)
    pts: List[Point] = []
    corners = [
        (x0 + rad, y0 + rad, math.pi, math.pi * 1.5),
        (x1 - rad, y0 + rad, math.pi * 1.5, math.pi * 2.0),
        (x1 - rad, y1 - rad, 0.0, math.pi * 0.5),
        (x0 + rad, y1 - rad, math.pi * 0.5, math.pi),
    ]
    for (cx, cy, a0, a1) in corners:
        for i in range(seg + 1):
            t = a0 + (a1 - a0) * i / seg
            pts.append((cx + rad * math.cos(t), cy + rad * math.sin(t)))
    return pts


def polyline_length(pts: Sequence[Point]) -> float:
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
               for i in range(len(pts) - 1))


def truncate_polyline(pts: Sequence[Point], reveal: float, closed: bool = False) -> List[Point]:
    """Return the polyline drawn up to `reveal` (0..1) of its total arc length."""
    pp = list(pts)
    if closed and len(pp) > 1:
        pp = pp + [pp[0]]
    if reveal >= 1.0:
        return pp
    if reveal <= 0.0 or len(pp) < 2:
        return []
    total = polyline_length(pp)
    if total <= 1e-6:
        return pp[:1]
    target = reveal * total
    out: List[Point] = [pp[0]]
    acc = 0.0
    for i in range(len(pp) - 1):
        L = math.hypot(pp[i + 1][0] - pp[i][0], pp[i + 1][1] - pp[i][1])
        if acc + L <= target:
            out.append(pp[i + 1])
            acc += L
        else:
            u = (target - acc) / L if L > 1e-6 else 0.0
            out.append((pp[i][0] + (pp[i + 1][0] - pp[i][0]) * u,
                        pp[i][1] + (pp[i + 1][1] - pp[i][1]) * u))
            break
    return out
