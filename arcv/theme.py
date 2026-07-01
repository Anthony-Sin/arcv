"""Theme / palette — a small port of the Arwes ``createThemeColor`` idea.

Arwes builds palettes procedurally: ``createThemeColor(fn)`` where ``fn(i)``
returns an HSL triple and ``i`` is a lightness ramp index (0 = light,
higher = darker). We reproduce that, then expose the classic signature
palette (the glowing cyan-on-#111 look ARCV is built around) as tokens.

Colors are returned as ``(r, g, b, a)`` floats in ``[0, 1]`` so they drop
straight into GLSL uniforms.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Tuple

RGBA = Tuple[float, float, float, float]
RGB = Tuple[float, float, float]


def hsl_to_rgb(h: float, s: float, l: float) -> RGB:
    """Convert HSL to RGB.

    ``h`` is in degrees [0, 360); ``s`` and ``l`` are in [0, 1].
    Returns ``(r, g, b)`` in [0, 1].
    """
    h = (h % 360.0) / 360.0
    if s == 0.0:
        return (l, l, l)

    def hue(p: float, q: float, t: float) -> float:
        if t < 0.0:
            t += 1.0
        if t > 1.0:
            t -= 1.0
        if t < 1.0 / 6.0:
            return p + (q - p) * 6.0 * t
        if t < 1.0 / 2.0:
            return q
        if t < 2.0 / 3.0:
            return p + (q - p) * (2.0 / 3.0 - t) * 6.0
        return p

    q = l * (1.0 + s) if l < 0.5 else l + s - l * s
    p = 2.0 * l - q
    r = hue(p, q, h + 1.0 / 3.0)
    g = hue(p, q, h)
    b = hue(p, q, h - 1.0 / 3.0)
    return (r, g, b)


def hex_to_rgba(value: str, alpha: float = 1.0) -> RGBA:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    r = int(value[0:2], 16) / 255.0
    g = int(value[2:4], 16) / 255.0
    b = int(value[4:6], 16) / 255.0
    return (r, g, b, alpha)


def create_theme_color(fn: Callable[[int], Tuple[float, float, float]]):
    """Mirror Arwes ``createThemeColor``.

    ``fn(i)`` returns ``(hue_deg, saturation_pct, lightness_pct)``.
    The returned callable maps an index to an ``(r, g, b, a)`` tuple.
    """

    def color(index: int, alpha: float = 1.0) -> RGBA:
        h, s_pct, l_pct = fn(index)
        r, g, b = hsl_to_rgb(h, s_pct / 100.0, l_pct / 100.0)
        return (r, g, b, alpha)

    return color


# The iconic Arwes ramp: hsl(180, 100%, 50% - 10%*i)  ->  #0ff, #0cc, #099, #066 ...
cyan_ramp = create_theme_color(lambda i: (180.0, 100.0, 50.0 - i * 10.0))
# Lighter "glow" tints above index 0: #3ff, #6ff, #9ff ...
cyan_glow = create_theme_color(lambda i: (180.0, 100.0, 50.0 + i * 10.0))


def _hsl(h: float, s: float, l: float, a: float = 1.0) -> RGBA:
    r, g, b = hsl_to_rgb(h, s / 100.0, l / 100.0)
    return (r, g, b, a)


@dataclass
class Theme:
    """A configurable theme. Defaults reproduce the classic Arwes neon look.

    Use :func:`make_theme` for hue-based presets (cyan/amber/red/green/...).
    """

    # Hue (degrees) the ramp/glow_tint derive from.
    hue: float = 180.0
    saturation: float = 100.0
    # Primary stroke / text color (pure cyan).
    stroke: RGBA = (0.0, 1.0, 1.0, 1.0)
    # Panel/frame fill color, used at low opacity.
    fill: RGBA = field(default_factory=lambda: (0.125, 0.875, 0.875, 1.0))
    fill_opacity: float = 0.10
    # Dark scene base (#111).
    base: RGBA = field(default_factory=lambda: hex_to_rgba("#111111"))
    # Bright bloom core tint (#6ff).
    glow: RGBA = field(default_factory=lambda: hex_to_rgba("#66ffff"))

    # Animation defaults (seconds) — match Arwes ANIMATOR_DEFAULT_DURATION.
    duration_enter: float = 0.4
    duration_exit: float = 0.4
    stagger: float = 0.04

    # Bloom controls.
    bloom_threshold: float = 0.35
    bloom_intensity: float = 1.6
    bloom_iterations: int = 6

    # Composite exposure (higher = brighter before tone-map).
    exposure: float = 1.25

    # Scanline controls.
    scanline_count: float = 240.0
    scanline_strength: float = 0.12
    scanline_sweep_speed: float = 0.15
    sweep_strength: float = 0.12  # moving sweep band (set 0 to disable)

    def ramp(self, index: int, alpha: float = 1.0) -> RGBA:
        return _hsl(self.hue, self.saturation, 50.0 - index * 10.0, alpha)

    def glow_tint(self, index: int, alpha: float = 1.0) -> RGBA:
        return _hsl(self.hue, self.saturation, 50.0 + index * 10.0, alpha)


# Hue-based presets. Each maps to make_theme(**preset).
THEME_PRESETS = {
    "cyan": dict(hue=180.0, base="#111111"),
    "amber": dict(hue=38.0, base="#140f08"),
    "red": dict(hue=2.0, base="#160a0a"),
    "green": dict(hue=135.0, base="#0a140d"),
    "magenta": dict(hue=305.0, base="#140a14"),
    "ice": dict(hue=200.0, saturation=72.0, base="#0d1114"),
}


def make_theme(name: str = "cyan", **overrides) -> Theme:
    """Build a :class:`Theme` from a hue preset.

    ``make_theme("amber")`` gives a gold HUD; ``make_theme("red", bloom_intensity=2.2)``
    overrides any Theme field. Names: cyan, amber, red, green, magenta, ice.
    """
    cfg = dict(THEME_PRESETS.get(name, THEME_PRESETS["cyan"]))
    cfg.update(overrides)
    hue = cfg.pop("hue", 180.0)
    sat = cfg.pop("saturation", 100.0)
    base_hex = cfg.pop("base", "#111111")
    return Theme(
        hue=hue,
        saturation=sat,
        stroke=_hsl(hue, sat, 50.0),
        fill=_hsl(hue, sat * 0.75, 50.0),
        base=hex_to_rgba(base_hex) if isinstance(base_hex, str) else base_hex,
        glow=_hsl(hue, sat, 66.0),
        **cfg,
    )
