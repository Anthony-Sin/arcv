"""ARCV boot sequence — OLD motion vs NEW anime.js model, side-by-side.

The SAME target-scan HUD assembles two ways so you can see exactly what the new
motion model adds. LEFT boots with the old Sequencer (uniform stagger, arc-length
reveal, whole-string decipher, one font); RIGHT boots with the new Timeline +
grid stagger + per-char/word split-text + spring/elastic overshoot + shape morph +
a motion-path sweep, in MULTIPLE fonts. Deterministic in t — the same build drives
the still, the looping GIF, and the window.

    python examples/anime_boot.py            # PNG still + looping GIF -> docs/media
    python examples/anime_boot.py --live      # animated window
"""

from __future__ import annotations

import argparse
import os
import sys

import cv2
import moderngl
import numpy as np
from PIL import Image

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))

from arcv.overlay import FlatOverlay, Draw, fonts  # noqa: E402

import anime_boot_layout as layout  # noqa: E402

W, H = 1120, 560
DUR = 5.5

OLD_C = (0.35, 0.85, 0.95, 1.0)
NEW_C = (0.3, 0.95, 1.0, 1.0)
DIVID = (0.25, 0.5, 0.6, 0.7)


def synthetic_feed(t):
    f = np.zeros((H, W, 3), np.uint8)
    grad = np.linspace(14, 26, H, dtype=np.uint8)
    f[:] = grad[:, None, None]
    f[:, :, 0] = np.clip(f[:, :, 0].astype(np.int16) + 8, 0, 255)
    step = 44
    off = int((t * 16) % step)
    f[off::step, :] = np.clip(f[off::step, :].astype(np.int16) + 5, 0, 255).astype(np.uint8)
    return f


def grade(frame):
    f = frame.astype(np.float32)
    gray = f @ np.array([0.114, 0.587, 0.299], np.float32)
    f = f * 0.5 + gray[..., None] * 0.25
    return np.clip(f * 0.8, 0, 255).astype(np.uint8)


class Renderer:
    def __init__(self, ctx):
        self.ov = FlatOverlay(ctx, (W, H), base_color=(0.02, 0.02, 0.04, 1.0))
        self.d = Draw(self.ov)
        fonts.register_hud_fonts(self.d, size=40)  # display / ocr / din / term

    def build(self, t):
        d = self.d
        tb = t % DUR
        # header
        d.text("BEFORE", 20, 8, 16, OLD_C, font="display")
        d.text("Sequencer  reveal  whole-string decipher  1 font", 108, 12, 11, (0.5, 0.7, 0.78, 1))
        d.text("AFTER", W // 2 + 16, 8, 16, NEW_C, font="display")
        d.text("Timeline  grid-stagger  split-text  spring  morph  multi-font",
               W // 2 + 92, 12, 11, (0.6, 0.85, 0.9, 1))
        d.text(f"t={tb:04.1f}", W - 78, 12, 12, (0.6, 0.8, 0.85, 1))
        d.line(0, 34, W, 34, DIVID, 1.0)
        d.line(W // 2, 34, W // 2, H, DIVID, 1.0)
        # halves
        layout.build_old(d, (16, 40, W // 2 - 10, H - 12), tb)
        layout.build_new(d, (W // 2 + 10, 40, W - 16, H - 12), tb)

    def frame(self, t):
        self.ov.begin()
        self.build(t)
        self.ov.render(cam_frame=grade(synthetic_feed(t % DUR)))
        return cv2.cvtColor(self.ov.read_pixels(), cv2.COLOR_RGB2BGR)


def run_live(r):
    import time
    t0 = time.perf_counter()
    print("[anime-boot] press Q or ESC to quit")
    while True:
        cv2.imshow("ARCV boot — old vs new motion", r.frame(time.perf_counter() - t0))
        if (cv2.waitKey(1) & 0xFF) in (27, ord("q")):
            break
    cv2.destroyAllWindows()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--png", default=os.path.join(_HERE, "..", "docs", "media", "anime_boot.png"))
    ap.add_argument("--gif", default=os.path.join(_HERE, "..", "docs", "media", "anime_boot.gif"))
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--still-at", type=float, default=2.0)
    args = ap.parse_args()

    ctx = moderngl.create_standalone_context(require=330)
    r = Renderer(ctx)
    print(f"[anime-boot] renderer={ctx.info['GL_RENDERER']}")

    if args.live:
        run_live(r)
        return

    os.makedirs(os.path.dirname(os.path.abspath(args.png)), exist_ok=True)
    cv2.imwrite(args.png, r.frame(args.still_at))
    print(f"[anime-boot] saved {args.png}")

    n = int(DUR * args.fps)
    frames = [r.frame(i / args.fps) for i in range(n)]
    print(f"[anime-boot] rendered {len(frames)} frames")
    step = max(1, args.fps // 12)
    gw = 960
    gh = int(gw * H / W)

    def _gif(f):
        rgb = cv2.cvtColor(cv2.resize(f, (gw, gh)), cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb).quantize(colors=128, method=Image.FASTOCTREE)

    imgs = [_gif(f) for f in frames[::step]]
    imgs[0].save(args.gif, save_all=True, append_images=imgs[1:],
                 duration=int(1000 / args.fps * step), loop=0, optimize=True)
    print(f"[anime-boot] saved {args.gif}")


if __name__ == "__main__":
    main()
