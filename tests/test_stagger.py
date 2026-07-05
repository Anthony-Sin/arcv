"""Phase 3 — full anime.js stagger() (pure Python, no GPU)."""

import math

import pytest

from arcv.overlay import anim
from arcv.overlay.anim import stagger, Stagger, Timeline


# ===========================================================================
#  1D staggering
# ===========================================================================
def test_stagger_from_first_even_spacing():
    s = stagger(0.1)
    vals = s.values(5)
    assert vals == pytest.approx([0.0, 0.1, 0.2, 0.3, 0.4])


def test_stagger_from_last():
    s = stagger(0.1, from_="last")
    vals = s.values(5)
    assert vals == pytest.approx([0.4, 0.3, 0.2, 0.1, 0.0])


def test_stagger_from_center():
    s = stagger(0.1, from_="center")
    vals = s.values(5)
    assert vals == pytest.approx([0.2, 0.1, 0.0, 0.1, 0.2])


def test_stagger_from_index():
    s = stagger(1.0, from_=1)
    vals = s.values(4)
    assert vals == pytest.approx([1.0, 0.0, 1.0, 2.0])


def test_stagger_start_offset():
    s = stagger(0.1, start=1.0)
    assert s.values(3) == pytest.approx([1.0, 1.1, 1.2])


def test_stagger_range_distribution():
    # distribute values from 0 to 100 across 5 indices
    s = stagger((0.0, 100.0))
    assert s.values(5) == pytest.approx([0.0, 25.0, 50.0, 75.0, 100.0])


def test_stagger_range_param_overrides_scalar():
    s = stagger(0.1, range=(10.0, 20.0))
    assert s.values(3) == pytest.approx([10.0, 15.0, 20.0])


def test_stagger_callable_index_signature():
    s = stagger(0.1)
    # usable as an Animation/Timeline function-value: (index, total) -> value
    assert s(0, 5) == pytest.approx(0.0)
    assert s(3, 5) == pytest.approx(0.3)


def test_stagger_reversed():
    s = stagger(0.1, reversed=True)
    assert s.values(3) == pytest.approx([0.2, 0.1, 0.0])


# ===========================================================================
#  Grid staggering
# ===========================================================================
def test_stagger_grid_center_distances():
    # 3x3 grid, spacing 1, from center -> euclidean cell distances
    s = stagger(1.0, grid=(3, 3), from_="center")
    vals = s.values(9)
    # layout (col,row): index = row*3 + col
    expected = []
    for i in range(9):
        col, row = i % 3, i // 3
        expected.append(math.hypot(col - 1, row - 1))
    assert vals == pytest.approx(expected)


def test_stagger_grid_axis_x_constraint():
    s = stagger(1.0, grid=(3, 3), from_="center", axis="x")
    vals = s.values(9)
    # only horizontal distance counts -> each row identical: [1,0,1]
    assert vals == pytest.approx([1, 0, 1, 1, 0, 1, 1, 0, 1])


def test_stagger_grid_axis_y_constraint():
    s = stagger(1.0, grid=(3, 3), from_="center", axis="y")
    vals = s.values(9)
    assert vals == pytest.approx([1, 1, 1, 0, 0, 0, 1, 1, 1])


def test_stagger_grid_from_corner_cell():
    s = stagger(1.0, grid=(3, 3), from_=(0, 0))
    vals = s.values(9)
    expected = [math.hypot(i % 3, i // 3) for i in range(9)]
    assert vals == pytest.approx(expected)


def test_stagger_grid_from_last_cell():
    s = stagger(1.0, grid=(2, 2), from_="last")
    # last cell is (1,1); distances: (0,0)->sqrt2, (1,0)->1, (0,1)->1, (1,1)->0
    assert s.values(4) == pytest.approx([math.sqrt(2), 1.0, 1.0, 0.0])


# ===========================================================================
#  Ease across the distribution
# ===========================================================================
def test_stagger_ease_reshapes_distribution():
    plain = stagger(1.0).values(5)
    eased = stagger(1.0, ease="inQuad").values(5)
    # endpoints identical, interior pulled toward the origin by the ease
    assert plain[0] == pytest.approx(eased[0])
    assert plain[-1] == pytest.approx(eased[-1])
    assert eased[1] < plain[1]
    assert eased[2] < plain[2]


# ===========================================================================
#  Determinism
# ===========================================================================
def test_stagger_deterministic():
    s = stagger(0.1, grid=(4, 4), from_="center", ease="outCubic")
    a = s.values(16)
    b = s.values(16)
    assert a == b


# ===========================================================================
#  Timeline.stagger integration
# ===========================================================================
def test_timeline_stagger_delays_children():
    tl = Timeline()
    tl.stagger(4, {"scale": (0.0, 1.0)},
               {"duration": 1.0, "delay": stagger(0.5)})
    # 4 children, each delayed 0.5 more; child k active window [0.5k, 0.5k+1]
    assert len(tl.children) == 4
    # at t=0.5, child 0 has run 0.5s (scale 0.5), child 1 just starting (0.0)
    snap = tl.at(0.5)
    assert snap["a0"]["scale"] == pytest.approx(0.5, abs=1e-6)
    assert snap["a1"]["scale"] == pytest.approx(0.0, abs=1e-6)


def test_timeline_stagger_function_value_in_props():
    tl = Timeline()
    # per-index target via stagger range in the property itself
    tl.stagger(5, {"x": (0.0, stagger((0.0, 40.0)))}, {"duration": 1.0}, position=0.0)
    snap = tl.at(1.0)
    ends = [snap[f"a{k}"]["x"] for k in range(5)]
    assert ends == pytest.approx([0.0, 10.0, 20.0, 30.0, 40.0])


def test_timeline_stagger_position_staggered_starts():
    tl = Timeline()
    tl.stagger(3, {"o": (0.0, 1.0)}, {"duration": 0.5}, position=stagger(1.0))
    assert [c.start for c in tl.children] == pytest.approx([0.0, 1.0, 2.0])


def test_stagger_empty_total():
    assert stagger(0.1).values(0) == []
    assert stagger(0.1)(0, 0) == 0.0
