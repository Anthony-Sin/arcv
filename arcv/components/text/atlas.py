"""Monospace glyph atlas built with Pillow.

Produces a single-row coverage atlas (one cell per character) plus metrics, with
no GPU dependency so it can be built and inspected on its own. The DecipherText
component uploads ``image`` as a single-channel texture.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Includes the Arwes decipher symbol flavor plus what HUD labels need.
CHARSET = (
    " ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    "-.:>/!?#%&()=@$+*|',·°•"
)

# Bundled HUD font (Share Tech Mono, OFL) takes priority over system fonts.
_FONTS_DIR = Path(__file__).resolve().parents[2] / "resources" / "fonts"
_FONT_CANDIDATES = [
    str(_FONTS_DIR / "ShareTechMono-Regular.ttf"),
    "C:/Windows/Fonts/consola.ttf",   # Consolas
    "C:/Windows/Fonts/cour.ttf",      # Courier New
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/Library/Fonts/Menlo.ttc",
]


def _load_font(size: int, font_path: Optional[str] = None) -> ImageFont.FreeTypeFont:
    candidates = ([font_path] if font_path else []) + _FONT_CANDIDATES
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:  # noqa: BLE001
            continue
    return ImageFont.load_default()


class FontAtlas:
    def __init__(self, font_size: int = 42, margin: int = 5, font_path: Optional[str] = None,
                 bold: Optional[int] = None) -> None:
        font = _load_font(font_size, font_path)
        # a small stroke thickens the (light) HUD font so it stays legible when
        # downscaled to small on-screen sizes
        bold = max(1, round(font_size * 0.045)) if bold is None else bold
        ascent, descent = font.getmetrics()
        # Cell sized to the widest advance so glyphs share a baseline and linear
        # filtering can't bleed one glyph into its neighbor.
        try:
            widths = [font.getlength(ch if ch != " " else "M") for ch in CHARSET]
        except Exception:  # noqa: BLE001 - very old Pillow
            widths = [font.getbbox(ch if ch != " " else "M")[2] for ch in CHARSET]
        self.cell_w = int(max(widths)) + margin * 2
        self.cell_h = ascent + descent + margin * 2
        self.margin = margin
        self.n = len(CHARSET)

        atlas_w = self.cell_w * self.n
        atlas_h = self.cell_h
        baseline = margin + ascent
        img = Image.new("L", (atlas_w, atlas_h), 0)
        draw = ImageDraw.Draw(img)
        self._index: Dict[str, int] = {}
        for i, ch in enumerate(CHARSET):
            self._index[ch] = i
            if ch == " ":
                continue
            x = i * self.cell_w + margin
            try:
                draw.text((x, baseline), ch, fill=255, font=font, anchor="ls",
                          stroke_width=bold, stroke_fill=255)
            except Exception:  # noqa: BLE001 - anchor unsupported on old Pillow
                draw.text((x, margin), ch, fill=255, font=font)

        self.image = np.asarray(img, dtype=np.uint8)  # (H, W), top-left origin
        self.atlas_w = atlas_w
        self.atlas_h = atlas_h
        self.aspect = self.cell_w / self.cell_h
        self.scramble_pool: List[str] = [c for c in CHARSET if c not in " "]

    def index(self, ch: str) -> int:
        return self._index.get(ch, 0)

    def u_range(self, ch: str) -> Tuple[float, float]:
        i = self.index(ch)
        # inset by a quarter texel to avoid edge bleed
        eps = 0.25 / self.atlas_w
        u0 = (i * self.cell_w) / self.atlas_w + eps
        u1 = ((i + 1) * self.cell_w) / self.atlas_w - eps
        return u0, u1
