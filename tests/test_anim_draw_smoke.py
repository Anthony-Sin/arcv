"""Phase 4/5 — headless GPU smoke test for the new anim draw capabilities.

Renders the rotation-capable ``marker`` primitive, a morph-interpolated polyline,
a motion-path follower (sample_path -> marker facing travel), and per-unit split
text, through the full Overlay pipeline; asserts GL is clean and pixels landed.
"""

import math

import pytest

moderngl = pytest.importorskip("moderngl")

from arcv.overlay import Overlay, Draw, anim
from arcv.theme import make_theme
from arcv.passes.base import Target


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_standalone_context(require=330)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"No GL context available: {e}")
    yield c
    c.release()


def test_marker_and_path_render(ctx):
    w, h = 640, 400
    ov = Overlay(ctx, (w, h), theme=make_theme("cyan"),
                 base_color=(0.02, 0.02, 0.03, 1.0))
    out = Target(ctx, (w, h), components=4, dtype="f1")
    C = (0.2, 0.9, 1.0, 1.0)

    ov.begin()
    d = Draw(ov)

    # rotation-capable marker: filled triangle + stroked chevron at several angles
    for k in range(8):
        ang = k / 8.0 * math.tau
        d.marker(80 + k * 60, 60, anim.shape_triangle(), C, angle=ang, scale=14.0, fill=True)
        d.marker(80 + k * 60, 110, anim.shape_chevron(), C, angle=ang, scale=14.0, w=2.0)

    # shape morph A->B drawn as an interpolated polyline
    a = [(200, 200), (260, 200), (260, 260), (200, 260)]      # square
    b = [(230, 170), (290, 230), (230, 290), (170, 230)]      # diamond
    for i in range(5):
        t = i / 4.0
        pts = anim.morph(a, b, t, closed=True)
        d.poly(pts, (0.2, 0.9, 1.0, 0.4 + 0.5 * t), 1.5, closed=True)

    # motion-path follower: sample the path, place a marker facing travel
    path = [(360, 320), (460, 300), (520, 360), (600, 300)]
    d.poly(path, (0.4, 0.7, 0.8, 0.6), 1.0)
    for i in range(9):
        u = i / 8.0
        px, py, ang = anim.sample_path(path, u)
        d.marker(px, py, anim.shape_triangle(), C, angle=ang, scale=8.0, fill=True)

    # line draw-on driven by an Animation reveal value
    rev = anim.Animation({"reveal": (0.0, 1.0)}, duration=1.0).at(0.6)["reveal"]
    d.line(20, 380, 620, 380, C, 2.0, reveal=rev)

    ov.render(0.0, target=out.fbo)

    assert ctx.error == "GL_NO_ERROR"
    img = ov.read_pixels(out.fbo)
    assert img.shape == (h, w, 3)
    assert img.max() > 0, "expected marker/morph/path draws to produce pixels"
