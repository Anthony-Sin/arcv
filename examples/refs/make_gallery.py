"""Assemble the reference-recreation results into two contact sheets (self-
contained — reads the in-repo reference copies + renders under gallery/):

  gallery/_gallery_master.png   — each reference (left) beside its ARCV render (right), 5 rows
  gallery/_gallery_renders.png  — the 5 ARCV recreations stacked

    python examples/refs/make_gallery.py
"""

from __future__ import annotations

import os

import cv2
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
GAL = os.path.join(_HERE, "gallery")
# committed showcase copies (docs/media is the only *.png path git tracks)
_DOCS = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "docs", "media")

# (label, reference image, render png) — all live in gallery/
PAIRS = [
    ("REF1  WARNING SET",         "ref1_reference.webp", "ref1.png"),
    ("REF2  CYBERPUNK WIREFRAME", "ref2_reference.webp", "ref2.png"),
    ("REF3  RADARSCAN",           "ref3_reference.webp", "ref3.png"),
    ("REF4  WINDSHIELD HUD",      "ref4_reference.webp", "ref4.png"),
    ("REF5  AR FACESCAN",         "ref5_reference.webp", "ref5.png"),
]

ROW_H = 320          # pixel height each row is scaled to
GAP = 10
PANEL_LABEL_H = 30


def _scale_h(img, h):
    w = max(1, int(img.shape[1] * h / img.shape[0]))
    return cv2.resize(img, (w, h))


def _label_bar(w, text):
    bar = np.full((PANEL_LABEL_H, w, 3), 24, np.uint8)
    cv2.putText(bar, text, (10, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (235, 235, 235), 1, cv2.LINE_AA)
    return bar


def main():
    os.makedirs(_DOCS, exist_ok=True)
    rows = []
    renders = []
    for i, (label, ref_name, ren_name) in enumerate(PAIRS):
        ref = cv2.imread(os.path.join(GAL, ref_name), cv2.IMREAD_COLOR)
        ren = cv2.imread(os.path.join(GAL, ren_name), cv2.IMREAD_COLOR)
        if ref is None or ren is None:
            print(f"  skip {label}: missing image")
            continue
        cv2.imwrite(os.path.join(_DOCS, "hud_ref%d.png" % (i + 1)), ren)  # committed copy
        ref, ren = _scale_h(ref, ROW_H), _scale_h(ren, ROW_H)
        divider = np.full((ROW_H, 4, 3), 90, np.uint8)
        row = np.hstack([ref, divider, ren])
        row = np.vstack([_label_bar(row.shape[1], f"{label}    [ reference | ARCV render ]"), row])
        rows.append(row)
        renders.append((label, ren))

    if rows:
        W = max(r.shape[1] for r in rows)
        padded = [np.hstack([r, np.full((r.shape[0], W - r.shape[1], 3), 12, np.uint8)]) for r in rows]
        gap = np.full((GAP, W, 3), 12, np.uint8)
        master = padded[0]
        for r in padded[1:]:
            master = np.vstack([master, gap, r])
        p1 = os.path.join(GAL, "_gallery_master.png")
        cv2.imwrite(p1, master)
        cv2.imwrite(os.path.join(_DOCS, "hud_recreations.png"), master)  # committed hero
        print("saved", p1, master.shape)

    if renders:
        W = max(r.shape[1] for _, r in renders)
        blocks = []
        for label, r in renders:
            if r.shape[1] < W:
                r = np.hstack([r, np.full((r.shape[0], W - r.shape[1], 3), 12, np.uint8)])
            blocks.append(np.vstack([_label_bar(W, label), r]))
        gap = np.full((GAP, W, 3), 12, np.uint8)
        sheet = blocks[0]
        for b in blocks[1:]:
            sheet = np.vstack([sheet, gap, b])
        p2 = os.path.join(GAL, "_gallery_renders.png")
        cv2.imwrite(p2, sheet)
        print("saved", p2, sheet.shape)


if __name__ == "__main__":
    main()
