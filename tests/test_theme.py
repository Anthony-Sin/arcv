import math

from arcv import theme
from arcv.theme import Theme


def approx(a, b, eps=1e-3):
    return all(abs(x - y) < eps for x, y in zip(a, b))


def test_hsl_to_rgb_cyan():
    assert approx(theme.hsl_to_rgb(180, 1.0, 0.5), (0.0, 1.0, 1.0))


def test_hsl_to_rgb_gray():
    assert approx(theme.hsl_to_rgb(0, 0.0, 0.5), (0.5, 0.5, 0.5))


def test_hex_to_rgba():
    r, g, b, a = theme.hex_to_rgba("#111111")
    assert math.isclose(r, 17 / 255, abs_tol=1e-6)
    assert a == 1.0
    # short form expands
    assert approx(theme.hex_to_rgba("#0ff")[:3], (0.0, 1.0, 1.0))


def test_cyan_ramp_matches_classic_arwes():
    # i=0 -> #0ff, i=1 -> #0cc, i=2 -> #099
    assert approx(theme.cyan_ramp(0)[:3], (0.0, 1.0, 1.0))
    assert approx(theme.cyan_ramp(1)[:3], (0.0, 0.8, 0.8))
    assert approx(theme.cyan_ramp(2)[:3], (0.0, 0.6, 0.6))


def test_theme_defaults():
    t = Theme()
    assert t.stroke == (0.0, 1.0, 1.0, 1.0)
    assert t.duration_enter == 0.4
    assert t.stagger == 0.04
    assert approx(t.base[:3], (17 / 255, 17 / 255, 17 / 255))


def test_make_theme_presets_build():
    from arcv.theme import make_theme, THEME_PRESETS

    for name in THEME_PRESETS:
        t = make_theme(name)
        assert len(t.stroke) == 4
        assert all(0.0 <= c <= 1.0 for c in t.stroke)


def test_amber_is_warm_and_overrides_apply():
    from arcv.theme import make_theme

    t = make_theme("amber", bloom_intensity=2.5)
    r, g, b, _ = t.stroke
    assert r > b  # warm hue: red channel dominates blue
    assert t.bloom_intensity == 2.5
