"""Easing functions used by the Animator.

All functions take a normalized time ``t`` in ``[0, 1]`` and return an eased
value in ``[0, 1]``. They mirror the defaults Arwes uses: ``linear`` for text
transitions and ``inOutCubic`` for canvas backgrounds.
"""

from __future__ import annotations


def linear(t: float) -> float:
    return _clamp01(t)


def in_out_cubic(t: float) -> float:
    t = _clamp01(t)
    if t < 0.5:
        return 4.0 * t * t * t
    f = 2.0 * t - 2.0
    return 0.5 * f * f * f + 1.0


def in_out_quad(t: float) -> float:
    t = _clamp01(t)
    if t < 0.5:
        return 2.0 * t * t
    return 1.0 - ((-2.0 * t + 2.0) ** 2) / 2.0


def out_cubic(t: float) -> float:
    t = _clamp01(t)
    f = t - 1.0
    return f * f * f + 1.0


def steps(n: int, jump_end: bool = True):
    """Return a stepped easing function (like CSS ``steps(n, end)``).

    Used for the blinking text cursor (``steps(2, end)``).
    """

    def _step(t: float) -> float:
        t = _clamp01(t)
        if jump_end:
            return min(int(t * n) / n, 1.0)
        return min((int(t * n) + 1) / n, 1.0)

    return _step


def _clamp01(t: float) -> float:
    if t < 0.0:
        return 0.0
    if t > 1.0:
        return 1.0
    return t


# Name -> function registry so themes/components can refer to easings by string.
REGISTRY = {
    "linear": linear,
    "inOutCubic": in_out_cubic,
    "inOutQuad": in_out_quad,
    "outCubic": out_cubic,
}


def get(name: str):
    return REGISTRY.get(name, linear)
