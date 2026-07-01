"""Headless GPU smoke test for FlatOverlay + the yellow warning HUD layout.

FlatOverlay draws opaque premultiplied-over geometry onto a solid base OR over a
camera frame, so it can paint black-on-yellow (which the additive glow Overlay
cannot). This renders one warning-HUD frame over a synthetic "camera" and checks
that:

* black content actually darkens the yellow fill (dark-on-light works),
* the camera base shows through the panel-free viewport window,
* the whole warning_hud_layout builds without a GL error.
"""

import os
import sys

import numpy as np
import pytest

moderngl = pytest.importorskip("moderngl")

from arcv.overlay import FlatOverlay

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
sys.path.insert(0, _EXAMPLES)


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_standalone_context(require=330)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"No GL context available: {e}")
    yield c
    c.release()


def test_black_on_yellow_and_camera_base(ctx):
    w, h = 320, 200
    ov = FlatOverlay(ctx, (w, h))
    YEL = (0.96, 0.88, 0.06, 1.0)
    BLK = (0.05, 0.05, 0.04, 1.0)

    # a bright red camera frame (BGR) so we can tell where it shows through
    cam = np.zeros((h, w, 3), np.uint8)
    cam[:, :, 2] = 220  # red channel in BGR

    ov.begin()
    # opaque yellow panel with a big black block on top of it
    ov.vector.rounded_rect_fill(20, 20, 160, 120, 6, YEL)
    ov.vector.rounded_rect_fill(40, 40, 120, 90, 2, BLK)
    ov.render(cam_frame=cam)
    img = ov.read_pixels()  # RGB uint8

    assert img.shape == (h, w, 3)
    # yellow fill region: high R, high G, low B
    yr = img[30, 150]
    assert yr[0] > 150 and yr[1] > 130 and yr[2] < 90
    # black block darkens the yellow underneath it
    br = img[65, 80]
    assert br.max() < 90
    # panel-free corner shows the red camera base through
    cr = img[180, 300]
    assert cr[0] > 130 and cr[1] < 90 and cr[2] < 90


def test_solid_base_without_camera(ctx):
    ov = FlatOverlay(ctx, (128, 96), base_color=(0.1, 0.1, 0.12, 1.0))
    ov.begin()
    ov.vector.rounded_rect_fill(10, 10, 100, 80, 4, (1.0, 1.0, 1.0, 1.0))
    ov.render()  # no camera -> solid base
    img = ov.read_pixels()
    assert img.shape == (96, 128, 3)
    assert img.max() > 240  # the white fill drew something bright
    assert int(img[90, 120].max()) < 60  # base color outside the fill


def test_warning_hud_layout_builds(ctx):
    import warning_hud_layout as layout
    from _hud_adapters import ArcvAdapter

    w, h = 480, 288
    ov = FlatOverlay(ctx, (w, h))
    cam = np.full((h, w, 3), 20, np.uint8)
    for t in (1.0, 3.6, 7.0, 9.6):        # boot / locked / lost / reacquire
        st = layout.state_at(t)
        ov.begin()
        layout.build(ArcvAdapter(ov), w, h, t, st)
        ov.render(cam_frame=cam)
        img = ov.read_pixels()
        assert img.shape == (h, w, 3)
        assert img.max() > 120           # yellow panels present
    # detection-driven state path also builds
    st = layout.state_from_detections(0.5, None, 30.0)
    assert st.alert and not st.locked
