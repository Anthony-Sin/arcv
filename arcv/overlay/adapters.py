"""Phase 7 — ARCV-native equivalents of anime.js's browser-only features.

anime.js ships several helpers that only make sense against a live DOM: they read
the scroll position, hit-test pointer events on elements, and re-scope animations
to CSS media queries. ARCV has no DOM — you own the GL context and the main loop —
so each is re-expressed as a small, pure adapter driven by a value *you* already
have (a detection count, optical-flow magnitude, a scrub knob, the mouse position
from :meth:`arcv.scene.Scene.set_mouse`, the live resolution).

Mapping
-------
======================  ==================================================
anime.js (DOM)          ARCV-native adapter
======================  ==================================================
``onScroll`` /          :class:`DriverFromSignal` — map any external scalar
``ScrollObserver``      onto a target's model time (enter/leave -> lo/hi).
``createDraggable``     :class:`Draggable` — drag a value from pointer state
                        you feed it; bounds / axis / snap, optional inertia.
``createScope`` +       :class:`Scope` — scale a design authored at a
responsive ``media``    reference resolution to the live one; named
                        breakpoints stand in for CSS media queries.
======================  ==================================================

Everything here is pure Python (no GPU import) and — apart from the deliberately
stateful live drivers (smoothing / inertia, exactly like :class:`Player`'s
wall-clock) — deterministic from its input, so stills and export stay exact.

Genuinely not applicable (DOM-only, listed rather than faked): see
:data:`NOT_APPLICABLE`.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

from .. import easing as _easing
from .anim import clamp01


NOT_APPLICABLE = (
    "getComputedStyle / reading CSS values off elements (no DOM/CSS engine)",
    "WAAPI (Web Animations API) hand-off — ARCV renders every frame itself",
    "DOM hit-testing for pointer targets (feed pointer state to Draggable instead)",
    "scroll-linked pinning to a real scrollbar (drive DriverFromSignal from any scalar)",
    "SVG getTotalLength()/getPointAtLength() — anim.sample_path computes arc length natively",
    "CSS 3D matrix/perspective transforms (2D marker rotation/scale is provided)",
)


class DriverFromSignal:
    """Map an external scalar onto a target's model time — ScrollObserver analog.

    anime.js ties an animation's progress to scroll position between ``enter`` and
    ``leave`` thresholds. Here ``lo``/``hi`` bound whatever scalar you have
    (detection count, ``Scene`` flow magnitude, a slider); the normalized position
    is optionally eased and exponentially smoothed, then mapped to the target's
    ``[0, duration]`` and sampled. Signals may move both ways, so callbacks fire
    through the target's forward :meth:`tick` (which self-resets on rewind).

    If ``target`` is ``None`` the driver simply returns the normalized/eased
    progress, handy for feeding a lone ``reveal``/``progress`` value.
    """

    def __init__(self, target: Any = None, lo: float = 0.0, hi: float = 1.0, *,
                 ease: Any = None, smoothing: float = 0.0, clamp: bool = True) -> None:
        self.target = target
        self.lo = float(lo)
        self.hi = float(hi)
        self.ease = _easing.get(ease) if ease is not None else None
        self.smoothing = clamp01(smoothing)
        self.clamp = clamp
        self._smoothed: Optional[float] = None

    @property
    def duration(self) -> float:
        return float(getattr(self.target, "duration", 1.0) or 1.0)

    def progress(self, signal: float) -> float:
        span = self.hi - self.lo
        n = (signal - self.lo) / span if abs(span) > 1e-12 else 0.0
        if self.clamp:
            n = clamp01(n)
        if self.smoothing > 0.0:
            if self._smoothed is None:
                self._smoothed = n
            else:
                self._smoothed += (n - self._smoothed) * (1.0 - self.smoothing)
            n = self._smoothed
        return self.ease(n) if self.ease is not None else n

    def time(self, signal: float) -> float:
        return self.progress(signal) * self.duration

    def sample(self, signal: float):
        p = self.progress(signal)
        if self.target is None:
            return p
        t = p * self.duration
        tk = getattr(self.target, "tick", None)
        if callable(tk):
            tk(t)
        return self.target.at(t)


class Draggable:
    """Drag a value with the pointer — anime.js ``createDraggable`` analog.

    No pointer runtime is assumed: feed pointer pixels (from
    :meth:`arcv.scene.Scene.set_mouse` or any source) to :meth:`grab` /
    :meth:`move` / :meth:`release`. Tracks an ``(x, y)`` value with optional
    ``bounds`` ``(minx, miny, maxx, maxy)``, an ``axis`` constraint, ``snap`` grid,
    and post-release inertia decayed by :meth:`update`. Read :attr:`value` for the
    draw call.
    """

    def __init__(self, value: Tuple[float, float] = (0.0, 0.0), *,
                 bounds: Optional[Tuple[float, float, float, float]] = None,
                 axis: Optional[str] = None,
                 snap: Optional[Tuple[float, float]] = None,
                 friction: float = 0.85) -> None:
        self.x, self.y = float(value[0]), float(value[1])
        self.bounds = bounds
        self.axis = axis
        self.snap = snap
        self.friction = clamp01(friction)
        self.dragging = False
        self._px = 0.0
        self._py = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.on_grab = None
        self.on_drag = None
        self.on_release = None

    @property
    def value(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def _apply_constraints(self) -> None:
        if self.axis == "x":
            pass  # y frozen elsewhere
        if self.snap is not None:
            sx, sy = self.snap
            if sx > 0:
                self.x = round(self.x / sx) * sx
            if sy > 0:
                self.y = round(self.y / sy) * sy
        if self.bounds is not None:
            minx, miny, maxx, maxy = self.bounds
            self.x = min(max(self.x, minx), maxx)
            self.y = min(max(self.y, miny), maxy)

    def grab(self, px: float, py: float) -> None:
        self.dragging = True
        self._px, self._py = float(px), float(py)
        self.vx = self.vy = 0.0
        if self.on_grab:
            self.on_grab(self)

    def move(self, px: float, py: float) -> Tuple[float, float]:
        if not self.dragging:
            return self.value
        dx, dy = px - self._px, py - self._py
        self._px, self._py = float(px), float(py)
        if self.axis != "y":
            self.x += dx
            self.vx = dx
        if self.axis != "x":
            self.y += dy
            self.vy = dy
        self._apply_constraints()
        if self.on_drag:
            self.on_drag(self)
        return self.value

    def release(self) -> None:
        self.dragging = False
        if self.on_release:
            self.on_release(self)

    def update(self, dt: float = 1.0) -> Tuple[float, float]:
        """Advance inertia after release; call each frame while not dragging."""
        if self.dragging:
            return self.value
        if abs(self.vx) < 1e-3 and abs(self.vy) < 1e-3:
            self.vx = self.vy = 0.0
            return self.value
        self.x += self.vx
        self.y += self.vy
        self.vx *= self.friction
        self.vy *= self.friction
        self._apply_constraints()
        return self.value


class Scope:
    """Resolution-aware layout — anime.js ``createScope`` + responsive analog.

    Author a HUD against a reference ``design`` resolution, then let Scope scale
    positions/sizes to the live resolution and report a named breakpoint (standing
    in for CSS media queries). ``x``/``y`` scale per-axis; ``px`` scales a size by
    the uniform (min-axis) factor so circles stay circular.
    """

    DEFAULT_BREAKPOINTS = (("sm", 0), ("md", 768), ("lg", 1280), ("xl", 1920))

    def __init__(self, size: Tuple[int, int], design: Tuple[int, int] = (1280, 720),
                 breakpoints=None) -> None:
        self.design = (float(design[0]), float(design[1]))
        self.breakpoints = tuple(breakpoints) if breakpoints else self.DEFAULT_BREAKPOINTS
        self.resize(size[0], size[1])

    def resize(self, w: int, h: int) -> "Scope":
        self.size = (float(w), float(h))
        self.sx = self.size[0] / self.design[0]
        self.sy = self.size[1] / self.design[1]
        self.scale = min(self.sx, self.sy)
        return self

    def x(self, v: float) -> float:
        return v * self.sx

    def y(self, v: float) -> float:
        return v * self.sy

    def pos(self, x: float, y: float) -> Tuple[float, float]:
        return (x * self.sx, y * self.sy)

    def px(self, v: float) -> float:
        return v * self.scale

    @property
    def breakpoint(self) -> str:
        name = self.breakpoints[0][0]
        for bp_name, bp_min in self.breakpoints:
            if self.size[0] >= bp_min:
                name = bp_name
        return name

    def matches(self, name: str) -> bool:
        return self.breakpoint == name
