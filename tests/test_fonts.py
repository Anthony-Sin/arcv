"""Multi-font support — FontAtlas distinctness (pure) + TextBatch rendering (GPU)."""

import os

import numpy as np
import pytest

from arcv.components.text.atlas import FontAtlas
from arcv.overlay import fonts


# -- pure: FontAtlas can load distinct faces + falls back gracefully ---------
def _first_existing(paths):
    return next((p for p in paths if os.path.exists(p)), None)


def test_fontatlas_bad_path_falls_back_to_bundled():
    bogus = FontAtlas(font_path="Z:/definitely/not/a/font.ttf")
    bundled = FontAtlas()
    assert np.array_equal(bogus.image, bundled.image)  # fell back to Share Tech Mono


def test_fontatlas_distinct_face_differs():
    alt = _first_existing([
        "C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ])
    if alt is None:
        pytest.skip("no alternate system font available")
    base = FontAtlas()
    other = FontAtlas(font_path=alt)
    # a genuinely different face changes the atlas (shape and/or pixels)
    assert base.image.shape != other.image.shape or not np.array_equal(base.image, other.image)


def test_fonts_helper_reports_roles():
    roles = fonts.available_roles()
    assert set(roles.keys()) == {"display", "ocr", "din", "term"}


# -- GPU: TextBatch renders multiple fonts + fallback ------------------------
moderngl = pytest.importorskip("moderngl")

from arcv.overlay import FlatOverlay, Draw  # noqa: E402


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_standalone_context(require=330)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"No GL context available: {e}")
    yield c
    c.release()


def test_textbatch_default_font_present(ctx):
    ov = FlatOverlay(ctx, (200, 80))
    assert ov.text.has_font("default")
    assert "default" in ov.text.fonts


def test_add_font_and_fallback(ctx):
    ov = FlatOverlay(ctx, (200, 80))
    ov.text.add_font("alt", font_path=None)   # None -> bundled, but registered under a new name
    assert ov.text.has_font("alt")
    # unknown font name falls back to default without raising
    ov.begin()
    ov.text.text("HELLO", 5, 5, 18, (1, 1, 1, 1), font="does-not-exist")
    ov.render(base_color=(0, 0, 0, 1))
    assert ctx.error == "GL_NO_ERROR"


def test_multifont_renders_pixels(ctx):
    ov = FlatOverlay(ctx, (420, 160))
    d = Draw(ov)
    fonts.register_hud_fonts(d, size=40)
    for name in ("display", "ocr", "din", "term"):
        assert ov.text.has_font(name)
    ov.begin()
    d.text("DEFAULT", 8, 6, 22, (1, 1, 1, 1))
    d.text("DISPLAY", 8, 34, 22, (1, 1, 1, 1), font="display")
    d.text("OCR-A 0123", 8, 62, 22, (1, 1, 1, 1), font="ocr")
    d.text("TERMINAL", 8, 90, 22, (1, 1, 1, 1), font="term")
    # split-text FX must work per-font too
    per = None
    d.text_fx("MIXED", 8, 120, 22, (1, 1, 1, 1), per_char=per, font="din")
    ov.render(base_color=(0.02, 0.02, 0.03, 1))
    assert ctx.error == "GL_NO_ERROR"
    assert ov.read_pixels().max() > 0


def test_font_specific_advance(ctx):
    ov = FlatOverlay(ctx, (200, 80))
    ov.text.add_font("term", font_path=_first_existing([
        "C:/Windows/Fonts/consola.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]))
    w_default = ov.text.measure("HELLO", 20, "default")
    w_term = ov.text.measure("HELLO", 20, "term")
    assert w_default > 0 and w_term > 0  # each face reports its own metrics
