"""Phase 8 — headless smoke test for the anime.js gallery example.

Imports the example layout and renders a couple of frames through the real
FlatOverlay pipeline, asserting the whole gallery draws without error and that
the build is deterministic in t (same t -> identical pixels).
"""

import os
import sys

import numpy as np
import pytest

moderngl = pytest.importorskip("moderngl")

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
sys.path.insert(0, _EXAMPLES)

from arcv.overlay import FlatOverlay, Draw  # noqa: E402

layout = pytest.importorskip("anime_gallery_layout")


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_standalone_context(require=330)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"No GL context available: {e}")
    yield c
    c.release()


def _render(ctx, t):
    W, H = 1200, 720
    ov = FlatOverlay(ctx, (W, H))
    d = Draw(ov)
    ov.begin()
    layout.build(d, W, H, t)
    ov.render(base_color=(0.02, 0.02, 0.04, 1.0))
    return ov.read_pixels()


def test_gallery_builds_and_draws(ctx):
    img = _render(ctx, 1.6)
    assert img.shape == (720, 1200, 3)
    assert img.max() > 0, "expected the gallery to draw something"


def test_gallery_deterministic_in_t(ctx):
    a = _render(ctx, 2.3)
    b = _render(ctx, 2.3)
    assert np.array_equal(a, b), "same t must produce identical pixels"


def test_gallery_animates_over_time(ctx):
    a = _render(ctx, 0.5)
    b = _render(ctx, 3.7)
    assert not np.array_equal(a, b), "different t should change the frame"
