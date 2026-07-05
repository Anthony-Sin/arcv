"""ARCV × anime.js — a native recreation of anime.js's iconic demos, rendered on
the ARCV GPU pipeline (Draw over FlatOverlay) *over the OpenCV feed*.

One looping gallery of: staggered grid ripple, SVG line draw-on, shape morph,
motion-path follower (rotating to face travel), split-text stagger (char/word/
line), a layered/labelled Timeline sequence, overshoot/settle (back/elastic/
spring), loop/alternate/reversed, the ScrollObserver + Draggable adapters, and an
easing showcase racing every easing (incl. spring/elastic/bounce). Everything is
deterministic in ``t`` — the same build drives the still, the GIF and the window.

    python examples/anime_gallery.py                 # PNG still + looping GIF -> docs/media
    python examples/anime_gallery.py --live           # animated window
    python examples/anime_gallery.py --live --camera 0 # over a real webcam feed

The default headless run draws over a dark synthetic "feed" so it works with no
webcam; ``--camera N`` composites the gallery over real OpenCV frames instead.
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

from arcv.overlay import FlatOverlay, Draw  # noqa: E402

import anime_gallery_layout as layout  # noqa: E402

W, H = 1200, 720
DUR = layout.DUR


def synthetic_feed(t: float) -> np.ndarray:
    """A dark, faintly-moving backdrop so the neon gallery reads as a live feed."""
    f = np.zeros((H, W, 3), np.uint8)
    grad = np.linspace(16, 30, H, dtype=np.uint8)
    f[:] = grad[:, None, None]
    f[:, :, 0] = np.clip(f[:, :, 0].astype(np.int16) + 10, 0, 255)  # cool blue cast
    step = 46
    off = int((t * 18) % step)
    f[:, off::step] = np.clip(f[:, off::step].astype(np.int16) + 6, 0, 255).astype(np.uint8)
    f[off::step, :] = np.clip(f[off::step, :].astype(np.int16) + 6, 0, 255).astype(np.uint8)
    return f


def grade_cam(frame: np.ndarray) -> np.ndarray:
    """Darken + desaturate the feed so the bright HUD pops over it."""
    f = frame.astype(np.float32)
    gray = f @ np.array([0.114, 0.587, 0.299], np.float32)  # BGR luma
    f = f * 0.5 + gray[..., None] * 0.5 * 0.5
    return np.clip(f * 0.85, 0, 255).astype(np.uint8)


class Renderer:
    def __init__(self, ctx):
        self.ov = FlatOverlay(ctx, (W, H), base_color=(0.02, 0.02, 0.04, 1.0))
        self.d = Draw(self.ov)

    def frame(self, t, cam=None):
        scene = synthetic_feed(t) if cam is None else cam
        self.ov.begin()
        layout.build(self.d, W, H, t)
        self.ov.render(cam_frame=grade_cam(scene))
        return cv2.cvtColor(self.ov.read_pixels(), cv2.COLOR_RGB2BGR)


def run_live(r, args):
    import time
    src = None
    if args.camera is not None:
        from arcv.capture import CameraSource
        try:
            src = CameraSource(index=args.camera, width=W, height=H).start()
            print(f"[anime-gallery] camera {args.camera}")
        except Exception as e:  # noqa: BLE001
            print(f"[anime-gallery] camera unavailable ({e}); synthetic feed")
            src = None
    t0 = time.perf_counter()
    print("[anime-gallery] press Q or ESC to quit")
    while True:
        t = time.perf_counter() - t0
        cam = None
        if src is not None:
            frame = src.read()
            if frame is not None:
                cam = cv2.resize(frame, (W, H))
        cv2.imshow("ARCV x anime.js — motion gallery", r.frame(t, cam))
        if (cv2.waitKey(1) & 0xFF) in (27, ord("q")):
            break
    if src is not None:
        src.release()
    cv2.destroyAllWindows()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="show a window instead of exporting")
    ap.add_argument("--camera", type=int, default=None, help="composite over a real webcam (live)")
    ap.add_argument("--png", default=os.path.join(_HERE, "..", "docs", "media", "anime_gallery.png"))
    ap.add_argument("--gif", default=os.path.join(_HERE, "..", "docs", "media", "anime_gallery.gif"))
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--still-at", type=float, default=1.6, help="time of the PNG still")
    args = ap.parse_args()

    ctx = moderngl.create_standalone_context(require=330)
    r = Renderer(ctx)
    print(f"[anime-gallery] renderer={ctx.info['GL_RENDERER']}")

    if args.live:
        run_live(r, args)
        return

    os.makedirs(os.path.dirname(os.path.abspath(args.png)), exist_ok=True)

    # PNG still
    cv2.imwrite(args.png, r.frame(args.still_at))
    print(f"[anime-gallery] saved {args.png}")

    # looping GIF
    n = int(DUR * args.fps)
    frames = [r.frame(i / args.fps) for i in range(n)]
    print(f"[anime-gallery] rendered {len(frames)} frames")
    step = max(1, args.fps // 12)
    gw = 900
    gh = int(gw * H / W)

    def _gif_frame(f):
        rgb = cv2.cvtColor(cv2.resize(f, (gw, gh)), cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb).quantize(colors=128, method=Image.FASTOCTREE)

    imgs = [_gif_frame(f) for f in frames[::step]]
    imgs[0].save(args.gif, save_all=True, append_images=imgs[1:],
                 duration=int(1000 / args.fps * step), loop=0, optimize=True)
    print(f"[anime-gallery] saved {args.gif}")


if __name__ == "__main__":
    main()
