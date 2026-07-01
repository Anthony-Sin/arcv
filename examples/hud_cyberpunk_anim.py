"""Animated boot/loading sequence of the Cyberpunk HUD, OpenCV vs ARCV.

Renders the assemble animation (strokes draw on, text deciphers/types, panels
fade, stagger, loading spinner + analysis bar, then idle motion) and writes:
  - an animated GIF (no audio)
  - a timeline contact sheet
  - an MP4 with SYNTHESIZED BLEEPS muxed in (needs ffmpeg)

    python examples/hud_cyberpunk_anim.py
    python examples/hud_cyberpunk_anim.py --mp4 boot.mp4 --no-gif
"""

from __future__ import annotations

import argparse
import math
import os
import shutil
import subprocess
import sys

import cv2
import moderngl
import numpy as np
from PIL import Image

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))

from arcv.overlay import Overlay  # noqa: E402
from arcv.theme import make_theme  # noqa: E402
from arcv.passes.base import Target  # noqa: E402
from arcv.audio import render_track, save_wav  # noqa: E402

import cyberpunk_layout as layout  # noqa: E402
from _hud_adapters import ArcvAdapter, OpenCVAdapter  # noqa: E402
from _cyber_cues import cues_for  # noqa: E402

W, H = 600, 380


def _scanmask(h, w):
    y = np.arange(h, dtype=np.float32)
    band = 0.5 + 0.5 * np.sin(y / h * (h * 0.9) * math.pi / h * 2.0)
    return (1.0 - 0.10 * (1.0 - band)).astype(np.float32)[:, None, None]


class Renderers:
    def __init__(self, ctx):
        theme = make_theme("green", bloom_intensity=1.8, bloom_threshold=0.22,
                           exposure=1.9, scanline_strength=0.09, scanline_count=H * 0.9)
        self.ov = Overlay(ctx, (W, H), theme=theme, base_color=(0.015, 0.05, 0.035, 1.0))
        self.out = Target(ctx, (W, H), 4, "f1")
        self.base = np.zeros((H, W, 3), np.uint8)
        self.base[:] = (12, 26, 16)
        self.scan = _scanmask(H, W)

    def arcv(self, t):
        self.ov.begin()
        layout.build(ArcvAdapter(self.ov), W, H, t)
        self.ov.render(t, target=self.out.fbo)
        return cv2.cvtColor(self.ov.read_pixels(self.out.fbo), cv2.COLOR_RGB2BGR)

    def opencv(self, t):
        overlay = np.zeros((H, W, 3), np.uint8)
        layout.build(OpenCVAdapter(overlay), W, H, t)
        glow = cv2.GaussianBlur(overlay, (0, 0), 5.0)
        out = cv2.add(self.base, overlay)
        out = cv2.add(out, (glow.astype(np.float32) * 1.4).clip(0, 255).astype(np.uint8))
        return (out.astype(np.float32) * self.scan).clip(0, 255).astype(np.uint8)


def _tag(img, text, x):
    cv2.putText(img, text, (x, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, (x, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)


def compose(r, t):
    ocv, arcv = r.opencv(t), r.arcv(t)
    combo = np.hstack([ocv, arcv])
    cv2.line(combo, (W, 0), (W, H), (60, 60, 60), 1)
    _tag(combo, "OpenCV (CPU)", 10)
    _tag(combo, "ARCV (GPU)", W + 10)
    cv2.putText(combo, "t=%.2fs" % t, (combo.shape[1] - 90, H - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 220, 200), 1, cv2.LINE_AA)
    return combo


def export_mp4(frames, fps, dur, path, volume, source):
    h, w = frames[0].shape[:2]
    tmp_v = path + ".v.mp4"
    vw = cv2.VideoWriter(tmp_v, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for f in frames:
        vw.write(f)
    vw.release()

    tmp_a = path + ".a.wav"
    save_wav(tmp_a, render_track(cues_for(dur), dur, volume, source=source))

    ff = shutil.which("ffmpeg")
    if ff:
        cmd = [ff, "-y", "-i", tmp_v, "-i", tmp_a, "-c:v", "libx264",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", path]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if res.returncode == 0:
            os.remove(tmp_v)
            os.remove(tmp_a)
            print(f"[anim] saved {path} (with audio)")
            return
        print("[anim] ffmpeg mux failed:\n" + res.stderr.decode(errors="ignore")[-400:])
    print(f"[anim] ffmpeg unavailable; kept {tmp_v} + {tmp_a} (mux manually)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gif", default=os.path.join(_HERE, "..", "cyber_boot.gif"))
    ap.add_argument("--sheet", default=os.path.join(_HERE, "..", "cyber_timeline.png"))
    ap.add_argument("--mp4", default=os.path.join(_HERE, "..", "cyber_boot.mp4"))
    ap.add_argument("--no-gif", action="store_true")
    ap.add_argument("--no-mp4", action="store_true")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--dur", type=float, default=4.0)
    ap.add_argument("--volume", type=float, default=0.6)
    ap.add_argument("--sound-source", default="arwes", help="arwes|synth")
    args = ap.parse_args()

    ctx = moderngl.create_standalone_context(require=330)
    r = Renderers(ctx)
    print(f"[anim] renderer={ctx.info['GL_RENDERER']}")

    n = int(args.dur * args.fps)
    frames = [compose(r, i / args.fps) for i in range(n)]
    print(f"[anim] rendered {len(frames)} frames")

    if not args.no_gif:
        step = max(1, args.fps // 18)  # thin frames so the GIF stays small
        imgs = [Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)) for f in frames[::step]]
        imgs[0].save(args.gif, save_all=True, append_images=imgs[1:],
                     duration=int(1000 / args.fps * step), loop=0, optimize=True)
        print(f"[anim] saved {args.gif}")

    picks = [int(t * args.fps) for t in (0.4, 0.8, 1.2, 1.7, 2.3, 3.2)]
    rows = [frames[min(i, n - 1)] for i in picks]
    cv2.imwrite(args.sheet, np.vstack(rows))
    print(f"[anim] saved {args.sheet}")

    if not args.no_mp4:
        export_mp4(frames, args.fps, args.dur, args.mp4, args.volume, args.sound_source)


if __name__ == "__main__":
    main()
