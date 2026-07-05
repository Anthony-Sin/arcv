"""Headless smoke test for the old-vs-new boot demo (examples/anime_boot.py)."""

import os
import sys

import numpy as np
import pytest

moderngl = pytest.importorskip("moderngl")

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
sys.path.insert(0, _EXAMPLES)

from arcv.overlay import FlatOverlay, Draw, fonts  # noqa: E402

layout = pytest.importorskip("anime_boot_layout")


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_standalone_context(require=330)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"No GL context available: {e}")
    yield c
    c.release()


def _render(ctx, t):
    W, H = 1120, 560
    ov = FlatOverlay(ctx, (W, H))
    d = Draw(ov)
    fonts.register_hud_fonts(d, size=40)
    ov.begin()
    layout.build_old(d, (16, 40, W // 2 - 10, H - 12), t)
    layout.build_new(d, (W // 2 + 10, 40, W - 16, H - 12), t)
    ov.render(base_color=(0.02, 0.02, 0.04, 1.0))
    return ov.read_pixels()


def test_both_sides_build_and_draw(ctx):
    img = _render(ctx, 2.0)
    assert img.shape == (560, 1120, 3)
    assert img.max() > 0
    # both halves have content
    assert img[:, :560].max() > 0 and img[:, 560:].max() > 0


def test_boot_deterministic(ctx):
    assert np.array_equal(_render(ctx, 1.4), _render(ctx, 1.4))


def test_boot_animates(ctx):
    assert not np.array_equal(_render(ctx, 0.6), _render(ctx, 2.6))
