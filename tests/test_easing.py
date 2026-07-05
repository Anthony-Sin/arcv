"""Phase 1 — full anime.js easing set (pure Python, no GPU)."""

import math

import pytest

from arcv import easing


# Named eases that must exist and hit the [0,1] endpoints exactly.
ALL_NAMED = [
    "linear",
    "inQuad", "outQuad", "inOutQuad",
    "inCubic", "outCubic", "inOutCubic",
    "inQuart", "outQuart", "inOutQuart",
    "inQuint", "outQuint", "inOutQuint",
    "inSine", "outSine", "inOutSine",
    "inExpo", "outExpo", "inOutExpo",
    "inCirc", "outCirc", "inOutCirc",
    "inBack", "outBack", "inOutBack",
    "inElastic", "outElastic", "inOutElastic",
    "inBounce", "outBounce", "inOutBounce",
]

# Smooth (non-overshooting) eases should be monotonic non-decreasing.
MONOTONIC = [
    "linear",
    "inQuad", "outQuad", "inOutQuad",
    "inCubic", "outCubic", "inOutCubic",
    "inQuart", "outQuart", "inOutQuart",
    "inQuint", "outQuint", "inOutQuint",
    "inSine", "outSine", "inOutSine",
    "inExpo", "outExpo", "inOutExpo",
    "inCirc", "outCirc", "inOutCirc",
]


@pytest.mark.parametrize("name", ALL_NAMED)
def test_endpoints(name):
    f = easing.REGISTRY[name]
    assert abs(f(0.0)) < 1e-6, name
    assert abs(f(1.0) - 1.0) < 1e-6, name


@pytest.mark.parametrize("name", ALL_NAMED)
def test_clamped_outside_domain(name):
    f = easing.REGISTRY[name]
    # inputs outside [0,1] are clamped, so they equal the endpoint values
    assert abs(f(-0.5) - f(0.0)) < 1e-9, name
    assert abs(f(1.5) - f(1.0)) < 1e-9, name


@pytest.mark.parametrize("name", MONOTONIC)
def test_monotonic_where_expected(name):
    f = easing.REGISTRY[name]
    prev = f(0.0)
    for i in range(1, 101):
        cur = f(i / 100.0)
        assert cur >= prev - 1e-6, f"{name} decreased at {i}"
        prev = cur


def test_backward_compatible_names():
    # original snake_case functions still importable + correct
    for fn in (easing.linear, easing.out_cubic, easing.in_out_cubic, easing.in_out_quad):
        assert abs(fn(0.0)) < 1e-6
        assert abs(fn(1.0) - 1.0) < 1e-6
    # midpoint of in_out_cubic unchanged (0.5)
    assert abs(easing.in_out_cubic(0.5) - 0.5) < 1e-9
    # 0.9375 at t=0.75 (regression guard vs old implementation)
    assert abs(easing.in_out_cubic(0.75) - 0.9375) < 1e-9


def test_overshoot_actually_overshoots():
    # back overshoots below 0 on the way in and above 1 on the way out
    assert min(easing.in_back(t / 100) for t in range(100)) < -0.01
    assert max(easing.out_back(t / 100) for t in range(100)) > 1.01
    # elastic wiggles past 1
    assert max(easing.out_elastic(t / 100) for t in range(100)) > 1.05
    # bounce never exceeds 1 and stays >= 0
    vals = [easing.out_bounce(t / 100) for t in range(101)]
    assert max(vals) <= 1.0 + 1e-9 and min(vals) >= -1e-9


# -- steps -------------------------------------------------------------------
def test_steps_end():
    s = easing.steps(4, jump_end=True)
    assert s(0.0) == 0.0
    assert s(0.24) == 0.0
    assert abs(s(0.26) - 0.25) < 1e-9
    assert abs(s(0.99) - 0.75) < 1e-9
    assert s(1.0) == 1.0


# -- cubic bezier ------------------------------------------------------------
def test_cubic_bezier_linear_control_points():
    f = easing.cubic_bezier(1 / 3, 1 / 3, 2 / 3, 2 / 3)
    for i in range(0, 101):
        t = i / 100.0
        assert abs(f(t) - t) < 1e-3, t


def test_cubic_bezier_identity_control_points():
    f = easing.cubic_bezier(0.0, 0.0, 1.0, 1.0)
    assert abs(f(0.0)) < 1e-9 and abs(f(1.0) - 1.0) < 1e-9


def test_cubic_bezier_ease_monotonic_and_bounds():
    # CSS "ease" curve
    f = easing.cubic_bezier(0.25, 0.1, 0.25, 1.0)
    assert abs(f(0.0)) < 1e-6 and abs(f(1.0) - 1.0) < 1e-6
    prev = -1.0
    for i in range(0, 101):
        v = f(i / 100.0)
        assert v >= prev - 1e-6
        prev = v
    # ease front-loads: past the halfway output well before halfway time
    assert f(0.35) > 0.5


def test_cubic_bezier_matches_known_value():
    # symmetric bezier at t=0.5 should output exactly 0.5
    f = easing.cubic_bezier(0.42, 0.0, 0.58, 1.0)
    assert abs(f(0.5) - 0.5) < 1e-6


# -- spring ------------------------------------------------------------------
def test_spring_settles_to_one():
    sp = easing.spring()
    assert sp(0.0) == 0.0
    assert abs(sp(1.0) - 1.0) < 1e-6
    assert sp.duration > 0.0
    # near the end it should be within a hair of the target
    assert abs(sp(0.98) - 1.0) < 0.02


def test_spring_underdamped_overshoots():
    sp = easing.spring(mass=1.0, stiffness=180.0, damping=8.0)
    peak = max(sp(i / 200.0) for i in range(201))
    assert peak > 1.02  # bouncy spring overshoots the target


def test_spring_critically_damped_no_overshoot():
    # heavy damping -> monotone approach, no overshoot past 1
    sp = easing.spring(mass=1.0, stiffness=100.0, damping=40.0)
    assert max(sp(i / 200.0) for i in range(201)) <= 1.001


def test_spring_duration_scales_with_damping():
    # at fixed stiffness, more damping (toward critical) settles faster
    bouncy = easing.spring(stiffness=200.0, damping=5.0)   # very underdamped
    snappy = easing.spring(stiffness=200.0, damping=28.0)  # near critical
    assert snappy.duration < bouncy.duration


# -- parameterized factories -------------------------------------------------
def test_back_factory_overshoot_grows():
    weak = easing.back(1.0, mode="out")
    strong = easing.back(4.0, mode="out")
    peak_weak = max(weak(t / 100) for t in range(100))
    peak_strong = max(strong(t / 100) for t in range(100))
    assert peak_strong > peak_weak
    assert abs(strong(0.0)) < 1e-9 and abs(strong(1.0) - 1.0) < 1e-9


def test_elastic_factory_endpoints_and_modes():
    for mode in ("in", "out", "inOut"):
        f = easing.elastic(1.2, 0.4, mode=mode)
        assert abs(f(0.0)) < 1e-9 and abs(f(1.0) - 1.0) < 1e-9


# -- registry / get() string resolution --------------------------------------
def test_get_registry_names():
    assert easing.get("outBounce") is easing.out_bounce
    assert easing.get("inOutSine") is easing.in_out_sine
    assert easing.get("out_cubic") is easing.out_cubic


def test_get_passthrough_and_fallback():
    assert easing.get(easing.linear) is easing.linear
    assert easing.get("nonsense-name") is easing.linear
    assert easing.get(None) is easing.linear


def test_get_factory_strings():
    st = easing.get("steps(4)")
    assert abs(st(0.26) - 0.25) < 1e-9

    bez = easing.get("cubicBezier(0.42,0,0.58,1)")
    assert abs(bez(0.5) - 0.5) < 1e-6

    sp = easing.get("spring(1,120,10)")
    assert abs(sp(1.0) - 1.0) < 1e-6

    ob = easing.get("outBack(3)")
    assert max(ob(t / 100) for t in range(100)) > 1.05

    oe = easing.get("outElastic(1.2,0.4)")
    assert abs(oe(0.0)) < 1e-9 and abs(oe(1.0) - 1.0) < 1e-9


def test_get_bad_factory_falls_back_to_linear():
    # malformed args -> linear, never raises
    assert easing.get("cubicBezier(0.2)") is easing.linear
    assert easing.get("spring(") is easing.linear
