"""Easing functions — a full port of the anime.js v4 easing set.

Every function takes a normalized time ``t`` in ``[0, 1]`` and returns an eased
value. Non-overshooting eases stay in ``[0, 1]``; ``back``/``elastic``/``bounce``
may overshoot *between* the endpoints but always satisfy ``f(0) == 0`` and
``f(1) == 1``.

The original ARCV names (``linear``, ``in_out_cubic``, ``in_out_quad``,
``out_cubic``, ``steps``) and the string :data:`REGISTRY` / :func:`get` lookup are
preserved, so existing components keep working. On top of that this module now
provides the whole anime.js family:

* in/out/inOut of ``quad, cubic, quart, quint, sine, expo, circ, back, elastic,
  bounce`` (snake_case functions + camelCase registry names),
* :func:`cubic_bezier` (CSS-style, Newton + bisection solve),
* :func:`spring` (numerically integrated, cached curve, natural duration),
* parameterized :func:`back` (overshoot) and :func:`elastic` (amplitude, period),
* :func:`steps` (unchanged).

Pure Python, no GPU / numpy dependency — importable without a GL context.
"""

from __future__ import annotations

import math
from typing import Callable, List, Tuple

Ease = Callable[[float], float]

_TAU = math.pi * 2.0


def _clamp01(t: float) -> float:
    if t < 0.0:
        return 0.0
    if t > 1.0:
        return 1.0
    return t


# -- linear ------------------------------------------------------------------
def linear(t: float) -> float:
    return _clamp01(t)


# -- power family (quad=2, cubic=3, quart=4, quint=5) -------------------------
def _in_pow(t: float, p: float) -> float:
    t = _clamp01(t)
    return t ** p


def _out_pow(t: float, p: float) -> float:
    t = _clamp01(t)
    return 1.0 - (1.0 - t) ** p


def _in_out_pow(t: float, p: float) -> float:
    t = _clamp01(t)
    if t < 0.5:
        return (2.0 ** (p - 1.0)) * (t ** p)
    return 1.0 - ((-2.0 * t + 2.0) ** p) / 2.0


def in_quad(t: float) -> float:
    return _in_pow(t, 2.0)


def out_quad(t: float) -> float:
    return _out_pow(t, 2.0)


def in_out_quad(t: float) -> float:
    return _in_out_pow(t, 2.0)


def in_cubic(t: float) -> float:
    return _in_pow(t, 3.0)


def out_cubic(t: float) -> float:
    return _out_pow(t, 3.0)


def in_out_cubic(t: float) -> float:
    return _in_out_pow(t, 3.0)


def in_quart(t: float) -> float:
    return _in_pow(t, 4.0)


def out_quart(t: float) -> float:
    return _out_pow(t, 4.0)


def in_out_quart(t: float) -> float:
    return _in_out_pow(t, 4.0)


def in_quint(t: float) -> float:
    return _in_pow(t, 5.0)


def out_quint(t: float) -> float:
    return _out_pow(t, 5.0)


def in_out_quint(t: float) -> float:
    return _in_out_pow(t, 5.0)


# -- sine --------------------------------------------------------------------
def in_sine(t: float) -> float:
    t = _clamp01(t)
    return 1.0 - math.cos((t * math.pi) / 2.0)


def out_sine(t: float) -> float:
    t = _clamp01(t)
    return math.sin((t * math.pi) / 2.0)


def in_out_sine(t: float) -> float:
    t = _clamp01(t)
    return -(math.cos(math.pi * t) - 1.0) / 2.0


# -- expo --------------------------------------------------------------------
def in_expo(t: float) -> float:
    t = _clamp01(t)
    if t <= 0.0:
        return 0.0
    return 2.0 ** (10.0 * t - 10.0)


def out_expo(t: float) -> float:
    t = _clamp01(t)
    if t >= 1.0:
        return 1.0
    return 1.0 - 2.0 ** (-10.0 * t)


def in_out_expo(t: float) -> float:
    t = _clamp01(t)
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    if t < 0.5:
        return (2.0 ** (20.0 * t - 10.0)) / 2.0
    return (2.0 - 2.0 ** (-20.0 * t + 10.0)) / 2.0


# -- circ --------------------------------------------------------------------
def in_circ(t: float) -> float:
    t = _clamp01(t)
    return 1.0 - math.sqrt(max(0.0, 1.0 - t * t))


def out_circ(t: float) -> float:
    t = _clamp01(t)
    return math.sqrt(max(0.0, 1.0 - (t - 1.0) ** 2))


def in_out_circ(t: float) -> float:
    t = _clamp01(t)
    if t < 0.5:
        return (1.0 - math.sqrt(max(0.0, 1.0 - (2.0 * t) ** 2))) / 2.0
    return (math.sqrt(max(0.0, 1.0 - (-2.0 * t + 2.0) ** 2)) + 1.0) / 2.0


# -- back (overshoot) --------------------------------------------------------
_BACK_S = 1.70158


def _in_back(t: float, s: float = _BACK_S) -> float:
    t = _clamp01(t)
    c3 = s + 1.0
    return c3 * t * t * t - s * t * t


def _out_back(t: float, s: float = _BACK_S) -> float:
    t = _clamp01(t)
    c3 = s + 1.0
    f = t - 1.0
    return 1.0 + c3 * f * f * f + s * f * f


def _in_out_back(t: float, s: float = _BACK_S) -> float:
    t = _clamp01(t)
    c2 = s * 1.525
    if t < 0.5:
        return ((2.0 * t) ** 2 * ((c2 + 1.0) * 2.0 * t - c2)) / 2.0
    return ((2.0 * t - 2.0) ** 2 * ((c2 + 1.0) * (2.0 * t - 2.0) + c2) + 2.0) / 2.0


def in_back(t: float) -> float:
    return _in_back(t)


def out_back(t: float) -> float:
    return _out_back(t)


def in_out_back(t: float) -> float:
    return _in_out_back(t)


def back(overshoot: float = _BACK_S, mode: str = "out") -> Ease:
    """Parameterized back easing factory. ``mode`` in ``{in, out, inOut}``."""
    if mode == "in":
        return lambda t: _in_back(t, overshoot)
    if mode in ("inOut", "in_out", "inout"):
        return lambda t: _in_out_back(t, overshoot)
    return lambda t: _out_back(t, overshoot)


# -- elastic (amplitude, period) ---------------------------------------------
_ELASTIC_A = 1.0
_ELASTIC_P = 0.3


def _elastic_shift(amplitude: float, period: float) -> Tuple[float, float]:
    a = amplitude
    if a < 1.0:
        a = 1.0
        s = period / 4.0
    else:
        s = period / _TAU * math.asin(1.0 / a)
    return a, s


def _out_elastic(t: float, amplitude: float = _ELASTIC_A, period: float = _ELASTIC_P) -> float:
    t = _clamp01(t)
    if t <= 0.0 or t >= 1.0:
        return t
    a, s = _elastic_shift(amplitude, period)
    return a * 2.0 ** (-10.0 * t) * math.sin((t - s) * _TAU / period) + 1.0


def _in_elastic(t: float, amplitude: float = _ELASTIC_A, period: float = _ELASTIC_P) -> float:
    t = _clamp01(t)
    if t <= 0.0 or t >= 1.0:
        return t
    return 1.0 - _out_elastic(1.0 - t, amplitude, period)


def _in_out_elastic(t: float, amplitude: float = _ELASTIC_A, period: float = _ELASTIC_P) -> float:
    t = _clamp01(t)
    if t <= 0.0 or t >= 1.0:
        return t
    if t < 0.5:
        return _in_elastic(2.0 * t, amplitude, period) / 2.0
    return _out_elastic(2.0 * t - 1.0, amplitude, period) / 2.0 + 0.5


def in_elastic(t: float) -> float:
    return _in_elastic(t)


def out_elastic(t: float) -> float:
    return _out_elastic(t)


def in_out_elastic(t: float) -> float:
    return _in_out_elastic(t)


def elastic(amplitude: float = _ELASTIC_A, period: float = _ELASTIC_P, mode: str = "out") -> Ease:
    """Parameterized elastic easing factory. ``mode`` in ``{in, out, inOut}``."""
    if mode == "in":
        return lambda t: _in_elastic(t, amplitude, period)
    if mode in ("inOut", "in_out", "inout"):
        return lambda t: _in_out_elastic(t, amplitude, period)
    return lambda t: _out_elastic(t, amplitude, period)


# -- bounce ------------------------------------------------------------------
def out_bounce(t: float) -> float:
    t = _clamp01(t)
    n1, d1 = 7.5625, 2.75
    if t < 1.0 / d1:
        return n1 * t * t
    if t < 2.0 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    t -= 2.625 / d1
    return n1 * t * t + 0.984375


def in_bounce(t: float) -> float:
    return 1.0 - out_bounce(1.0 - _clamp01(t))


def in_out_bounce(t: float) -> float:
    t = _clamp01(t)
    if t < 0.5:
        return (1.0 - out_bounce(1.0 - 2.0 * t)) / 2.0
    return (1.0 + out_bounce(2.0 * t - 1.0)) / 2.0


# -- steps -------------------------------------------------------------------
def steps(n: int, jump_end: bool = True) -> Ease:
    """Return a stepped easing function (like CSS ``steps(n, end)``).

    Used for the blinking text cursor (``steps(2, end)``).
    """

    def _step(t: float) -> float:
        t = _clamp01(t)
        if jump_end:
            return min(int(t * n) / n, 1.0)
        return min((int(t * n) + 1) / n, 1.0)

    return _step


# -- cubic bezier (CSS cubic-bezier) -----------------------------------------
def cubic_bezier(x1: float, y1: float, x2: float, y2: float) -> Ease:
    """Return the CSS ``cubic-bezier(x1, y1, x2, y2)`` easing.

    Control points are ``(0,0)``, ``(x1,y1)``, ``(x2,y2)``, ``(1,1)``. ``x`` is
    solved for the given progress via Newton-Raphson with a bisection fallback,
    then ``y`` is evaluated on that parameter.
    """

    def _coeff(a1: float, a2: float) -> Tuple[float, float, float]:
        c = 3.0 * a1
        b = 3.0 * (a2 - a1) - c
        a = 1.0 - c - b
        return a, b, c

    ax, bx, cx = _coeff(x1, x2)
    ay, by, cy = _coeff(y1, y2)

    def _bezier(t: float, a: float, b: float, c: float) -> float:
        return ((a * t + b) * t + c) * t

    def _slope(t: float, a: float, b: float, c: float) -> float:
        return (3.0 * a * t + 2.0 * b) * t + c

    def _solve_x(x: float) -> float:
        if x <= 0.0:
            return 0.0
        if x >= 1.0:
            return 1.0
        lo, hi = 0.0, 1.0
        t = x
        for _ in range(24):
            xt = _bezier(t, ax, bx, cx)
            err = xt - x
            if abs(err) < 1e-7:
                return t
            if err > 0.0:
                hi = t
            else:
                lo = t
            s = _slope(t, ax, bx, cx)
            if abs(s) > 1e-7:
                tn = t - err / s
                if lo < tn < hi:
                    t = tn
                    continue
            t = 0.5 * (lo + hi)
        return t

    def _ease(t: float) -> float:
        t = _clamp01(t)
        if x1 == y1 and x2 == y2:
            return t  # identity / linear control points
        return _bezier(_solve_x(t), ay, by, cy)

    return _ease


# -- spring ------------------------------------------------------------------
class Spring:
    """A normalized spring easing (anime.js ``createSpring``).

    A damped harmonic oscillator is integrated from ``0`` toward ``1`` with the
    given physical parameters. The trajectory is sampled once and cached; calling
    the instance maps normalized progress ``u in [0, 1]`` onto that curve. The
    natural settle time is exposed as :attr:`duration` (seconds) so a Timeline can
    pick a real duration from the physics instead of a hand-tuned number.
    """

    def __init__(
        self,
        mass: float = 1.0,
        stiffness: float = 100.0,
        damping: float = 10.0,
        velocity: float = 0.0,
        rest_threshold: float = 5e-4,
    ) -> None:
        self.mass = max(1e-4, float(mass))
        self.stiffness = max(1e-4, float(stiffness))
        self.damping = max(0.0, float(damping))
        self.velocity = float(velocity)
        self.rest_threshold = float(rest_threshold)
        self._dt = 1.0 / 1000.0
        self._p: List[float] = [0.0]
        self.duration = 0.0
        self._solve()

    def _solve(self) -> None:
        dt = self._dt
        p = 0.0
        v = self.velocity
        traj: List[float] = [0.0]
        t = 0.0
        max_t = 30.0
        settle_needed = int(0.05 / dt)  # sustained rest before we call it done
        settle_count = 0
        rest = self.rest_threshold
        while t < max_t:
            a = (-self.stiffness * (p - 1.0) - self.damping * v) / self.mass
            v += a * dt
            p += v * dt
            t += dt
            traj.append(p)
            if abs(p - 1.0) < rest and abs(v) < rest:
                settle_count += 1
                if settle_count >= settle_needed:
                    break
            else:
                settle_count = 0
        self.duration = max(t, dt)
        self._p = traj

    def __call__(self, u: float) -> float:
        u = _clamp01(u)
        if u <= 0.0:
            return 0.0
        if u >= 1.0:
            return 1.0
        time = u * self.duration
        fidx = time / self._dt
        i = int(fidx)
        if i >= len(self._p) - 1:
            return 1.0
        frac = fidx - i
        return self._p[i] * (1.0 - frac) + self._p[i + 1] * frac


def spring(
    mass: float = 1.0,
    stiffness: float = 100.0,
    damping: float = 10.0,
    velocity: float = 0.0,
) -> Spring:
    """Return a :class:`Spring` easing (callable ``0..1 -> 0..1`` with ``.duration``)."""
    return Spring(mass, stiffness, damping, velocity)


# -- registry ----------------------------------------------------------------
# Name -> function registry so themes / components / timelines can refer to
# easings by string. Original camelCase names are kept; the full anime.js family
# is added alongside snake_case aliases.
REGISTRY = {
    "linear": linear,
    "inQuad": in_quad, "outQuad": out_quad, "inOutQuad": in_out_quad,
    "inCubic": in_cubic, "outCubic": out_cubic, "inOutCubic": in_out_cubic,
    "inQuart": in_quart, "outQuart": out_quart, "inOutQuart": in_out_quart,
    "inQuint": in_quint, "outQuint": out_quint, "inOutQuint": in_out_quint,
    "inSine": in_sine, "outSine": out_sine, "inOutSine": in_out_sine,
    "inExpo": in_expo, "outExpo": out_expo, "inOutExpo": in_out_expo,
    "inCirc": in_circ, "outCirc": out_circ, "inOutCirc": in_out_circ,
    "inBack": in_back, "outBack": out_back, "inOutBack": in_out_back,
    "inElastic": in_elastic, "outElastic": out_elastic, "inOutElastic": in_out_elastic,
    "inBounce": in_bounce, "outBounce": out_bounce, "inOutBounce": in_out_bounce,
}

# snake_case aliases also resolvable by string
REGISTRY.update({
    "in_quad": in_quad, "out_quad": out_quad, "in_out_quad": in_out_quad,
    "in_cubic": in_cubic, "out_cubic": out_cubic, "in_out_cubic": in_out_cubic,
    "in_quart": in_quart, "out_quart": out_quart, "in_out_quart": in_out_quart,
    "in_quint": in_quint, "out_quint": out_quint, "in_out_quint": in_out_quint,
    "in_sine": in_sine, "out_sine": out_sine, "in_out_sine": in_out_sine,
    "in_expo": in_expo, "out_expo": out_expo, "in_out_expo": in_out_expo,
    "in_circ": in_circ, "out_circ": out_circ, "in_out_circ": in_out_circ,
    "in_back": in_back, "out_back": out_back, "in_out_back": in_out_back,
    "in_elastic": in_elastic, "out_elastic": out_elastic, "in_out_elastic": in_out_elastic,
    "in_bounce": in_bounce, "out_bounce": out_bounce, "in_out_bounce": in_out_bounce,
})


def _parse_args(s: str) -> List[float]:
    s = s.strip()
    if not s:
        return []
    return [float(x) for x in s.split(",") if x.strip() != ""]


def get(name):
    """Resolve an easing by string, function, or ``"name(args)"`` factory call.

    Accepts an easing function directly (returned unchanged), a registry name,
    or a parameterized anime.js-style call such as ``"spring(1,80,12)"``,
    ``"cubicBezier(.25,.1,.25,1)"``, ``"steps(4)"``, ``"outBack(2)"`` or
    ``"outElastic(1.2,.4)"``. Falls back to :func:`linear`.
    """
    if callable(name):
        return name
    if not isinstance(name, str):
        return linear
    key = name.strip()
    if key in REGISTRY:
        return REGISTRY[key]
    if "(" in key and key.endswith(")"):
        head, _, rest = key.partition("(")
        head = head.strip()
        args = _parse_args(rest[:-1])
        try:
            return _factory(head, args)
        except (ValueError, TypeError, IndexError):
            return linear
    return linear


def _factory(head: str, args: List[float]) -> Ease:
    low = head.lower()
    if low in ("steps", "step"):
        n = int(args[0]) if args else 1
        jump_end = bool(args[1]) if len(args) > 1 else True
        return steps(n, jump_end)
    if low in ("cubicbezier", "cubic-bezier", "cubic_bezier", "bezier"):
        return cubic_bezier(args[0], args[1], args[2], args[3])
    if low == "spring":
        return spring(*args) if args else spring()
    if low in ("back", "outback", "out_back"):
        return back(args[0] if args else _BACK_S, mode="out")
    if low in ("inback", "in_back"):
        return back(args[0] if args else _BACK_S, mode="in")
    if low in ("inoutback", "in_out_back"):
        return back(args[0] if args else _BACK_S, mode="inOut")
    if low in ("elastic", "outelastic", "out_elastic"):
        return elastic(*(args or []), mode="out")
    if low in ("inelastic", "in_elastic"):
        return elastic(*(args or []), mode="in")
    if low in ("inoutelastic", "in_out_elastic"):
        return elastic(*(args or []), mode="inOut")
    raise ValueError(f"unknown easing factory: {head}")
