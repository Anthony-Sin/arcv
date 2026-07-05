"""Phase 7 — ARCV-native adapters for anime.js browser-only features (pure)."""

import pytest

from arcv.overlay.anim import Timer, Animation
from arcv.overlay.adapters import DriverFromSignal, Draggable, Scope, NOT_APPLICABLE


# -- DriverFromSignal (ScrollObserver analog) --------------------------------
def test_driver_progress_maps_lo_hi():
    d = DriverFromSignal(lo=0.0, hi=10.0)
    assert d.progress(0.0) == pytest.approx(0.0)
    assert d.progress(5.0) == pytest.approx(0.5)
    assert d.progress(10.0) == pytest.approx(1.0)


def test_driver_clamps():
    d = DriverFromSignal(lo=0.0, hi=10.0)
    assert d.progress(-5.0) == pytest.approx(0.0)
    assert d.progress(50.0) == pytest.approx(1.0)


def test_driver_ease_applied():
    d = DriverFromSignal(lo=0.0, hi=1.0, ease="inQuad")
    assert d.progress(0.5) == pytest.approx(0.25)


def test_driver_maps_to_target_time_and_samples():
    a = Animation({"x": (0.0, 100.0)}, duration=1.0)
    d = DriverFromSignal(a, lo=0.0, hi=10.0)
    assert d.time(5.0) == pytest.approx(0.5)
    assert d.sample(5.0)["x"] == pytest.approx(50.0)


def test_driver_bare_returns_progress():
    d = DriverFromSignal(lo=0.0, hi=4.0)
    assert d.sample(2.0) == pytest.approx(0.5)


def test_driver_smoothing_lags_toward_target():
    d = DriverFromSignal(lo=0.0, hi=1.0, smoothing=0.5)
    d.progress(0.0)                       # seed at 0
    a = d.progress(1.0)                   # first step toward 1
    b = d.progress(1.0)                   # second step, closer
    assert 0.0 < a < b < 1.0


def test_driver_fires_target_callbacks():
    events = []
    tm = Timer(1.0, on_complete=lambda s: events.append("done"))
    d = DriverFromSignal(tm, lo=0.0, hi=1.0)
    d.sample(0.0)
    d.sample(0.5)
    d.sample(1.0)                          # reaches the end -> complete once
    assert events.count("done") == 1


# -- Draggable (createDraggable analog) --------------------------------------
def test_draggable_basic_move():
    d = Draggable((0.0, 0.0))
    d.grab(10.0, 10.0)
    assert d.move(15.0, 12.0) == (5.0, 2.0)


def test_draggable_ignores_move_without_grab():
    d = Draggable((3.0, 3.0))
    assert d.move(50.0, 50.0) == (3.0, 3.0)


def test_draggable_bounds_clamp():
    d = Draggable((0.0, 0.0), bounds=(0.0, 0.0, 4.0, 4.0))
    d.grab(0.0, 0.0)
    assert d.move(10.0, 1.0) == (4.0, 1.0)


def test_draggable_axis_constraint():
    d = Draggable((0.0, 0.0), axis="x")
    d.grab(0.0, 0.0)
    x, y = d.move(5.0, 9.0)
    assert x == pytest.approx(5.0) and y == pytest.approx(0.0)


def test_draggable_snap():
    d = Draggable((0.0, 0.0), snap=(5.0, 5.0))
    d.grab(0.0, 0.0)
    x, y = d.move(7.0, 3.0)
    assert x == pytest.approx(5.0) and y == pytest.approx(5.0)


def test_draggable_inertia_decays():
    d = Draggable((0.0, 0.0), friction=0.5)
    d.grab(0.0, 0.0)
    d.move(10.0, 0.0)        # velocity vx = 10
    d.release()
    x1 = d.update()[0]       # coasts +10 -> 20
    x2 = d.update()[0]       # coasts +5  -> 25
    assert x1 == pytest.approx(20.0)
    assert x2 == pytest.approx(25.0)


def test_draggable_callbacks():
    log = []
    d = Draggable((0.0, 0.0))
    d.on_grab = lambda s: log.append("grab")
    d.on_drag = lambda s: log.append("drag")
    d.on_release = lambda s: log.append("release")
    d.grab(0, 0)
    d.move(1, 1)
    d.release()
    assert log == ["grab", "drag", "release"]


# -- Scope (createScope + responsive analog) ---------------------------------
def test_scope_scales_per_axis():
    s = Scope((640, 360), design=(1280, 720))
    assert s.x(100) == pytest.approx(50.0)
    assert s.y(100) == pytest.approx(50.0)
    assert s.pos(200, 100) == pytest.approx((100.0, 50.0))


def test_scope_uniform_px():
    s = Scope((640, 720), design=(1280, 720))  # sx=0.5, sy=1.0
    assert s.px(10) == pytest.approx(5.0)       # uniform uses min axis


def test_scope_breakpoints():
    assert Scope((640, 360)).breakpoint == "sm"
    assert Scope((800, 600)).breakpoint == "md"
    assert Scope((1400, 900)).breakpoint == "lg"
    assert Scope((2000, 1100)).breakpoint == "xl"
    assert Scope((640, 360)).matches("sm")


def test_scope_resize():
    s = Scope((640, 360), design=(1280, 720))
    s.resize(1280, 720)
    assert s.x(100) == pytest.approx(100.0)
    assert s.breakpoint == "lg"


def test_not_applicable_documented():
    assert len(NOT_APPLICABLE) >= 4
    assert all(isinstance(x, str) for x in NOT_APPLICABLE)
