"""Render the ARCV HUD over a still image (or synthetic scene) — no webcam.

    python examples/preview_static.py                 # synthetic scene -> window
    python examples/preview_static.py --image face.jpg
    python examples/preview_static.py --save out.png
"""

from __future__ import annotations

import argparse
import sys
import time

import os

import cv2
import moderngl

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))
from arcv.scene import Scene  # noqa: E402
from arcv.theme import make_theme  # noqa: E402
from arcv.vision.pipeline import DetectorPipeline  # noqa: E402
from arcv.passes.base import Target  # noqa: E402

from _demo_scene import FrameSource  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", type=str, default=None)
    ap.add_argument("--size", type=str, default="960x540")
    ap.add_argument("--save", type=str, default=None)
    ap.add_argument("--frames", type=int, default=45)
    ap.add_argument("--frame", default="nefrex",
                    help="nefrex|corners|lines|octagon|underline|kranox")
    ap.add_argument("--text", default="decipher", help="decipher|typeon")
    ap.add_argument("--bg", default="", help="comma list: dots,gridlines,movinglines,puffs")
    ap.add_argument("--keypoints", action="store_true", help="ORB / landmark tracker dots")
    ap.add_argument("--theme", default="cyan", help="cyan|amber|red|green|magenta|ice")
    ap.add_argument("--faces", default="haar", help="haar|yunet")
    ap.add_argument("--upload", default="direct", help="direct|double")
    args = ap.parse_args()

    w, h = (int(v) for v in args.size.lower().split("x"))
    backgrounds = [b for b in args.bg.split(",") if b]
    ctx = moderngl.create_standalone_context(require=330)
    pipeline = DetectorPipeline(
        max_boxes=12, enable_orb=args.keypoints, enable_flow=bool(backgrounds),
        face_backend=args.faces,
    )
    scene = Scene(
        ctx, (w, h), theme=make_theme(args.theme), detector=pipeline,
        frame_style=args.frame, text_style=args.text,
        backgrounds=backgrounds, show_keypoints=args.keypoints, upload=args.upload,
    )
    out = Target(ctx, (w, h), components=4, dtype="f1")
    src = FrameSource(w, h, image=args.image)
    print(f"[preview] source={src.kind} renderer={ctx.info['GL_RENDERER']}")

    if args.save:
        for i in range(args.frames):
            frame = src.read(i * 0.033)
            scene.submit(frame)
            scene.render(i * 0.033, target=out.fbo)
        img = scene.read_pixels(out.fbo)
        cv2.imwrite(args.save, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        print(f"[preview] saved {args.save}")
        return

    t0 = time.perf_counter()
    print("[preview] press Q or ESC to quit")
    while True:
        t = time.perf_counter() - t0
        frame = src.read(t)
        scene.submit(frame)
        scene.render(t, target=out.fbo)
        img = scene.read_pixels(out.fbo)
        cv2.imshow("ARCV preview", cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        if (cv2.waitKey(1) & 0xFF) in (27, ord("q")):
            break
    src.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
