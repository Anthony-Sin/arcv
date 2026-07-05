"""Phase 4 — motion-path + shape-morph geometry (pure Python, no GPU)."""

import math

import pytest

from arcv.overlay import anim


# -- sample_path (arc-length + tangent) --------------------------------------
def test_sample_path_arc_length_midpoint():
    # L-shape, total length 20; u=0.5 lands exactly on the corner (10,0)
    pts = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]
    x, y, ang = anim.sample_path(pts, 0.5)
    assert (x, y) == pytest.approx((10.0, 0.0))


def test_sample_path_endpoints():
    pts = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]
    x0, y0, _ = anim.sample_path(pts, 0.0)
    x1, y1, _ = anim.sample_path(pts, 1.0)
    assert (x0, y0) == pytest.approx((0.0, 0.0))
    assert (x1, y1) == pytest.approx((10.0, 10.0))


def test_sample_path_tangent_angle():
    # horizontal segment -> angle 0; vertical (downward in screen space) -> +pi/2
    pts = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]
    _, _, a_h = anim.sample_path(pts, 0.25)
    _, _, a_v = anim.sample_path(pts, 0.75)
    assert a_h == pytest.approx(0.0)
    assert a_v == pytest.approx(math.pi / 2)


def test_sample_path_clamps_u():
    pts = [(0.0, 0.0), (4.0, 0.0)]
    assert anim.sample_path(pts, -1.0)[:2] == pytest.approx((0.0, 0.0))
    assert anim.sample_path(pts, 2.0)[:2] == pytest.approx((4.0, 0.0))


def test_sample_path_degenerate():
    assert anim.sample_path([], 0.5) == (0.0, 0.0, 0.0)
    assert anim.sample_path([(3.0, 7.0)], 0.5) == (3.0, 7.0, 0.0)


def test_path_length_open_and_closed():
    sq = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert anim.path_length(sq) == pytest.approx(30.0)
    assert anim.path_length(sq, closed=True) == pytest.approx(40.0)


# -- resample ----------------------------------------------------------------
def test_resample_count_and_spacing():
    pts = [(0.0, 0.0), (10.0, 0.0)]
    out = anim.resample_polyline(pts, 5)
    assert len(out) == 5
    xs = [p[0] for p in out]
    assert xs == pytest.approx([0.0, 2.5, 5.0, 7.5, 10.0])


def test_resample_closed_no_duplicate_endpoint():
    sq = [(0, 0), (10, 0), (10, 10), (0, 10)]
    out = anim.resample_polyline(sq, 4, closed=True)
    assert len(out) == 4
    assert out[0] != out[-1]  # closed sampling doesn't repeat the start


# -- morph -------------------------------------------------------------------
def test_morph_point_count_matches():
    a = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]        # 3 pts
    b = [(0.0, 0.0), (5.0, 5.0), (0.0, 10.0), (2.0, 3.0)]  # 4 pts
    m = anim.morph(a, b, 0.5)
    assert len(m) == 4  # resampled to max count


def test_morph_endpoints_are_resamples():
    a = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]
    b = [(0.0, 0.0), (0.0, 10.0), (-10.0, 10.0)]
    n = max(len(a), len(b))
    assert anim.morph(a, b, 0.0) == pytest.approx(anim.resample_polyline(a, n))
    assert anim.morph(a, b, 1.0) == pytest.approx(anim.resample_polyline(b, n))


def test_morph_midpoint_between():
    a = [(0.0, 0.0), (10.0, 0.0)]
    b = [(0.0, 10.0), (10.0, 10.0)]
    m = anim.morph(a, b, 0.5)
    assert m[0] == pytest.approx((0.0, 5.0))
    assert m[-1] == pytest.approx((10.0, 5.0))


# -- rotate_points -----------------------------------------------------------
def test_rotate_points_quarter_turn():
    out = anim.rotate_points([(1.0, 0.0)], math.pi / 2)
    assert out[0] == pytest.approx((0.0, 1.0), abs=1e-9)


def test_rotate_points_about_pivot():
    out = anim.rotate_points([(2.0, 1.0)], math.pi, pivot=(1.0, 1.0))
    assert out[0] == pytest.approx((0.0, 1.0), abs=1e-9)


# -- marker shapes -----------------------------------------------------------
def test_marker_shapes_face_positive_x():
    for shape in (anim.shape_triangle(), anim.shape_chevron(), anim.shape_diamond()):
        assert len(shape) >= 3
        # tip / rightmost point is on +x axis-ish (leads travel direction)
        rightmost = max(shape, key=lambda p: p[0])
        assert rightmost[0] > 0


# -- reveal wired to an Animation (line draw-on) -----------------------------
def test_animation_drives_reveal_and_truncate():
    a = anim.Animation({"reveal": (0.0, 1.0)}, duration=1.0)
    pts = [(0.0, 0.0), (10.0, 0.0)]
    half = a.at(0.5)["reveal"]
    assert half == pytest.approx(0.5)
    drawn = anim.truncate_polyline(pts, half)
    assert drawn[-1][0] == pytest.approx(5.0)  # drawn halfway along
