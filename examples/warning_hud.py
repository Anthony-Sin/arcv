"""ARCV — yellow "WARNING // TARGET ACQUISITION" HUD over the OpenCV feed.

A ref1-style (bright-yellow angular panels, black content) computer-vision HUD
rendered OPAQUE over the live camera through :class:`arcv.overlay.FlatOverlay`.
It shows only the useful CV telemetry (status / target count / confidence /
position / distance / fps / signal), boots up with draw-on + decipher/type-on
animation, and plays a LOCKED -> TARGET LOST -> REACQUIRE story with synced
bleeps. All text is Share Tech Mono (the bundled atlas font).

    python examples/warning_hud.py                 # gif + timeline + mp4 (+ stills)
    python examples/warning_hud.py --live           # scripted story in a window
    python examples/warning_hud.py --live --camera 0 --sound   # real webcam + CV + bleeps

The default (headless) run drives a scripted synthetic scene so it works with no
webcam; ``--camera N`` locks the HUD onto real OpenCV detections instead.
"""

from __future__ import annotations

import argparse
import math
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

from arcv.overlay import FlatOverlay  # noqa: E402
from arcv.audio import render_track, save_wav  # noqa: E402

import warning_hud_layout as layout  # noqa: E402
from _hud_adapters import ArcvAdapter  # noqa: E402

W, H = 1200, 720
DUR = layout.DUR

# bleep cues timed to the scripted story (see warning_hud_layout timeline)
CUES = [
    (0.00, "assemble"), (0.15, "decipher"), (0.25, "panel"), (0.40, "type"),
    (0.55, "type"), (0.70, "panel"), (0.85, "type"), (1.00, "panel"),
    (1.20, "action"), (1.35, "action"), (1.50, "action"), (1.65, "action"),
    (0.90, "scan"),
    (layout.T_BOOT, "lock"),                                   # target locked
    (3.4, "scan"), (4.4, "scan"), (5.4, "scan"),               # idle follow
    (layout.T_LOST, "error"), (layout.T_LOST + 0.15, "alert"),  # TARGET LOST
    (6.7, "scan"), (7.3, "scan"), (7.9, "scan"), (8.5, "scan"), (9.1, "scan"),
    (layout.T_REACQ, "lock"),                                  # reacquired
    (10.6, "scan"), (11.9, "scan"),
]


# ------------------------------------------------------------- synthetic scene
def synthetic_scene(t, st) -> np.ndarray:
    """A dark room with a moving 'person' the HUD locks onto (no webcam needed).
    The figure is present while tracked and gone while the target is lost."""
    f = np.zeros((H, W, 3), np.uint8)
    grad = np.linspace(10, 30, H, dtype=np.uint8)
    f[:] = grad[:, None, None]
    # floor line + faint environment blocks
    cv2.line(f, (0, int(H * 0.74)), (W, int(H * 0.74)), (44, 46, 48), 2)
    cv2.rectangle(f, (int(W * 0.30), int(H * 0.60)), (int(W * 0.40), int(H * 0.74)), (36, 40, 42), -1)
    cv2.rectangle(f, (int(W * 0.60), int(H * 0.55)), (int(W * 0.66), int(H * 0.74)), (34, 38, 40), -1)

    if not st.alert:
        vp = layout.VP
        tx = int((vp[0] + (vp[2] - vp[0]) * st.target[0]) * W)
        ty = int((vp[1] + (vp[3] - vp[1]) * st.target[1]) * H)
        bw = int(st.box[0] * (vp[2] - vp[0]) * W)
        bh = int(st.box[1] * (vp[3] - vp[1]) * H)
        skin = (150, 158, 162)
        body = (120, 128, 132)
        cv2.circle(f, (tx, ty - bh + int(bh * 0.35)), int(bw * 0.55), skin, -1)      # head
        cv2.rectangle(f, (tx - bw, ty - int(bh * 0.35)), (tx + bw, ty + bh), body, -1)  # torso
        # legs
        cv2.rectangle(f, (tx - int(bw * 0.6), ty + bh), (tx - int(bw * 0.1), ty + bh + int(bh * 0.5)), body, -1)
        cv2.rectangle(f, (tx + int(bw * 0.1), ty + bh), (tx + int(bw * 0.6), ty + bh + int(bh * 0.5)), body, -1)
    return f


def grade_cam(frame: np.ndarray) -> np.ndarray:
    """Darken + desaturate the feed so the bright-yellow HUD pops over it."""
    f = frame.astype(np.float32)
    gray = f @ np.array([0.114, 0.587, 0.299], np.float32)  # BGR luma
    f = f * 0.6 + gray[..., None] * 0.4 * 0.6   # desaturate ~40%
    return np.clip(f * 0.92, 0, 255).astype(np.uint8)


class Renderer:
    def __init__(self, ctx):
        self.ov = FlatOverlay(ctx, (W, H))

    def frame(self, t, cam=None):
        st = layout.state_at(t) if cam is None else cam["state"]
        scene = synthetic_scene(t, st) if cam is None else cam["frame"]
        self.ov.begin()
        layout.build(ArcvAdapter(self.ov), W, H, t, st)
        self.ov.render(cam_frame=grade_cam(scene))
        return cv2.cvtColor(self.ov.read_pixels(), cv2.COLOR_RGB2BGR)


def export_mp4(frames, fps, path, volume, source):
    h, w = frames[0].shape[:2]
    tv = path + ".v.mp4"
    vw = cv2.VideoWriter(tv, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for f in frames:
        vw.write(f)
    vw.release()
    ta = path + ".a.wav"
    save_wav(ta, render_track(CUES, DUR, volume, source=source))
    ff = shutil.which("ffmpeg")
    if ff:
        r = subprocess.run([ff, "-y", "-i", tv, "-i", ta, "-c:v", "libx264",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", path],
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if r.returncode == 0:
            os.remove(tv)
            os.remove(ta)
            print(f"[warn-hud] saved {path} (with audio)")
            return
        print("[warn-hud] ffmpeg failed:\n" + r.stderr.decode(errors="ignore")[-300:])
    print(f"[warn-hud] kept {tv} + {ta}")


def _audio_source():
    try:
        from arcv.audio import arwes_available
        return "arwes" if arwes_available() else "synth"
    except Exception:  # noqa: BLE001
        return "synth"


def run_live(r, ctx, args):
    sched = None
    if args.sound:
        from arcv.audio import Bleeps, CueScheduler
        src = _audio_source()
        print(f"[warn-hud] sound: {src}")
        sched = CueScheduler(Bleeps(volume=args.volume, source=src), CUES)

    src = None
    pipe = None
    if args.camera is not None:
        from arcv.vision import DetectorPipeline
        from arcv.capture import CameraSource
        try:
            src = CameraSource(index=args.camera, width=W, height=H).start()
            pipe = DetectorPipeline(enable_edges=True, enable_contours=True)
            print(f"[warn-hud] camera {args.camera} + CV pipeline")
        except Exception as e:  # noqa: BLE001
            print(f"[warn-hud] camera unavailable ({e}); scripted story")
            src = None

    t0 = time.perf_counter()
    last = t0
    prev_tl = 0.0
    cshown: dict = {}
    print("[warn-hud] press Q or ESC to quit")
    while True:
        now = time.perf_counter()
        t = now - t0
        dt = max(now - last, 1e-3)
        fps = 1.0 / dt
        last = now
        cam = None
        if src is not None:
            frame = src.read()
            if frame is not None:
                frame = cv2.resize(frame, (W, H))
                det = pipe.process(frame)
                st = layout.state_from_detections(t, det, fps)
                # smooth the instant card targets so cards spawn/collapse over time
                k = min(1.0, dt * 7.0)
                for cid, tgt in st.cards.items():
                    cshown[cid] = cshown.get(cid, 0.0) + (tgt - cshown.get(cid, 0.0)) * k
                st.cards = dict(cshown)
                cam = {"frame": frame, "state": st}
        tl = t % DUR                       # loop the scripted story
        if sched is not None and cam is None:
            if tl < prev_tl:               # wrapped -> replay the cue list
                sched.reset()
            sched.update(tl)
        prev_tl = tl
        cv2.imshow("ARCV — WARNING // Target Acquisition HUD", r.frame(t if cam is not None else tl, cam))
        if (cv2.waitKey(1) & 0xFF) in (27, ord("q")):
            break
    if src is not None:
        src.release()
    cv2.destroyAllWindows()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="show a window instead of exporting")
    ap.add_argument("--camera", type=int, default=None, help="use a real webcam + CV (live only)")
    ap.add_argument("--sound", action="store_true", help="play bleeps (live)")
    ap.add_argument("--gif", default=os.path.join(_HERE, "..", "warning_hud.gif"))
    ap.add_argument("--sheet", default=os.path.join(_HERE, "..", "warning_timeline.png"))
    ap.add_argument("--mp4", default=os.path.join(_HERE, "..", "warning_hud.mp4"))
    ap.add_argument("--stills", default=os.path.join(_HERE, "..", "warning_stills"))
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--volume", type=float, default=0.6)
    args = ap.parse_args()

    ctx = moderngl.create_standalone_context(require=330)
    r = Renderer(ctx)
    print(f"[warn-hud] renderer={ctx.info['GL_RENDERER']}")

    if args.live:
        run_live(r, ctx, args)
        return

    n = int(DUR * args.fps)
    frames = [r.frame(i / args.fps) for i in range(n)]
    print(f"[warn-hud] rendered {len(frames)} frames")

    # stills (boot / locked / lost / reacquire)
    for name, tt in (("boot", 1.0), ("locked", 3.8), ("lost", 7.2), ("reacquire", 9.6)):
        cv2.imwrite(f"{args.stills}_{name}.png", r.frame(tt))
    print(f"[warn-hud] saved stills {args.stills}_*.png")

    step = max(1, args.fps // 12)
    gw = 900
    gh = int(gw * H / W)

    def _gif_frame(f):
        rgb = cv2.cvtColor(cv2.resize(f, (gw, gh)), cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb).quantize(colors=128, method=Image.FASTOCTREE)

    imgs = [_gif_frame(f) for f in frames[::step]]
    imgs[0].save(args.gif, save_all=True, append_images=imgs[1:],
                 duration=int(1000 / args.fps * step), loop=0, optimize=True)
    print(f"[warn-hud] saved {args.gif}")

    picks = [int(x * args.fps) for x in (1.2, 3.8, 7.2, 9.6, 11.5)]
    cv2.imwrite(args.sheet, np.vstack([frames[min(i, n - 1)] for i in picks]))
    print(f"[warn-hud] saved {args.sheet}")

    export_mp4(frames, args.fps, args.mp4, args.volume, _audio_source())


if __name__ == "__main__":
    main()
