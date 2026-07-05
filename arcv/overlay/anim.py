"""Animation helpers for the overlay kit.

Two layers live here:

* The original Arwes-style helpers — :class:`Sequencer`, :func:`flicker`,
  arc-length stroke reveal (:func:`truncate_polyline`) and small easings. These
  keep their exact signatures so the warning/robot/cyberpunk demos keep working.

* A native port of the **anime.js v4 motion model** — :class:`Timer`,
  :class:`Animation` and :class:`Timeline`. Everything is *deterministic from a
  time value*: ``.at(t)`` is order-independent (no hidden mutable playhead), so
  scrubbing, stills and MP4 export all agree. Live playback is a thin wall-clock
  → ``t`` driver layered on top (see :class:`Player` in Phase 6).

The engine imports no GPU / numpy, so it can be used and unit-tested without a GL
context, exactly like the rest of this module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from .. import easing as _easing

Point = Tuple[float, float]
Number = Union[int, float]


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


# ===========================================================================
#  anime.js motion model — Timer / Animation / Timeline
#
#  Everything below is deterministic from ``t`` (seconds). No object mutates a
#  hidden playhead; ``.at(t)`` returns the same values regardless of call order.
# ===========================================================================

# -- colors ------------------------------------------------------------------
Color = Tuple[float, float, float, float]

_NAMED_COLORS = {
    "black": (0.0, 0.0, 0.0, 1.0), "white": (1.0, 1.0, 1.0, 1.0),
    "red": (1.0, 0.0, 0.0, 1.0), "green": (0.0, 1.0, 0.0, 1.0),
    "blue": (0.0, 0.0, 1.0, 1.0), "cyan": (0.0, 1.0, 1.0, 1.0),
    "magenta": (1.0, 0.0, 1.0, 1.0), "yellow": (1.0, 1.0, 0.0, 1.0),
    "transparent": (0.0, 0.0, 0.0, 0.0),
}


def is_color(v: Any) -> bool:
    """True if ``v`` looks like a color: a color string or an RGB(A) 3/4-tuple."""
    if isinstance(v, str):
        s = v.strip().lower()
        return s.startswith("#") or s.startswith("rgb") or s.startswith("hsl") or s in _NAMED_COLORS
    if isinstance(v, (tuple, list)) and len(v) in (3, 4):
        return all(isinstance(x, (int, float)) for x in v)
    return False


def _hue_to_rgb(p: float, q: float, t: float) -> float:
    if t < 0.0:
        t += 1.0
    if t > 1.0:
        t -= 1.0
    if t < 1.0 / 6.0:
        return p + (q - p) * 6.0 * t
    if t < 1.0 / 2.0:
        return q
    if t < 2.0 / 3.0:
        return p + (q - p) * (2.0 / 3.0 - t) * 6.0
    return p


def _hsl_to_rgb(h: float, s: float, l: float) -> Tuple[float, float, float]:
    if s == 0.0:
        return l, l, l
    q = l * (1.0 + s) if l < 0.5 else l + s - l * s
    p = 2.0 * l - q
    return _hue_to_rgb(p, q, h + 1.0 / 3.0), _hue_to_rgb(p, q, h), _hue_to_rgb(p, q, h - 1.0 / 3.0)


def parse_color(c: Any) -> Color:
    """Parse a color into an RGBA float tuple in ``[0, 1]``.

    Accepts ``#rgb`` / ``#rrggbb`` / ``#rrggbbaa`` hex, ``rgb()/rgba()``,
    ``hsl()/hsla()``, a handful of named colors, or an RGB(A) tuple/list (values
    ``>1`` are treated as the ``0..255`` scale). This is the "sane space" the
    Animation tweens colors in — plain RGBA, matching what ``ov.vector``/``ov.text``
    already consume.
    """
    if isinstance(c, (tuple, list)):
        vals = [float(x) for x in c]
        if len(vals) == 3:
            vals.append(1.0 if max(vals) <= 1.0 else 255.0)
        if max(vals[:3]) > 1.0:
            vals = [vals[0] / 255.0, vals[1] / 255.0, vals[2] / 255.0,
                    vals[3] / 255.0 if vals[3] > 1.0 else vals[3]]
        return (vals[0], vals[1], vals[2], vals[3])
    if isinstance(c, str):
        s = c.strip().lower()
        if s in _NAMED_COLORS:
            return _NAMED_COLORS[s]
        if s.startswith("#"):
            h = s[1:]
            if len(h) == 3:
                h = "".join(ch * 2 for ch in h)
            if len(h) == 6:
                h += "ff"
            if len(h) == 8:
                r = int(h[0:2], 16) / 255.0
                g = int(h[2:4], 16) / 255.0
                b = int(h[4:6], 16) / 255.0
                a = int(h[6:8], 16) / 255.0
                return (r, g, b, a)
        if s.startswith("rgb"):
            nums = _extract_numbers(s)
            if len(nums) >= 3:
                a = nums[3] if len(nums) > 3 else 1.0
                return (nums[0] / 255.0, nums[1] / 255.0, nums[2] / 255.0, a)
        if s.startswith("hsl"):
            nums = _extract_numbers(s)
            if len(nums) >= 3:
                h = (nums[0] % 360.0) / 360.0
                sat = nums[1] / 100.0
                lig = nums[2] / 100.0
                a = nums[3] if len(nums) > 3 else 1.0
                r, g, b = _hsl_to_rgb(h, sat, lig)
                return (r, g, b, a)
    raise ValueError(f"cannot parse color: {c!r}")


def _extract_numbers(s: str) -> List[float]:
    out: List[float] = []
    cur = ""
    for ch in s:
        if ch.isdigit() or ch in ".-+":
            cur += ch
        else:
            if cur:
                try:
                    out.append(float(cur))
                except ValueError:
                    pass
                cur = ""
    if cur:
        try:
            out.append(float(cur))
        except ValueError:
            pass
    return out


def lerp_color(a: Any, b: Any, u: float) -> Color:
    ca, cb = parse_color(a), parse_color(b)
    return (
        ca[0] + (cb[0] - ca[0]) * u,
        ca[1] + (cb[1] - ca[1]) * u,
        ca[2] + (cb[2] - ca[2]) * u,
        ca[3] + (cb[3] - ca[3]) * u,
    )


def interpolate(a: Any, b: Any, u: float) -> Any:
    """Interpolate between two values by ``u``.

    Handles numbers, colors (hex/rgb/hsl/tuple, lerped in RGBA), and short
    numeric tuples such as points ``(x, y)`` (element-wise). Non-interpolatable
    values switch at the midpoint.
    """
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a + (b - a) * u
    if is_color(a) and is_color(b):
        return lerp_color(a, b, u)
    if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)) and len(a) == len(b):
        return tuple(interpolate(x, y, u) for x, y in zip(a, b))
    return a if u < 0.5 else b


# -- Timer -------------------------------------------------------------------
@dataclass
class TimerState:
    """Pure snapshot of a :class:`Timer` at a given time — no easing applied."""
    began: bool
    completed: bool
    iteration: int
    progress: float          # linear [0,1] within the current iteration
    reversed_iteration: bool
    t: float


class Timer:
    """A bare deterministic clock — anime.js ``Timer``.

    Given an absolute time ``t`` (seconds), it reports which iteration is active
    and the linear progress within it, honouring ``delay``, ``end_delay``,
    ``loop`` (iteration count; ``True`` == infinite), ``alternate`` (yoyo) and
    ``reversed``. Value computation via :meth:`state_at` / :meth:`at` is pure;
    callbacks fire only through the forward-only :meth:`tick` driver.
    """

    def __init__(
        self,
        duration: float = 1.0,
        *,
        delay: float = 0.0,
        end_delay: float = 0.0,
        loop: Union[bool, int] = 1,
        alternate: bool = False,
        reversed: bool = False,
        on_begin: Optional[Callable[["Timer"], None]] = None,
        on_update: Optional[Callable[["Timer", float], None]] = None,
        on_complete: Optional[Callable[["Timer"], None]] = None,
        on_loop: Optional[Callable[["Timer", int], None]] = None,
    ) -> None:
        self.duration = max(0.0, float(duration))
        self.delay = float(delay)
        self.end_delay = max(0.0, float(end_delay))
        self.alternate = bool(alternate)
        self.reversed = bool(reversed)
        if loop is True:
            self.loops: float = math.inf
        elif loop is False:
            self.loops = 1
        else:
            self.loops = max(1, int(loop))
        self.on_begin = on_begin
        self.on_update = on_update
        self.on_complete = on_complete
        self.on_loop = on_loop
        # forward-play bookkeeping (callbacks only; never affects value output)
        self._t_prev = -math.inf
        self._began_fired = False
        self._completed_fired = False
        self._last_iteration = 0
        self.completed = False

    @property
    def iteration_length(self) -> float:
        return self.duration + self.end_delay

    @property
    def total_duration(self) -> float:
        if math.isinf(self.loops):
            return math.inf
        return self.delay + self.iteration_length * self.loops

    # -- pure sampling -----------------------------------------------------
    def state_at(self, t: float) -> TimerState:
        tl = t - self.delay
        if tl < 0.0:
            first_rev = self.reversed
            return TimerState(False, False, 0, 1.0 if first_rev else 0.0, first_rev, t)
        il = self.iteration_length
        if il <= 0.0:
            done = math.isinf(self.loops) is False
            return TimerState(True, done, 0, 1.0, self.reversed, t)
        i = int(tl // il)
        completed = False
        if not math.isinf(self.loops) and i >= self.loops:
            i = int(self.loops) - 1
            within = il
            completed = True
        else:
            within = tl - i * il
        raw = within / self.duration if self.duration > 0.0 else 1.0
        if raw > 1.0:
            raw = 1.0
        rev = self.reversed ^ (self.alternate and (i % 2 == 1))
        progress = (1.0 - raw) if rev else raw
        return TimerState(True, completed, i, progress, rev, t)

    def at(self, t: float) -> float:
        """Linear progress ``[0,1]`` of the active iteration (direction applied)."""
        return self.state_at(t).progress

    def is_complete(self, t: float) -> bool:
        return self.state_at(t).completed

    # -- forward-only callback driver -------------------------------------
    def tick(self, t: float) -> TimerState:
        """Sample at ``t`` and fire callbacks with once-semantics for forward play.

        Values still come from the pure :meth:`state_at`; this only decides when
        ``on_begin/on_update/on_complete/on_loop`` fire. Rewinding (``t`` going
        backwards) resets the latch so a re-played run fires again.
        """
        if t < self._t_prev:
            self._began_fired = False
            self._completed_fired = False
        st = self.state_at(t)
        if st.began and not self._began_fired:
            self._began_fired = True
            if self.on_begin:
                self.on_begin(self)
        if st.began and self.on_loop and st.iteration > self._last_iteration:
            for it in range(self._last_iteration + 1, st.iteration + 1):
                self.on_loop(self, it)
        self._last_iteration = st.iteration
        if st.began and self.on_update:
            self.on_update(self, st.progress)
        if st.completed and not self._completed_fired:
            self._completed_fired = True
            self.completed = True
            if self.on_complete:
                self.on_complete(self)
        if not st.completed:
            self.completed = False
        self._t_prev = t
        return st


# -- Tween (one animated property track) -------------------------------------
def _resolve_value(v: Any, index: int, total: int) -> Any:
    """Resolve function-based values ``lambda i, n: ...`` to a concrete value."""
    if callable(v) and not isinstance(v, str):
        try:
            return v(index, total)
        except TypeError:
            return v(index)
    return v


def _apply_relative(base: Any, expr: str) -> Any:
    op, num = expr[:2], float(expr[2:])
    if op == "+=":
        return base + num
    if op == "-=":
        return base - num
    if op == "*=":
        return base * num
    raise ValueError(f"bad relative value: {expr!r}")


def _is_relative(v: Any) -> bool:
    return isinstance(v, str) and v[:2] in ("+=", "-=", "*=")


@dataclass
class _Segment:
    dur: float
    frm: Any
    to: Any
    ease: Callable[[float], float]


class Tween:
    """One property's timeline: a delay, a chain of eased segments, plus its own
    loop/alternate/reversed/end_delay. Sampled purely from the global clock.
    """

    def __init__(
        self,
        name: str,
        segments: List[_Segment],
        *,
        delay: float = 0.0,
        end_delay: float = 0.0,
        loop: Union[bool, int] = 1,
        alternate: bool = False,
        reversed: bool = False,
    ) -> None:
        self.name = name
        self.segments = segments
        self.delay = float(delay)
        self.end_delay = max(0.0, float(end_delay))
        self.alternate = bool(alternate)
        self.reversed = bool(reversed)
        if loop is True:
            self.loops: float = math.inf
        elif loop is False:
            self.loops = 1
        else:
            self.loops = max(1, int(loop))
        self.content_duration = sum(s.dur for s in segments)

    @property
    def iteration_length(self) -> float:
        return self.content_duration + self.end_delay

    @property
    def duration(self) -> float:
        if math.isinf(self.loops):
            return math.inf
        return self.delay + self.iteration_length * self.loops

    def _sample_segments(self, local_time: float) -> Any:
        if not self.segments:
            return 0.0
        if local_time <= 0.0:
            s0 = self.segments[0]
            return interpolate(s0.frm, s0.to, s0.ease(0.0))
        acc = 0.0
        for seg in self.segments:
            if local_time <= acc + seg.dur:
                u = (local_time - acc) / seg.dur if seg.dur > 0.0 else 1.0
                return interpolate(seg.frm, seg.to, seg.ease(_clamp01_local(u)))
            acc += seg.dur
        last = self.segments[-1]
        return interpolate(last.frm, last.to, last.ease(1.0))

    def value_at(self, t: float) -> Any:
        tl = t - self.delay
        if tl <= 0.0:
            # hold the pre-start value (respecting a reversed first iteration)
            start_rev = self.reversed ^ (self.alternate and False)
            return self._sample_segments(self.content_duration if start_rev else 0.0)
        il = self.iteration_length
        if il <= 0.0:
            return self._sample_segments(self.content_duration)
        i = int(tl // il)
        if not math.isinf(self.loops) and i >= self.loops:
            i = int(self.loops) - 1
            within = il
        else:
            within = tl - i * il
        raw = within / self.content_duration if self.content_duration > 0.0 else 1.0
        if raw > 1.0:
            raw = 1.0
        rev = self.reversed ^ (self.alternate and (i % 2 == 1))
        local = (1.0 - raw) * self.content_duration if rev else raw * self.content_duration
        return self._sample_segments(local)


def _clamp01_local(t: float) -> float:
    return 0.0 if t < 0.0 else 1.0 if t > 1.0 else t


# -- Animation ---------------------------------------------------------------
class Animation:
    """Tween one or more named properties — anime.js ``animate()`` off the DOM.

    ``props`` maps a property name to its spec. A spec may be:

    * a scalar / color ``to`` value (``from`` defaults to ``base[name]`` or 0),
    * a ``(from, to)`` tuple,
    * a relative string ``"+=10"`` / ``"-=5"`` / ``"*=2"`` (resolved vs ``from``),
    * a function ``lambda i, n: value`` (per-target-index, anime.js style),
    * a dict ``{from, to, duration, ease, delay, endDelay, loop, alternate,
      reversed}`` — or ``{keyframes: [{to, duration, ease, delay}, ...]}``,
    * a keyframe list ``[{to, duration, ease, delay}, ...]``.

    ``.at(t) -> {name: value}`` is pure and order-independent.
    """

    def __init__(
        self,
        props: Dict[str, Any],
        *,
        duration: float = 1.0,
        delay: float = 0.0,
        end_delay: float = 0.0,
        ease: Any = "linear",
        loop: Union[bool, int] = 1,
        alternate: bool = False,
        reversed: bool = False,
        index: int = 0,
        total: int = 1,
        base: Optional[Dict[str, Any]] = None,
        on_begin: Optional[Callable] = None,
        on_update: Optional[Callable] = None,
        on_complete: Optional[Callable] = None,
        on_loop: Optional[Callable] = None,
    ) -> None:
        self.index = index
        self.total = total
        self.base = base or {}
        defaults = {
            "duration": float(duration),
            "delay": float(delay),
            "end_delay": float(end_delay),
            "ease": ease,
            "loop": loop,
            "alternate": alternate,
            "reversed": reversed,
        }
        self.tweens: Dict[str, Tween] = {}
        for name, spec in props.items():
            self.tweens[name] = self._build_tween(name, spec, defaults)
        self.duration = max((tw.duration for tw in self.tweens.values()), default=0.0)
        self._timer = Timer(
            self.duration if not math.isinf(self.duration) else 1.0,
            loop=loop, alternate=alternate, reversed=reversed,
            on_begin=on_begin, on_update=on_update,
            on_complete=on_complete, on_loop=on_loop,
        )

    # -- build -------------------------------------------------------------
    def _build_tween(self, name: str, spec: Any, defaults: Dict[str, Any]) -> Tween:
        p = dict(defaults)
        keyframes: Optional[List[dict]] = None
        frm_spec: Any = _MISSING
        to_spec: Any = _MISSING

        if isinstance(spec, dict):
            if "keyframes" in spec:
                keyframes = spec["keyframes"]
            for k_alias, k in (("from", "frm"), ("frm", "frm"), ("to", "to"),
                               ("duration", "duration"), ("dur", "duration"),
                               ("ease", "ease"), ("easing", "ease"),
                               ("delay", "delay"), ("endDelay", "end_delay"),
                               ("end_delay", "end_delay"), ("loop", "loop"),
                               ("alternate", "alternate"), ("reversed", "reversed"),
                               ("direction", "_direction")):
                if k_alias in spec:
                    if k == "frm":
                        frm_spec = spec[k_alias]
                    elif k == "to":
                        to_spec = spec[k_alias]
                    else:
                        p[k] = spec[k_alias]
            if p.get("_direction") == "reverse":
                p["reversed"] = True
        elif isinstance(spec, (list, tuple)):
            if spec and all(isinstance(x, dict) for x in spec):
                keyframes = list(spec)
            elif len(spec) == 2 and not is_color(spec):
                frm_spec, to_spec = spec[0], spec[1]
            else:
                to_spec = spec  # e.g. a single color/point value
        else:
            to_spec = spec

        base_val = self.base.get(name, 0.0)
        segments: List[_Segment] = []

        if keyframes is not None:
            running = _resolve_value(frm_spec, self.index, self.total) if frm_spec is not _MISSING else base_val
            n = len(keyframes)
            share = p["duration"] / n if p["duration"] else 0.0
            for kf in keyframes:
                to_v = _resolve_value(kf.get("to", kf.get("value")), self.index, self.total)
                if _is_relative(to_v):
                    to_v = _apply_relative(running if isinstance(running, (int, float)) else 0.0, to_v)
                dur = float(kf.get("duration", kf.get("dur", share)))
                kf_delay = float(kf.get("delay", 0.0))
                ez = _easing.get(kf.get("ease", kf.get("easing", p["ease"])))
                if kf_delay > 0.0:
                    segments.append(_Segment(kf_delay, running, running, _easing.linear))
                segments.append(_Segment(max(0.0, dur), running, to_v, ez))
                running = to_v
        else:
            frm_val = (_resolve_value(frm_spec, self.index, self.total)
                       if frm_spec is not _MISSING else base_val)
            to_val = _resolve_value(to_spec, self.index, self.total) if to_spec is not _MISSING else frm_val
            if _is_relative(to_val):
                to_val = _apply_relative(frm_val if isinstance(frm_val, (int, float)) else 0.0, to_val)
            if _is_relative(frm_val):
                frm_val = _apply_relative(base_val if isinstance(base_val, (int, float)) else 0.0, frm_val)
            ez = _easing.get(p["ease"])
            segments.append(_Segment(max(0.0, float(p["duration"])), frm_val, to_val, ez))

        return Tween(
            name, segments,
            delay=p["delay"], end_delay=p["end_delay"],
            loop=p["loop"], alternate=p["alternate"], reversed=p["reversed"],
        )

    # -- sampling ----------------------------------------------------------
    def at(self, t: float) -> Dict[str, Any]:
        return {name: tw.value_at(t) for name, tw in self.tweens.items()}

    def value_at(self, t: float, name: str) -> Any:
        return self.tweens[name].value_at(t)

    def tick(self, t: float) -> TimerState:
        return self._timer.tick(t)

    @property
    def completed(self) -> bool:
        return self._timer.completed


_MISSING = object()


# -- Timeline ----------------------------------------------------------------
@dataclass
class _Child:
    id: str
    anim: Animation
    start: float

    @property
    def end(self) -> float:
        d = self.anim.duration
        return self.start + (0.0 if math.isinf(d) else d)


class Timeline:
    """Compose animations on one shared, deterministic clock — anime.js ``Timeline``.

    ``add(props, params, position)`` appends a child :class:`Animation`. ``position``
    accepts an absolute time, a relative offset (``"+=0.1"`` / ``"-=0.2"`` vs the
    timeline end), ``"<"`` / ``">"`` (previous child's start / end), or a label name
    (optionally ``"label+=0.1"``). ``tl.at(t)`` returns ``{child_id: {prop: value}}``.
    """

    def __init__(
        self,
        *,
        loop: Union[bool, int] = 1,
        alternate: bool = False,
        reversed: bool = False,
        autoplay: bool = True,
        defaults: Optional[Dict[str, Any]] = None,
        on_begin: Optional[Callable] = None,
        on_update: Optional[Callable] = None,
        on_complete: Optional[Callable] = None,
        on_loop: Optional[Callable] = None,
    ) -> None:
        self.children: List[_Child] = []
        self.labels: Dict[str, float] = {}
        self.defaults = defaults or {}
        self.autoplay = autoplay
        self._loop = loop
        self._alternate = alternate
        self._reversed = reversed
        self._duration = 0.0
        self._last_start = 0.0
        self._last_end = 0.0
        self._auto = 0
        self._cb = dict(on_begin=on_begin, on_update=on_update,
                        on_complete=on_complete, on_loop=on_loop)
        self._timer: Optional[Timer] = None

    # -- construction ------------------------------------------------------
    def label(self, name: str, time: Optional[float] = None) -> "Timeline":
        self.labels[name] = self._duration if time is None else float(time)
        return self

    def _resolve_position(self, position: Any) -> float:
        if position is None:
            return self._duration
        if isinstance(position, (int, float)):
            return float(position)
        if isinstance(position, str):
            s = position.strip()
            # label with optional offset, e.g. "boot+=0.2"
            for op in ("+=", "-=", "*="):
                if op in s:
                    head, _, num = s.partition(op)
                    head = head.strip()
                    val = float(num)
                    if head == "" or head == "<" or head == ">":
                        anchor = (self._last_start if head == "<"
                                  else self._last_end if head == ">"
                                  else self._duration)
                    elif head in self.labels:
                        anchor = self.labels[head]
                    else:
                        anchor = self._duration
                    if op == "+=":
                        return anchor + val
                    if op == "-=":
                        return anchor - val
                    return anchor * val
            if s == "<":
                return self._last_start
            if s == ">":
                return self._last_end
            if s in self.labels:
                return self.labels[s]
        return self._duration

    def add(self, props: Dict[str, Any], params: Optional[Dict[str, Any]] = None,
            position: Any = None) -> "Timeline":
        params = dict(params or {})
        merged = dict(self.defaults)
        merged.update(params)
        cid = merged.pop("id", None)
        # accept a position passed inside params as well
        if position is None and "position" in merged:
            position = merged.pop("position")
        else:
            merged.pop("position", None)
        start = self._resolve_position(position)
        if cid is None:
            cid = f"a{self._auto}"
            self._auto += 1
        anim = Animation(props, **merged)
        child = _Child(cid, anim, start)
        self.children.append(child)
        self._last_start = start
        self._last_end = child.end
        self._duration = max(self._duration, child.end)
        self._timer = None  # invalidate cached clock
        return self

    # -- clock -------------------------------------------------------------
    @property
    def duration(self) -> float:
        return self._duration

    def _clock(self) -> Timer:
        if self._timer is None:
            self._timer = Timer(
                self._duration if self._duration > 0 else 1.0,
                loop=self._loop, alternate=self._alternate, reversed=self._reversed,
                **self._cb,
            )
        return self._timer

    def _local_time(self, t: float) -> float:
        clk = self._clock()
        st = clk.state_at(t)
        return st.progress * (self._duration if self._duration > 0 else 0.0)

    # -- sampling ----------------------------------------------------------
    def at(self, t: float) -> Dict[str, Dict[str, Any]]:
        lt = self._local_time(t)
        out: Dict[str, Dict[str, Any]] = {}
        for c in self.children:
            out[c.id] = c.anim.at(lt - c.start)
        return out

    def values_at(self, t: float) -> Dict[str, Any]:
        """Flat ``{prop: value}`` merge across children (last write wins on clashes)."""
        flat: Dict[str, Any] = {}
        for vals in self.at(t).values():
            flat.update(vals)
        return flat

    def child_at(self, t: float, cid: str) -> Dict[str, Any]:
        lt = self._local_time(t)
        for c in self.children:
            if c.id == cid:
                return c.anim.at(lt - c.start)
        raise KeyError(cid)

    def tick(self, t: float) -> TimerState:
        return self._clock().tick(t)

    @property
    def completed(self) -> bool:
        clk = self._clock()
        return clk.completed

    # -- stagger helper ----------------------------------------------------
    def stagger(self, count: int, props: Dict[str, Any],
                params: Optional[Dict[str, Any]] = None, position: Any = None) -> "Timeline":
        """Add ``count`` staggered children in one call — anime.js ``tl`` + ``stagger()``.

        Any :class:`Stagger` value in ``params`` (typically ``delay``) or the
        ``position`` argument is resolved per index; ``props`` values that are
        Stagger/functions are resolved by each child :class:`Animation` via its
        ``index``/``total``. Every child gets ``index=k, total=count`` so
        function-based values line up.
        """
        params = dict(params or {})
        for k in range(count):
            resolved = {
                key: (val(k, count) if isinstance(val, Stagger) else val)
                for key, val in params.items()
            }
            resolved["index"] = k
            resolved["total"] = count
            pos = position(k, count) if isinstance(position, Stagger) else position
            self.add(props, resolved, pos)
        return self


# -- Stagger -----------------------------------------------------------------
class Stagger:
    """anime.js ``stagger()`` — per-index (and per-grid-cell) values.

    Distances to an origin are measured in index units (1D) or grid-cell units
    (2D), optionally constrained to one axis and re-shaped by an easing across
    the distribution. A :class:`Stagger` is itself callable as ``(index, total)``
    so it drops straight into an :class:`Animation` function-value or a
    :meth:`Timeline.stagger` parameter (typically ``delay``).

    Parameters
    ----------
    value:
        The base spacing (scalar) — each step is ``value`` further out — or a
        ``(start, end)`` range to distribute values across.
    from_:
        Origin the distance is measured from: ``"first"``, ``"last"``,
        ``"center"``, an integer index, or an ``(x, y)`` grid cell.
    start:
        Constant offset added to every produced value.
    grid:
        ``(cols, rows)`` to lay indices out in 2D; distance becomes Euclidean.
    axis:
        ``"x"`` or ``"y"`` to constrain a grid distance to one axis.
    range:
        Explicit ``(lo, hi)`` spread (overrides scalar spacing).
    ease:
        Easing applied to the normalized distance before scaling (name or fn).
    reversed:
        Reverse the produced ordering (mirror the origin).
    """

    def __init__(
        self,
        value: Any = 0.0,
        *,
        from_: Any = "first",
        start: float = 0.0,
        grid: Optional[Tuple[int, int]] = None,
        axis: Optional[str] = None,
        range: Optional[Tuple[float, float]] = None,  # noqa: A002 - anime.js name
        ease: Any = None,
        reversed: bool = False,
    ) -> None:
        self.value = value
        self.from_ = from_
        self.start = float(start)
        self.grid = grid
        self.axis = axis
        self.reversed = bool(reversed)
        self.ease = _easing.get(ease) if ease is not None else None
        # effective range: explicit range param, or value if it's a 2-tuple
        if range is not None:
            self._range: Optional[Tuple[float, float]] = (float(range[0]), float(range[1]))
        elif isinstance(value, (tuple, list)) and len(value) == 2:
            self._range = (float(value[0]), float(value[1]))
        else:
            self._range = None
        self._spacing = 0.0 if self._range is not None else float(value)
        self._cache: Dict[int, List[float]] = {}

    # -- geometry ----------------------------------------------------------
    def _origin_1d(self, total: int) -> float:
        f = self.from_
        if f == "first":
            return 0.0
        if f == "last":
            return float(total - 1)
        if f == "center":
            return (total - 1) / 2.0
        if isinstance(f, (int, float)):
            return float(f)
        return 0.0

    def _origin_grid(self, cols: int, rows: int) -> Tuple[float, float]:
        f = self.from_
        if f == "first":
            return 0.0, 0.0
        if f == "last":
            return float(cols - 1), float(rows - 1)
        if f == "center":
            return (cols - 1) / 2.0, (rows - 1) / 2.0
        if isinstance(f, (tuple, list)) and len(f) == 2:
            return float(f[0]), float(f[1])
        if isinstance(f, (int, float)):
            i = int(f)
            return float(i % cols), float(i // cols)
        return 0.0, 0.0

    def _distances(self, total: int) -> List[float]:
        if self.grid is not None:
            cols, rows = int(self.grid[0]), int(self.grid[1])
            ox, oy = self._origin_grid(cols, rows)
            out = []
            for i in range(total):
                col, row = float(i % cols), float(i // cols)
                if self.axis == "x":
                    out.append(abs(col - ox))
                elif self.axis == "y":
                    out.append(abs(row - oy))
                else:
                    out.append(math.hypot(col - ox, row - oy))
            return out
        origin = self._origin_1d(total)
        return [abs(i - origin) for i in range(total)]

    # -- values ------------------------------------------------------------
    def values(self, total: int) -> List[float]:
        if total <= 0:
            return []
        if total in self._cache:
            return self._cache[total]
        dist = self._distances(total)
        maxd = max(dist) if dist else 0.0
        out: List[float] = []
        for d in dist:
            n = d / maxd if maxd > 0.0 else 0.0
            e = self.ease(n) if self.ease is not None else n
            if self._range is not None:
                lo, hi = self._range
                v = self.start + lo + (hi - lo) * e
            else:
                v = self.start + e * maxd * self._spacing
            out.append(v)
        if self.reversed:
            out = list(reversed(out))
        self._cache[total] = out
        return out

    def __call__(self, index: int, total: int = 1) -> float:
        vals = self.values(total)
        if not vals:
            return self.start
        return vals[index % len(vals)]


def stagger(value: Any = 0.0, **params: Any) -> Stagger:
    """Return a :class:`Stagger` (callable ``(index, total) -> value``).

    Example::

        tl.stagger(9, {"scale": (0.0, 1.0)},
                   {"duration": 0.4, "delay": stagger(0.05, grid=(3, 3), from_="center")})
    """
    return Stagger(value, **params)
