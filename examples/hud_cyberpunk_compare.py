"""Recreate the Cyberpunk-2077 scanner HUD with BOTH backends, side by side.

The SAME layout (cyberpunk_layout.build) is drawn through:
  left  = OpenCV (CPU primitives + GaussianBlur glow)
  right = ARCV   (GPU vector/text batches + HDR ping-pong bloom)

    python examples/hud_cyberpunk_compare.py                 # -> window
    python examples/hud_cyberpunk_compare.py --save out.png
"""

from __future__ import annotations

import argparse
import math
import os
import sys

import cv2
import moderngl
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))

from arcv.overlay import Overlay  # noqa: E402
from arcv.theme import make_theme  # noqa: E402
from arcv.passes.base import Target  # noqa: E402

import cyberpunk_layout as layout  # noqa: E402
from _hud_adapters import ArcvAdapter, OpenCVAdapter  # noqa: E402
from _cyber_cues import BOOT_CUES  # noqa: E402


def render_arcv(ctx, w, h, t):
    theme = make_theme("green", bloom_intensity=1.8, bloom_threshold=0.22,
                       exposure=1.9, scanline_strength=0.09, scanline_count=h * 0.9)
    ov = Overlay(ctx, (w, h), theme=theme, base_color=(0.015, 0.05, 0.035, 1.0))
    out = Target(ctx, (w, h), 4, "f1")
    ov.begin()
    layout.build(ArcvAdapter(ov), w, h, t)
    ov.render(t, target=out.fbo)
    rgb = ov.read_pixels(out.fbo)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _scanline_mask(h, w):
    y = np.arange(h, dtype=np.float32)
    band = 0.5 + 0.5 * np.sin(y / h * (h * 0.9) * math.pi / h * 2.0)
    return (1.0 - 0.10 * (1.0 - band)).astype(np.float32)[:, None, None]


def render_opencv(w, h, t):
    base = np.zeros((h, w, 3), np.uint8)
    base[:] = (12, 26, 16)  # dark teal BGR
    overlay = np.zeros((h, w, 3), np.uint8)
    layout.build(OpenCVAdapter(overlay), w, h, t)
    glow = cv2.GaussianBlur(overlay, (0, 0), 5.0)
    out = cv2.add(base, overlay)
    out = cv2.add(out, (glow.astype(np.float32) * 1.4).clip(0, 255).astype(np.uint8))
    out = (out.astype(np.float32) * _scanline_mask(h, w)).clip(0, 255).astype(np.uint8)
    return out


def _tag(img, text, x):
    cv2.putText(img, text, (x, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, (x, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)


def compose(ocv, arcv, w, h):
    combo = np.hstack([ocv, arcv])
    cv2.line(combo, (w, 0), (w, h), (60, 60, 60), 1)
    _tag(combo, "OpenCV (CPU)", 12)
    _tag(combo, "ARCV (GPU)", w + 12)
    return combo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", default="980x610", help="WxH per half")
    ap.add_argument("--save", default=None)
    ap.add_argument("--time", type=float, default=3.2)
    ap.add_argument("--sound", action="store_true", help="play synthesized bleeps live")
    args = ap.parse_args()
    w, h = (int(v) for v in args.size.lower().split("x"))

    ctx = moderngl.create_standalone_context(require=330)
    print(f"[hud] renderer={ctx.info['GL_RENDERER']} size={w}x{h}")

    if args.save:
        ocv = render_opencv(w, h, args.time)
        arcv = render_arcv(ctx, w, h, args.time)
        cv2.imwrite(args.save, compose(ocv, arcv, w, h))
        print(f"[hud] saved {args.save}")
        return

    sched = None
    if args.sound:
        from arcv.audio import Bleeps, CueScheduler, arwes_available
        src = "arwes" if arwes_available() else "synth"
        print(f"[hud] sound source: {src}")
        sched = CueScheduler(Bleeps(volume=0.6, source=src), BOOT_CUES)

    import time as _time
    t0 = _time.perf_counter()
    print("[hud] press Q or ESC to quit" + (" (sound on)" if args.sound else ""))
    while True:
        t = _time.perf_counter() - t0
        if sched is not None:
            sched.update(t)
        ocv = render_opencv(w, h, t)
        arcv = render_arcv(ctx, w, h, t)
        cv2.imshow("Cyberpunk HUD - OpenCV vs ARCV", compose(ocv, arcv, w, h))
        if (cv2.waitKey(1) & 0xFF) in (27, ord("q")):
            break
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
