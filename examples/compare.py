"""Side-by-side comparison: plain OpenCV vs ARCV doing the SAME two things —
render the feed and annotate detections — on the SAME frame + SAME detections.

Left  = OpenCV baseline (CPU: brackets, putText, GaussianBlur glow, scanlines).
Right = ARCV (GPU: draw-on brackets, decipher labels, reticle, edge-trace,
        HDR ping-pong bloom, animated scanline sweep).

Capture + detection run ONCE per frame and are shared, so neither side is
charged for them; per-library *render* time is measured and shown separately.
The GPU->CPU readback used only for display is excluded from ARCV's timing.

Usage:
    python examples/compare.py                 # live window, synthetic source
    python examples/compare.py --camera 0      # live window, webcam
    python examples/compare.py --image face.jpg
    python examples/compare.py --bench 200     # headless FPS benchmark
    python examples/compare.py --save out.png  # render a still side-by-side
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import deque

import os

import cv2
import moderngl
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)              # examples/ (for _demo_scene, opencv_baseline)
sys.path.insert(0, os.path.dirname(_HERE))  # repo root (for arcv)
from arcv.scene import Scene  # noqa: E402
from arcv.theme import make_theme  # noqa: E402
from arcv.vision.pipeline import DetectorPipeline  # noqa: E402
from arcv.passes.base import Target  # noqa: E402

from _demo_scene import FrameSource  # noqa: E402
from opencv_baseline import OpenCVHud  # noqa: E402


def _stats(samples):
    a = np.asarray(samples, dtype=np.float64)
    return a.mean(), np.percentile(a, 95)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", type=int, default=None)
    ap.add_argument("--image", type=str, default=None)
    ap.add_argument("--size", type=str, default="640x360", help="WxH per half")
    ap.add_argument("--bench", type=int, default=0, help="headless: N frames, print stats")
    ap.add_argument("--save", type=str, default=None, help="render a still and save")
    ap.add_argument("--frames", type=int, default=45, help="warm-up frames for --save")
    ap.add_argument("--theme", default="cyan", help="cyan|amber|red|green|magenta|ice")
    ap.add_argument("--frame", default="nefrex", help="frame style for the ARCV side")
    ap.add_argument("--faces", default="haar", help="haar|yunet")
    ap.add_argument("--upload", default="direct", help="direct|double")
    args = ap.parse_args()

    w, h = (int(v) for v in args.size.lower().split("x"))

    ctx = moderngl.create_standalone_context(require=330)
    theme = make_theme(args.theme)
    scene = Scene(ctx, (w, h), theme=theme, frame_style=args.frame, upload=args.upload)
    out = Target(ctx, (w, h), components=4, dtype="f1")
    hud = OpenCVHud((w, h))
    pipe = DetectorPipeline(max_boxes=12, face_backend=args.faces)
    src = FrameSource(w, h, camera=args.camera, image=args.image)
    print(f"[compare] source={src.kind} size={w}x{h} renderer={ctx.info['GL_RENDERER']}")

    def render_pair(t):
        frame = src.read(t)
        dets = pipe.process(frame)  # shared, timed separately

        c0 = time.perf_counter()
        ocv = hud.render(frame, dets, t)
        ocv_ms = (time.perf_counter() - c0) * 1000.0

        scene.submit(frame, dets)
        g0 = time.perf_counter()
        scene.render(t, target=out.fbo)
        ctx.finish()
        arcv_ms = (time.perf_counter() - g0) * 1000.0

        arcv_rgb = scene.read_pixels(out.fbo)  # display only; excluded from timing
        arcv = cv2.cvtColor(arcv_rgb, cv2.COLOR_RGB2BGR)
        return ocv, arcv, ocv_ms, arcv_ms

    # ---- headless benchmark ----
    if args.bench:
        o_s, a_s = [], []
        for i in range(args.bench):
            _, _, om, am = render_pair(i * 0.033)
            if i > 5:  # skip warm-up
                o_s.append(om)
                a_s.append(am)
        om, op95 = _stats(o_s)
        am, ap95 = _stats(a_s)
        print("\n=== HUD render cost (capture + detection excluded, shared) ===")
        print(f"OpenCV (CPU):  mean {om:6.2f} ms  p95 {op95:6.2f} ms  ~{1000/om:5.1f} fps")
        print(f"ARCV  (GPU):   mean {am:6.2f} ms  p95 {ap95:6.2f} ms  ~{1000/am:5.1f} fps")
        print(f"speedup: {om/am:0.2f}x")
        src.release()
        return

    # ---- still image ----
    if args.save:
        ocv = arcv = None
        for i in range(args.frames):  # warm up so enter animations settle
            ocv, arcv, om, am = render_pair(i * 0.033)
        combo = _compose(ocv, arcv, om, am, w, h)
        cv2.imwrite(args.save, combo)
        print(f"[compare] saved {args.save}")
        src.release()
        return

    # ---- live window ----
    o_hist, a_hist = deque(maxlen=30), deque(maxlen=30)
    t0 = time.perf_counter()
    print("[compare] press Q or ESC to quit")
    while True:
        t = time.perf_counter() - t0
        ocv, arcv, om, am = render_pair(t)
        o_hist.append(om)
        a_hist.append(am)
        combo = _compose(ocv, arcv, np.mean(o_hist), np.mean(a_hist), w, h)
        cv2.imshow("ARCV vs OpenCV", combo)
        k = cv2.waitKey(1) & 0xFF
        if k in (27, ord("q")):
            break
    src.release()
    cv2.destroyAllWindows()


def _compose(ocv, arcv, om, am, w, h):
    combo = np.hstack([ocv, arcv])
    cv2.line(combo, (w, 0), (w, h), (60, 60, 60), 1)
    _tag(combo, f"OpenCV (CPU)   {om:5.1f} ms  {1000/max(om,1e-3):4.0f} fps", 10)
    _tag(combo, f"ARCV (GPU)     {am:5.1f} ms  {1000/max(am,1e-3):4.0f} fps", w + 10)
    return combo


def _tag(img, text, x):
    cv2.putText(img, text, (x, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, (x, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)


if __name__ == "__main__":
    main()
