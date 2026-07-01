"""Headless GPU smoke test for the reusable HUD kit primitives.

Wraps an Overlay in a Draw surface, calls EVERY arcv.overlay.hud_kit primitive
once (spread across the canvas), renders the full bloom/composite pipeline, and
asserts the GL state is clean and something was actually drawn. Plus a pure
-logic check of the Liang-Barsky segment clipper.
"""

import math

import numpy as np
import pytest

moderngl = pytest.importorskip("moderngl")

from arcv.overlay import Overlay, Draw, hud_kit
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


def test_every_hud_kit_primitive_renders(ctx):
    w, h = 640, 400
    ov = Overlay(ctx, (w, h), theme=make_theme("amber"),
                 base_color=(0.02, 0.02, 0.03, 1.0))
    out = Target(ctx, (w, h), components=4, dtype="f1")

    C = (0.9, 0.5, 0.2, 1.0)      # opaque accent
    C_T = (0.85, 0.2, 0.12, 0.24)  # translucent (for sweep_wedge)

    ov.begin()
    d = Draw(ov)

    # --- icons / badges (top row, spread across x) ---
    hud_kit.warning_triangle(d, 40, 40, 22, C, width=2.0)
    hud_kit.biohazard(d, 100, 40, 22, C)
    hud_kit.radiation_trefoil(d, 160, 40, 22, C)
    hud_kit.hexagon(d, 220, 40, 22, C, width=2.0, flat_top=True, fill=(0.9, 0.5, 0.2, 0.1))
    hud_kit.hex_badge(d, 280, 40, 22, "42", C, width=2.0)
    hud_kit.crescent(d, 340, 40, 22, C, width=2.0)

    # --- textures / strips (second band) ---
    hud_kit.hazard_stripes(d, 400, 24, 560, 56, C, gap=12.0, width=5.0)
    hud_kit.barcode(d, 400, 70, 120, 24, C, seed=3, vertical=True)
    hud_kit.waveform(d, 20, 90, 160, 40, C, bars=40, seed=1)
    hud_kit.spectrum_bar(d, 200, 90, 10, 60, segments=7, vertical=True)
    hud_kit.segmented_bar(d, 230, 100, 150, 12, 10, C, filled=(0, 2, 5))

    # --- gauges / radar (mid band) ---
    hud_kit.tick_ring(d, 70, 210, 44, 48, 8, C, width=1.0, major_every=6, major_length=14)
    hud_kit.radial_gauge(d, 180, 210, 46, 0.62, C, needle_deg=58, hub=True)
    hud_kit.sweep_wedge(d, 300, 210, 46, math.radians(18), math.radians(88), C_T)
    hud_kit.contour_map(d, 430, 210, 60, C, seed=0, systems=3)

    # --- wireframe (bottom band) ---
    hud_kit.wireframe_sphere(d, 80, 330, 44, C, vortex=False, lat=8, lon=12)
    hud_kit.wireframe_sphere(d, 200, 330, 44, C, vortex=True)
    hud_kit.wireframe_terrain(d, 300, 300, 130, 90, C, cols=32, rows=20, seed=2)
    hud_kit.face_mesh(d, 560, 320, 100, 150, C, markers=True)

    ov.render(0.0, target=out.fbo)

    assert ctx.error == "GL_NO_ERROR"
    img = ov.read_pixels(out.fbo)
    assert img.shape == (h, w, 3)
    assert img.max() > 0, "expected the HUD kit primitives to draw something"


def test_clip_seg_pure_logic():
    """The ported Liang-Barsky clipper keeps in-box segments, trims crossing
    ones, and rejects fully-outside ones."""
    from arcv.overlay.hud_kit import _clip_seg

    # fully inside -> unchanged
    seg = _clip_seg(2, 2, 8, 8, 0, 0, 10, 10)
    assert seg is not None
    assert seg == pytest.approx((2, 2, 8, 8))

    # crossing the box -> trimmed to the boundary (diagonal through unit-ish box)
    seg = _clip_seg(-5, 5, 15, 5, 0, 0, 10, 10)
    assert seg is not None
    ax, ay, bx, by = seg
    assert ax == pytest.approx(0.0)
    assert bx == pytest.approx(10.0)
    assert ay == pytest.approx(5.0) and by == pytest.approx(5.0)

    # fully outside (above the box) -> None
    assert _clip_seg(-5, -5, 15, -5, 0, 0, 10, 10) is None
