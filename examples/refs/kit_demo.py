"""Visual contact sheet for arcv.overlay.hud_kit.

Lays out every reusable HUD kit primitive on a labeled grid and renders it
through the shared reference harness (glow mode over a dark base), writing
examples/refs/gallery/_kit_demo.png. This is the doc screenshot for the kit.

    python examples/refs/kit_demo.py
"""

from __future__ import annotations

import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from _ref_render import render_png  # noqa: E402
from arcv.overlay import hud_kit  # noqa: E402
from arcv.theme import make_theme  # noqa: E402

# ------------------------------------------------------------------ palette
CY = (0.55, 0.9, 1.0, 1.0)       # cyan primary
CY_T = (0.35, 0.7, 1.0, 0.26)    # translucent (sweep wedge)
LABEL = (0.75, 0.85, 0.95, 1.0)
TITLE = (0.9, 0.97, 1.0, 1.0)
GRID = (0.30, 0.42, 0.55, 0.35)

# grid layout: 5 columns x 4 rows of cells, each hosting one primitive
COLS = 5
ROWS = 4


def build(d, W, H, t=0.0):
    d.text("arcv.overlay.hud_kit", W * 0.5, 14, 22, TITLE, align="center")
    d.text("reusable HUD primitives", W * 0.5, 40, 11, LABEL, align="center")

    m = 40                       # outer margin
    top = 70                     # below the title
    cw = (W - 2 * m) / COLS
    ch = (H - top - m) / ROWS

    # each entry: (label, draw-fn taking (d, cell-center-x, cell-center-y, cell-w, cell-h))
    items = [
        ("warning_triangle", lambda d, x, y, w, h: hud_kit.warning_triangle(d, x, y, min(w, h) * 0.30, CY, width=2.0)),
        ("biohazard",        lambda d, x, y, w, h: hud_kit.biohazard(d, x, y, min(w, h) * 0.30, CY)),
        ("radiation_trefoil", lambda d, x, y, w, h: hud_kit.radiation_trefoil(d, x, y, min(w, h) * 0.30, CY)),
        ("hexagon",          lambda d, x, y, w, h: hud_kit.hexagon(d, x, y, min(w, h) * 0.30, CY, width=2.0, fill=(0.4, 0.7, 1.0, 0.08))),
        ("hex_badge",        lambda d, x, y, w, h: hud_kit.hex_badge(d, x, y, min(w, h) * 0.30, "84", CY, width=2.0)),

        ("crescent",         lambda d, x, y, w, h: hud_kit.crescent(d, x, y, min(w, h) * 0.30, CY, width=2.0)),
        ("hazard_stripes",   lambda d, x, y, w, h: hud_kit.hazard_stripes(d, x - w * 0.36, y - 12, x + w * 0.36, y + 12, CY, gap=12.0, width=5.0)),
        ("barcode",          lambda d, x, y, w, h: hud_kit.barcode(d, x - w * 0.34, y - 22, w * 0.68, 44, CY, seed=5)),
        ("waveform",         lambda d, x, y, w, h: hud_kit.waveform(d, x - w * 0.36, y - 22, w * 0.72, 44, CY, bars=40, seed=2)),
        ("spectrum_bar",     lambda d, x, y, w, h: hud_kit.spectrum_bar(d, x, y - h * 0.30, 12, h * 0.6, segments=7, vertical=True)),

        ("segmented_bar",    lambda d, x, y, w, h: hud_kit.segmented_bar(d, x - w * 0.36, y - 7, w * 0.72, 14, 10, CY, filled=(0, 2, 3, 6))),
        ("tick_ring",        lambda d, x, y, w, h: hud_kit.tick_ring(d, x, y, min(w, h) * 0.34, 48, min(w, h) * 0.06, CY, width=1.0, major_every=6, major_length=min(w, h) * 0.12)),
        ("radial_gauge",     lambda d, x, y, w, h: hud_kit.radial_gauge(d, x, y, min(w, h) * 0.34, 0.62, CY, needle_deg=58)),
        ("sweep_wedge",      lambda d, x, y, w, h: (hud_kit.tick_ring(d, x, y, min(w, h) * 0.34, 36, min(w, h) * 0.05, GRID), hud_kit.sweep_wedge(d, x, y, min(w, h) * 0.34, math.radians(18), math.radians(92), CY_T))),
        ("contour_map",      lambda d, x, y, w, h: hud_kit.contour_map(d, x, y, min(w, h) * 0.40, CY, seed=0, systems=3)),

        ("wireframe_sphere", lambda d, x, y, w, h: hud_kit.wireframe_sphere(d, x, y, min(w, h) * 0.34, CY, vortex=False)),
        ("sphere (vortex)",  lambda d, x, y, w, h: hud_kit.wireframe_sphere(d, x, y, min(w, h) * 0.34, CY, vortex=True)),
        ("wireframe_terrain", lambda d, x, y, w, h: hud_kit.wireframe_terrain(d, x - w * 0.40, y - h * 0.30, w * 0.80, h * 0.62, CY, cols=34, rows=22, seed=1)),
        ("face_mesh",        lambda d, x, y, w, h: hud_kit.face_mesh(d, x, y - h * 0.02, min(w, h) * 0.66, min(w, h) * 0.92, CY)),
    ]

    for idx, (label, fn) in enumerate(items):
        col = idx % COLS
        row = idx // COLS
        x0 = m + col * cw
        y0 = top + row * ch
        cx = x0 + cw * 0.5
        cy = y0 + ch * 0.5 + 4      # nudge down to leave room for label
        # faint cell frame
        d.rect(x0 + 4, y0 + 4, x0 + cw - 4, y0 + ch - 4, GRID, 1.0)
        # label at the top-left of the cell
        d.text(label, x0 + 10, y0 + 8, 9.5, LABEL, align="left")
        fn(d, cx, cy, cw - 24, ch - 40)


def main():
    theme = make_theme("ice", bloom_intensity=0.7, bloom_threshold=0.55,
                       exposure=1.35, scanline_strength=0.0, sweep_strength=0.0)
    out = render_png(build, "gallery/_kit_demo.png", size=(1280, 800), mode="glow",
                     theme=theme, base_color=(0.02, 0.03, 0.05, 1.0))
    import shutil
    docs = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "docs", "media")
    os.makedirs(docs, exist_ok=True)
    shutil.copyfile(out, os.path.join(docs, "hud_kit_demo.png"))  # committed copy (docs/media is git-tracked)
    print("wrote", out)
    return out


if __name__ == "__main__":
    main()
