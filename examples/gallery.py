"""Render showcase contact sheets: the six frame styles and the theme presets.

    python examples/gallery.py --out docs/media
"""

from __future__ import annotations

import argparse
import os
import sys

import cv2
import moderngl
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))

from arcv.scene import Scene  # noqa: E402
from arcv.theme import make_theme, THEME_PRESETS  # noqa: E402
from arcv.vision.types import Detection, DetectionFrame  # noqa: E402
from arcv.passes.base import Target  # noqa: E402
from arcv.components.frames import FRAME_STYLES  # noqa: E402

from _demo_scene import synthetic_frame  # noqa: E402

W, H = 480, 270


def _dets(w, h):
    edges = np.zeros((h, w), np.uint8)
    edges[::10, :] = 255
    edges[:, ::10] = 255
    boxes = [
        Detection(0.36, 0.55, 0.14, 0.22, 0.98, "TGT-00", "face", 0),
        Detection(0.74, 0.40, 0.10, 0.13, 0.80, "OBJ-01", "object", 1),
    ]
    return DetectionFrame(boxes=boxes, edges=edges, frame_size=(w, h), primary=0)


def _tile(ctx, label, theme, frame_style):
    scene = Scene(ctx, (W, H), theme=theme, frame_style=frame_style, backgrounds=("gridlines",))
    out = Target(ctx, (W, H), 4, "f1")
    for i in range(45):
        scene.submit(synthetic_frame(W, H, i * 0.033), _dets(W, H))
        scene.render(i * 0.033, target=out.fbo)
    img = cv2.cvtColor(scene.read_pixels(out.fbo), cv2.COLOR_RGB2BGR)
    cv2.putText(img, label, (10, H - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(_HERE, "..", "docs", "media"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    ctx = moderngl.create_standalone_context(require=330)

    styles = list(FRAME_STYLES)
    tiles = [_tile(ctx, s.upper(), make_theme("cyan"), s) for s in styles]
    sheet = np.vstack([np.hstack(tiles[0:3]), np.hstack(tiles[3:6])])
    cv2.imwrite(os.path.join(args.out, "frames.png"), sheet)
    print("saved frames.png", sheet.shape)

    names = list(THEME_PRESETS)
    tiles = [_tile(ctx, n.upper(), make_theme(n), "nefrex") for n in names]
    sheet = np.vstack([np.hstack(tiles[0:3]), np.hstack(tiles[3:6])])
    cv2.imwrite(os.path.join(args.out, "themes.png"), sheet)
    print("saved themes.png", sheet.shape)


if __name__ == "__main__":
    main()
