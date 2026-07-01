"""Pure-logic tests for the overlay animation helpers (no GPU)."""

import math

from arcv.overlay import anim
from arcv.overlay.anim import Sequencer, flicker, truncate_polyline


def test_sequencer_progress():
    q = Sequencer(0.0)
    assert q.at(0.5, 0.4) == 0.0          # before delay
    q = Sequencer(0.7)
    p = q.at(0.5, 0.4, anim.linear)       # 0.2/0.4 = 0.5
    assert abs(p - 0.5) < 1e-6
    q = Sequencer(5.0)
    assert q.at(0.5, 0.4) == 1.0          # well after


def test_sequencer_stagger_orders():
    q = Sequencer(1.0)
    p0 = q.stagger(0, 0.0, 0.2, 0.3, anim.linear)
    p1 = q.stagger(1, 0.0, 0.2, 0.3, anim.linear)
    assert p0 >= p1                         # later items lag


def test_truncate_polyline_half():
    pts = [(0.0, 0.0), (10.0, 0.0)]
    out = truncate_polyline(pts, 0.5)
    assert len(out) == 2
    assert abs(out[1][0] - 5.0) < 1e-6      # halfway along
    assert truncate_polyline(pts, 0.0) == []
    assert truncate_polyline(pts, 1.0) == pts


def test_truncate_polyline_closed_wraps():
    sq = [(0, 0), (10, 0), (10, 10), (0, 10)]
    full = truncate_polyline(sq, 1.0, closed=True)
    assert full[-1] == sq[0]                # closing point appended


def test_flicker_endpoints():
    assert flicker(0.0, 1.23) == 0.0
    assert flicker(1.0, 1.23) == 1.0
    v = flicker(0.5, 1.23)
    assert 0.0 <= v <= 1.0


def test_eases_bounded():
    for e in (anim.linear, anim.out_cubic, anim.in_out_cubic, anim.out_back):
        assert abs(e(0.0)) < 1e-6
        assert abs(e(1.0) - 1.0) < 1e-6
