"""Autonomous quadruped follow-HUD (ARCV only).

Renders the robot's tracking overlay with a scripted story: boot/assemble →
LOCKED follow → TARGET LOST (red alert + searching) → REACQUIRE. Writes a GIF,
a timeline contact sheet, and an MP4 with synchronized bleeps; or runs live.

    python examples/robot_hud.py                 # gif + timeline + mp4
    python examples/robot_hud.py --live --sound  # live window with bleeps
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time

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

import robot_hud_layout as layout  # noqa: E402
from _hud_adapters import ArcvAdapter  # noqa: E402

W, H = 1000, 600
DUR = 13.0

# bleep cues timed to the story (see robot_hud_layout timeline)
CUES = [
    (0.0, "assemble"), (0.12, "decipher"), (0.20, "assemble"), (0.30, "type"),
    (0.50, "type"), (0.70, "panel"), (0.90, "type"), (1.00, "panel"),
    (1.20, "action"), (1.32, "action"), (1.44, "action"), (1.56, "action"),
    (1.30, "panel"), (1.40, "scan"),
    (2.20, "lock"),                                   # target locked
    (3.2, "scan"), (4.2, "scan"), (5.2, "scan"),      # idle follow
    (6.00, "error"), (6.15, "alert"),                 # TARGET LOST
    (6.6, "scan"), (7.2, "scan"), (7.8, "scan"), (8.4, "scan"), (9.0, "scan"),
    (9.40, "lock"),                                   # reacquired
    (10.6, "scan"), (11.8, "scan"),
]


class R:
    def __init__(self, ctx):
        theme = make_theme("cyan", bloom_intensity=1.6, bloom_threshold=0.24,
                           exposure=1.6, scanline_strength=0.0, sweep_strength=0.0)
        theme.glow = (0.80, 0.95, 1.0)  # near-white bloom so red alerts stay red
        self.ov = Overlay(ctx, (W, H), theme=theme, base_color=(0.01, 0.03, 0.05, 1.0),
                          grid=True, grid_cell=46.0, grid_alpha=0.09)
        self.out = Target(ctx, (W, H), 4, "f1")

    def frame(self, t):
        self.ov.begin()
        layout.build(ArcvAdapter(self.ov), W, H, t)
        self.ov.render(t, target=self.out.fbo)
        return cv2.cvtColor(self.ov.read_pixels(self.out.fbo), cv2.COLOR_RGB2BGR)


def export_mp4(frames, fps, dur, path, volume, source):
    h, w = frames[0].shape[:2]
    tv = path + ".v.mp4"
    vw = cv2.VideoWriter(tv, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for f in frames:
        vw.write(f)
    vw.release()
    ta = path + ".a.wav"
    save_wav(ta, render_track(CUES, dur, volume, source=source))
    ff = shutil.which("ffmpeg")
    if ff:
        r = subprocess.run([ff, "-y", "-i", tv, "-i", ta, "-c:v", "libx264",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", path],
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if r.returncode == 0:
            os.remove(tv)
            os.remove(ta)
            print(f"[robot] saved {path} (with audio)")
            return
        print("[robot] ffmpeg failed:\n" + r.stderr.decode(errors='ignore')[-300:])
    print(f"[robot] kept {tv} + {ta}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--sound", action="store_true")
    ap.add_argument("--gif", default=os.path.join(_HERE, "..", "robot_hud.gif"))
    ap.add_argument("--sheet", default=os.path.join(_HERE, "..", "robot_timeline.png"))
    ap.add_argument("--mp4", default=os.path.join(_HERE, "..", "robot_hud.mp4"))
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--volume", type=float, default=0.6)
    args = ap.parse_args()

    ctx = moderngl.create_standalone_context(require=330)
    r = R(ctx)
    print(f"[robot] renderer={ctx.info['GL_RENDERER']}")

    if args.live:
        sched = None
        if args.sound:
            from arcv.audio import Bleeps, CueScheduler, arwes_available
            src = "arwes" if arwes_available() else "synth"
            print(f"[robot] sound: {src}")
            sched = CueScheduler(Bleeps(volume=args.volume, source=src), CUES)
        t0 = time.perf_counter()
        print("[robot] press Q or ESC to quit")
        while True:
            t = time.perf_counter() - t0
            if sched is not None:
                sched.update(t)
            cv2.imshow("ARCV — Quadruped Follow HUD", r.frame(t))
            if (cv2.waitKey(1) & 0xFF) in (27, ord("q")):
                break
        cv2.destroyAllWindows()
        return

    n = int(DUR * args.fps)
    frames = [r.frame(i / args.fps) for i in range(n)]
    print(f"[robot] rendered {len(frames)} frames")

    step = max(1, args.fps // 16)
    imgs = [Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)) for f in frames[::step]]
    imgs[0].save(args.gif, save_all=True, append_images=imgs[1:],
                 duration=int(1000 / args.fps * step), loop=0, optimize=True)
    print(f"[robot] saved {args.gif}")

    picks = [int(x * args.fps) for x in (1.0, 3.5, 7.0, 9.6, 11.5)]
    cv2.imwrite(args.sheet, np.vstack([frames[min(i, n - 1)] for i in picks]))
    print(f"[robot] saved {args.sheet}")

    src = "arwes"
    try:
        from arcv.audio import arwes_available
        src = "arwes" if arwes_available() else "synth"
    except Exception:  # noqa: BLE001
        src = "synth"
    export_mp4(frames, args.fps, DUR, args.mp4, args.volume, src)


if __name__ == "__main__":
    main()
