"""REF5 — Spider-Man-style AR face-recognition overlay (translucent blue holo).

A glowing blue-cyan holographic targeting overlay floating over a dark
top-down industrial scene. All content is authored as local helper primitives
composed from the ARCV adapter `d`; nothing under arcv/ or any shared file is
touched. Deterministic geometry only (no randomness).

Heroes:
  face_mesh    — a triangulated FACE MESH over the implied bald man's face
  hex_bracket  — a hexagonal targeting reticle around the face
  ar_web       — faint concentric circles + long radial "network" lines
  db_panel     — translucent name-list panels with RED highlight rows
  id_card      — NICBCS card with data table + mugshot slot + M. GARGAN
  spectrum_bar — vertical rainbow chromatic edge marker (+ 82% + L bracket)
  hex_badge    — small hexagon with a number ("42", "84")
"""

from __future__ import annotations

import math

# ------------------------------------------------------------------ palette
# holographic BLUE-CYAN primary, with dim/faint variants for the web, WHITE
# for key text, RED for highlight bars. Brightened so the holo reads clearly
# on the pure-dark base (like the reference).
HOLO = (0.60, 0.90, 1.0, 1.0)          # primary blue-cyan
HOLO_B = (0.72, 0.95, 1.0, 1.0)        # brighter accent
HOLO_DIM = (0.55, 0.85, 1.0, 0.9)      # dim structure (still bright)
FAINT = (0.50, 0.80, 1.0, 0.6)         # faint web (boosted)
FAINT2 = (0.48, 0.78, 1.0, 0.42)       # very faint (boosted)
WHITE = (0.92, 0.98, 1.0, 1.0)         # key text
WHITE_D = (0.85, 0.94, 1.0, 0.9)
RED = (0.98, 0.22, 0.20, 0.6)          # highlight bar (saturated)
RED_B = (1.0, 0.30, 0.26, 0.85)        # red arcs
PANEL = (0.32, 0.62, 0.92, 0.09)       # translucent panel fill

# full-saturation rainbow for the chromatic spectrum bars
RAINBOW = [
    (1.0, 0.15, 0.15, 1.0),   # red
    (1.0, 0.5, 0.1, 1.0),     # orange
    (1.0, 0.9, 0.1, 1.0),     # yellow
    (0.3, 1.0, 0.2, 1.0),     # green
    (0.1, 1.0, 0.9, 1.0),     # cyan
    (0.2, 0.5, 1.0, 1.0),     # blue
    (0.7, 0.25, 1.0, 1.0),    # violet
]

_TAU = math.pi * 2.0


def _f(c, a):
    return (c[0], c[1], c[2], c[3] * a)


# =====================================================================
#  HERO HELPER PRIMITIVES
# =====================================================================
def face_mesh(d, cx, cy, w, h, s):
    """A triangulated FACE MESH that unmistakably reads as a FACE.

    Construction:
      * an OVAL face contour (ring of points around the head),
      * a symmetric pair of EYE clusters + a BROW line,
      * a NOSE bridge -> tip,
      * a MOUTH cluster, and a JAW / CHIN line,
    all wired into triangles, with small square feature-markers over the
    eyes / nose / mouth. Deterministic geometry only."""
    hw, hh = w * 0.5, h * 0.5

    def P(nx, ny):
        return (cx + nx * hw, cy + ny * hh)

    # ---- OVAL face contour: 14 points around an egg-shaped oval (wider at
    # cheeks, tapering to the chin at the bottom). Deterministic angle table.
    oval = []
    n_oval = 14
    for i in range(n_oval):
        a = -math.pi / 2 + i * _TAU / n_oval   # start at top, go clockwise
        ox = math.cos(a) * 0.78
        oy = math.sin(a)
        # taper the lower half toward a pointed chin; narrow the very top
        if oy > 0:
            ox *= (1.0 - 0.28 * oy)             # jaw narrows toward chin
            oy = oy * 1.02
        else:
            ox *= (1.0 + 0.04 * oy)
            oy = oy * 0.88                       # slightly flatter crown
        oval.append(P(ox, oy))
    # chin is the lowest oval point (index n_oval*3//4 ~ bottom); force a clean
    # pointed chin at bottom-center for the jaw line.
    chin = P(0.0, 0.98)

    # ---- interior feature anchors --------------------------------------
    brow_l = P(-0.36, -0.34)
    brow_c = P(0.0, -0.40)
    brow_r = P(0.36, -0.34)
    eye_l = P(-0.32, -0.18)
    eye_r = P(0.32, -0.18)
    eye_li = P(-0.14, -0.16)   # inner corners
    eye_ri = P(0.14, -0.16)
    nose_top = P(0.0, -0.10)
    nose_mid = P(0.0, 0.10)
    nose_tip = P(0.0, 0.26)
    nose_l = P(-0.10, 0.24)
    nose_r = P(0.10, 0.24)
    cheek_l = P(-0.44, 0.14)
    cheek_r = P(0.44, 0.14)
    mouth_l = P(-0.22, 0.48)
    mouth_c = P(0.0, 0.50)
    mouth_r = P(0.22, 0.48)
    jaw_l = P(-0.40, 0.52)
    jaw_r = P(0.40, 0.52)

    # ---- draw the OVAL contour (closed) as bright structure ------------
    d.poly(oval, _f(HOLO, 0.65), 1.2 * s, closed=True)

    # ---- triangle web edges (deterministic) ----------------------------
    edges = [
        # brow line
        (brow_l, brow_c), (brow_c, brow_r),
        # brows to eyes
        (brow_l, eye_l), (brow_r, eye_r), (brow_c, eye_li), (brow_c, eye_ri),
        # eye clusters
        (eye_l, eye_li), (eye_r, eye_ri), (eye_li, eye_ri),
        (eye_l, cheek_l), (eye_r, cheek_r),
        # nose bridge -> tip
        (eye_li, nose_top), (eye_ri, nose_top),
        (nose_top, nose_mid), (nose_mid, nose_tip),
        (nose_tip, nose_l), (nose_tip, nose_r), (nose_l, nose_r),
        (nose_mid, cheek_l), (nose_mid, cheek_r),
        # cheeks
        (cheek_l, nose_l), (cheek_r, nose_r),
        (cheek_l, mouth_l), (cheek_r, mouth_r),
        # mouth cluster
        (mouth_l, mouth_c), (mouth_c, mouth_r),
        (nose_l, mouth_l), (nose_r, mouth_r), (nose_tip, mouth_c),
        # jaw / chin line
        (mouth_l, jaw_l), (mouth_r, jaw_r),
        (jaw_l, chin), (jaw_r, chin), (mouth_c, chin),
        (mouth_l, chin), (mouth_r, chin),
        (cheek_l, jaw_l), (cheek_r, jaw_r),
    ]
    for (a, b) in edges:
        d.line(a[0], a[1], b[0], b[1], _f(HOLO, 0.62), 1.0 * s)

    # ---- connect interior anchors to the nearest oval contour points so the
    # mesh fills the whole face (spider-web to the silhouette). Deterministic
    # nearest-neighbour by distance.
    spokes = [brow_l, brow_r, eye_l, eye_r, cheek_l, cheek_r, jaw_l, jaw_r,
              nose_top, brow_c]
    for (ax, ay) in spokes:
        nearest = min(oval, key=lambda p: (p[0] - ax) ** 2 + (p[1] - ay) ** 2)
        d.line(ax, ay, nearest[0], nearest[1], _f(HOLO, 0.45), 1.0 * s)

    # ---- node dots at every anchor ------------------------------------
    nodes = [brow_l, brow_c, brow_r, eye_l, eye_r, eye_li, eye_ri, nose_top,
             nose_mid, nose_tip, nose_l, nose_r, cheek_l, cheek_r, mouth_l,
             mouth_c, mouth_r, jaw_l, jaw_r, chin]
    for (px, py) in nodes + oval:
        d.disc(px, py, 1.7 * s, _f(HOLO_B, 0.95))

    # ---- square feature markers over eyes / nose / mouth --------------
    def marker(pt, half):
        d.rect(pt[0] - half, pt[1] - half, pt[0] + half, pt[1] + half, HOLO_B, 1.3 * s)
    marker(eye_l, 8 * s)
    marker(eye_r, 8 * s)
    marker(nose_tip, 6 * s)
    marker(mouth_c, 7 * s)


def hex_bracket(d, cx, cy, r, s, c=HOLO):
    """Hexagon targeting frame (six-sided) with small corner ticks."""
    pts = []
    for k in range(6):
        a = -math.pi / 2 + k * _TAU / 6.0
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    d.poly(pts, _f(c, 0.9), 1.6 * s, closed=True)
    # corner ticks: short outward spurs at each vertex
    for (px, py) in pts:
        dx, dy = px - cx, py - cy
        m = math.hypot(dx, dy) or 1.0
        ux, uy = dx / m, dy / m
        d.line(px, py, px + ux * 10 * s, py + uy * 10 * s, _f(c, 0.9), 1.6 * s)


def hex_node_graph(d, cx, cy, r, s):
    """Radiating hexagon node graph beside the face (small hexes joined by
    lines) — deterministic angles."""
    nodes = []
    for k in range(6):
        a = k * _TAU / 6.0
        nx = cx + math.cos(a) * r
        ny = cy + math.sin(a) * r
        nodes.append((nx, ny))
        # small hexagon at each node
        for j in range(6):
            b = j * _TAU / 6.0
            d.line(nx + math.cos(b) * 6 * s, ny + math.sin(b) * 6 * s,
                   nx + math.cos(b + _TAU / 6) * 6 * s, ny + math.sin(b + _TAU / 6) * 6 * s,
                   _f(HOLO, 0.6), 1.0 * s)
        d.line(cx, cy, nx, ny, _f(HOLO, 0.4), 1.0 * s)
        d.disc(nx, ny, 2.0 * s, _f(HOLO_B, 0.9))
    d.disc(cx, cy, 2.5 * s, HOLO_B)


def ar_web(d, W, H, s):
    """Faint large concentric CIRCLES + long radial/connecting LINES spanning
    the frame — the AR 'global information network', with small node dots where
    lines meet. Deterministic geometry."""
    cx, cy = W * 0.52, H * 0.44
    # concentric circles (brighter so the lens reads clearly)
    for i, rr in enumerate((0.14, 0.24, 0.36, 0.50, 0.66, 0.82)):
        d.ring(cx, cy, rr * W * 0.5, _f(FAINT, 1.0 if i < 2 else 0.7), 1.3 * s)
    # a dotted inner ring (radar-ish) near the top-center
    dr = 0.20 * W * 0.5
    for k in range(72):
        a = k * _TAU / 72.0
        px = W * 0.50 + math.cos(a) * dr
        py = H * 0.10 + math.sin(a) * dr * 0.9
        if k % 2 == 0:
            d.disc(px, py, 0.8 * s, _f(FAINT, 0.6))

    # long radial spokes from center to frame edge, deterministic angles
    spokes = [12, 34, 58, 108, 128, 152, 200, 222, 274, 300, 322, 344]
    edge_nodes = []
    for deg in spokes:
        a = math.radians(deg)
        ex = cx + math.cos(a) * W * 1.1
        ey = cy + math.sin(a) * H * 1.1
        d.line(cx, cy, ex, ey, _f(FAINT2, 1.3), 1.2 * s)
        # node dot partway along
        for frac in (0.35, 0.62, 0.85):
            nx = cx + math.cos(a) * W * 0.55 * frac * 2
            ny = cy + math.sin(a) * H * 0.55 * frac * 2
            if 0 < nx < W and 0 < ny < H:
                edge_nodes.append((nx, ny, deg))
                d.disc(nx, ny, 1.2 * s, _f(FAINT, 0.7))

    # a few long connecting chords between distant nodes (the "network")
    chords = [(0, 6), (2, 9), (4, 11), (7, 13), (1, 10)]
    corners = [(W * 0.08, H * 0.12), (W * 0.92, H * 0.16), (W * 0.90, H * 0.9),
               (W * 0.1, H * 0.88), (W * 0.5, H * 0.02), (W * 0.5, H * 0.98)]
    for (i, j) in chords:
        p, qq = corners[i % len(corners)], corners[j % len(corners)]
        d.line(p[0], p[1], qq[0], qq[1], _f(FAINT2, 0.7), 1.0 * s)


def pct_mark(d, x, y, sz, c, s):
    """Draw a clean '%' sign from primitives (two small rings + a slash) so the
    readout stays unambiguous under bloom (the atlas glyph blurs to '4'-ish)."""
    r = sz * 0.14
    d.ring(x + r, y + r, r, c, 1.3 * s)                       # top-left circle
    d.ring(x + sz * 0.5 - r, y + sz - r, r, c, 1.3 * s)        # bottom-right
    d.line(x + sz * 0.5, y, x, y + sz, c, 1.4 * s)            # slash


def spectrum_bar(d, x, y0, h, s, num="82", side="left"):
    """Vertical CHROMATIC/RAINBOW edge marker: stacked short segments cycling
    through the rainbow; paired with a percentage and an L-corner bracket. The
    percent value is drawn as the number + a primitive '%' mark."""
    n = len(RAINBOW)
    seg = h / n
    bw = 7 * s
    for i in range(n):
        col = RAINBOW[i]
        yy0 = y0 + i * seg
        yy1 = yy0 + seg - 1.5 * s
        # draw the segment as a thick short vertical line
        d.line(x, yy0, x, yy1, col, bw)
    ty = y0 - 22 * s
    th = 15 * s
    if side == "left":
        # L-corner bracket wrapping the top of the bar
        d.line(x - bw * 0.9, y0 - 6 * s, x - bw * 0.9, y0 + 22 * s, HOLO, 1.4 * s)
        d.line(x - bw * 0.9, y0 - 6 * s, x + bw * 0.9, y0 - 6 * s, HOLO, 1.4 * s)
        tx = x + bw + 4 * s
        d.text(num, tx, ty, th, WHITE, align="left")
        pct_mark(d, tx + d.text_width(num, th) + 3 * s, ty + 1 * s, th, WHITE, s)
    else:
        d.line(x + bw * 0.9, y0 - 6 * s, x + bw * 0.9, y0 + 22 * s, HOLO, 1.4 * s)
        d.line(x + bw * 0.9, y0 - 6 * s, x - bw * 0.9, y0 - 6 * s, HOLO, 1.4 * s)
        mw = th * 0.5
        tx = x - bw - 4 * s
        # right-aligned: draw mark first then number to its left
        pct_mark(d, tx - mw, ty + 1 * s, th, WHITE, s)
        d.text(num, tx - mw - 3 * s, ty, th, WHITE, align="right")


def hex_badge(d, cx, cy, label, s, r=26):
    """Small hexagon with a number inside."""
    r = r * s
    pts = []
    for k in range(6):
        a = math.pi / 6 + k * _TAU / 6.0   # flat-top
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    d.poly(pts, HOLO, 1.6 * s, closed=True)
    # inner faint hex
    pts2 = [(cx + (p[0] - cx) * 0.8, cy + (p[1] - cy) * 0.8) for p in pts]
    d.poly(pts2, _f(HOLO, 0.4), 1.0 * s, closed=True)
    d.text(label, cx, cy - r * 0.42, r * 0.85, WHITE, align="center")


def db_panel(d, x0, y0, x1, y1, title, rows, s, highlights=()):
    """Translucent panel with a title bar + list of NAME rows (monospace); some
    rows overlaid with a semi-transparent RED highlight bar."""
    d.rrect_fill(x0, y0, x1, y1, 3 * s, PANEL)
    d.rect(x0, y0, x1, y1, _f(HOLO, 0.8), 1.4 * s)
    # title bar
    d.line(x0, y0 + 16 * s, x1, y0 + 16 * s, _f(HOLO, 0.6), 1.0 * s)
    d.text(title, x0 + 6 * s, y0 + 4 * s, 9.5 * s, WHITE, align="left")
    # corner ticks
    d.line(x0, y0, x0 + 8 * s, y0, HOLO_B, 2.0 * s)
    d.line(x1, y1, x1 - 8 * s, y1, HOLO_B, 2.0 * s)
    # rows
    ry0 = y0 + 22 * s
    rh = (y1 - ry0 - 4 * s) / max(1, len(rows))
    for i, name in enumerate(rows):
        yy = ry0 + i * rh
        if i in highlights:
            d.line(x0 + 2 * s, yy + rh * 0.5, x1 - 2 * s, yy + rh * 0.5, RED, rh)
        d.text(name, x0 + 6 * s, yy, 6.5 * s, _f(HOLO, 0.9), align="left")
        # tiny code column at right
        d.text("%02d" % (i * 3 % 100), x1 - 22 * s, yy, 6.5 * s, _f(HOLO, 0.6), align="left")


def id_card(d, x0, y0, x1, y1, s):
    """NATIONAL INSTANT CRIMINAL BACKGROUND CHECK SYSTEM card — data table on
    the left, MUGSHOT slot with a simple face silhouette on the right, and
    'M. GARGAN'."""
    d.rrect_fill(x0, y0, x1, y1, 3 * s, PANEL)
    d.rect(x0, y0, x1, y1, _f(HOLO, 0.85), 1.5 * s)
    # corner ticks
    for (cx0, sx) in ((x0, 1), (x1, -1)):
        for (cy0, sy) in ((y0, 1), (y1, -1)):
            d.line(cx0, cy0, cx0 + sx * 10 * s, cy0, HOLO_B, 2.0 * s)
            d.line(cx0, cy0, cx0, cy0 + sy * 10 * s, HOLO_B, 2.0 * s)
    # title
    d.text("NATIONAL INSTANT CRIMINAL BACKGROUND CHECK SYSTEM",
           x0 + 8 * s, y0 + 5 * s, 8.5 * s, WHITE, align="left")
    d.line(x0, y0 + 18 * s, x1, y0 + 18 * s, _f(HOLO, 0.6), 1.0 * s)

    # left data table: label + value bars
    tx = x0 + 10 * s
    labels = ["AFRICAN AMERICAN", "SEX / M", "COMPLEXION", "EYE", "HAIR",
              "BLACK", "NRA", "REG"]
    vy = y0 + 26 * s
    mug_x0 = x1 - (y1 - y0) * 0.82   # mugshot column start
    col2 = x0 + (mug_x0 - x0) * 0.5
    for i, lab in enumerate(labels):
        yy = vy + i * ((y1 - vy - 6 * s) / len(labels))
        d.text(lab, tx, yy, 6.0 * s, _f(HOLO, 0.85), align="left")
        # a filled cyan value bar next to it
        bx0 = col2
        bx1 = mug_x0 - 14 * s
        bw = (bx1 - bx0) * (0.4 + 0.5 * ((i * 37 % 10) / 10.0))
        d.line(bx0, yy + 4 * s, bx0 + bw, yy + 4 * s, _f(HOLO_B, 0.9), 4.0 * s)

    # mugshot slot on the right
    m0x, m0y = mug_x0, y0 + 24 * s
    m1x, m1y = x1 - 10 * s, y1 - 24 * s
    d.rect(m0x, m0y, m1x, m1y, _f(HOLO, 0.9), 1.4 * s)
    d.rrect_fill(m0x, m0y, m1x, m1y, 2 * s, _f(HOLO, 0.06))
    # simple face silhouette inside the mugshot
    fcx = (m0x + m1x) * 0.5
    fcy = (m0y + m1y) * 0.45
    fr = (m1x - m0x) * 0.26
    d.ring(fcx, fcy, fr, _f(HOLO, 0.7), 1.2 * s)                  # head
    d.ring(fcx, fcy + fr * 1.6, fr * 1.5, _f(HOLO, 0.5), 1.2 * s,
           a0=math.radians(200), a1=math.radians(340))            # shoulders arc
    # M. GARGAN caption under card
    d.text("M. GARGAN", (m0x + m1x) * 0.5, m1y + 3 * s, 9 * s, WHITE, align="center")


def corner_reticle(d, cx, cy, r, s, c=HOLO):
    """A square bracket reticle with corner Ls (tracked target)."""
    for (sx, sy) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        px = cx + sx * r
        py = cy + sy * r
        d.line(px, py, px - sx * r * 0.4, py, c, 1.4 * s)
        d.line(px, py, px, py - sy * r * 0.4, c, 1.4 * s)


def crosshair(d, cx, cy, r, s, c=HOLO):
    """An X target reticle."""
    d.line(cx - r, cy - r, cx + r, cy + r, c, 1.4 * s)
    d.line(cx - r, cy + r, cx + r, cy - r, c, 1.4 * s)
    d.ring(cx, cy, r * 0.5, _f(c, 0.7), 1.2 * s)


def connecting_header(d, cx, y, s):
    """The 'CONNECTING' header panel with 'IP ADDRESS 192.168.23.5'."""
    w = 200 * s
    h = 24 * s
    x0, x1 = cx - w, cx + w
    # angled-end bar (chevrons at both ends)
    d.rrect_fill(x0, y, x1, y + h, 2 * s, _f(HOLO, 0.10))
    d.rect(x0, y, x1, y + h, _f(HOLO, 0.85), 1.4 * s)
    # end chevrons
    for (ex, dirn) in ((x0, 1), (x1, -1)):
        d.line(ex, y, ex + dirn * 10 * s, y + h * 0.5, HOLO_B, 2.0 * s)
        d.line(ex + dirn * 10 * s, y + h * 0.5, ex, y + h, HOLO_B, 2.0 * s)
    d.text("CONNECTING", cx, y + 4 * s, 15 * s, WHITE, align="center")
    d.text("IP ADDRESS 192.168.23.5", cx, y + h + 3 * s, 8 * s, _f(HOLO, 0.9),
           align="center")


# =====================================================================
#  BUILD
# =====================================================================
def build(d, W, H, t=0.0):
    s = H / 837.0

    # ---- background AR web (draw first, faint) ----
    ar_web(d, W, H, s)

    # global network label at very top center
    d.text("GLOBAL INFORMATION NETWORK", W * 0.5, H * 0.028, 7.5 * s,
            _f(HOLO, 0.7), align="center")

    # =============================== FACE REGION (center-top) ============
    face_cx, face_cy = W * 0.595, H * 0.28
    fw, fh = W * 0.155, H * 0.42
    # tall vertical targeting bracket frame around the face (ref: rounded
    # arrow-tipped vertical brackets on both sides of the head)
    bx0, bx1 = face_cx - fw * 0.72, face_cx + fw * 0.72
    by0, by1 = face_cy - fh * 0.55, face_cy + fh * 0.72
    for (ex, dirn) in ((bx0, 1), (bx1, -1)):
        d.line(ex, by0 + 24 * s, ex, by1 - 24 * s, _f(HOLO, 0.75), 1.6 * s)
        # arrow tip top
        d.line(ex, by0 + 24 * s, ex + dirn * 18 * s, by0, _f(HOLO, 0.75), 1.6 * s)
        d.line(ex + dirn * 18 * s, by0, ex + dirn * 36 * s, by0 + 20 * s, _f(HOLO, 0.55), 1.4 * s)
        # arrow tip bottom
        d.line(ex, by1 - 24 * s, ex + dirn * 18 * s, by1, _f(HOLO, 0.75), 1.6 * s)
    # face mesh over implied face (centered on the face)
    face_mesh(d, face_cx, face_cy, fw * 1.15, fh * 1.0, s)
    # hexagon targeting reticle framing the face
    hex_bracket(d, face_cx, face_cy - fh * 0.03, fw * 0.72, s)
    # radiating hexagon node graph to the lower-left of the face
    hex_node_graph(d, face_cx - fw * 0.9, face_cy + fh * 0.55, 30 * s, s)
    # connecting line to a small photo/frame slot below-left
    ph_x, ph_y = face_cx - fw * 1.05, face_cy + fh * 0.28
    d.line(face_cx - fw * 0.3, face_cy + fh * 0.2, ph_x + 30 * s, ph_y + 20 * s,
           _f(HOLO, 0.6), 1.0 * s)
    d.rect(ph_x, ph_y, ph_x + 60 * s, ph_y + 46 * s, _f(HOLO, 0.7), 1.2 * s)
    d.line(ph_x, ph_y, ph_x + 60 * s, ph_y + 46 * s, _f(HOLO, 0.35), 1.0 * s)
    d.line(ph_x + 60 * s, ph_y, ph_x, ph_y + 46 * s, _f(HOLO, 0.35), 1.0 * s)

    # ---- CONNECTING header (above face) ----
    connecting_header(d, W * 0.615, H * 0.05, s)

    # =============================== LEFT EDGE ==========================
    # rainbow spectrum bar on the far left
    spectrum_bar(d, W * 0.022, H * 0.335, H * 0.10, s, num="82", side="left")
    # hex badge "42"
    hex_badge(d, W * 0.147, H * 0.505, "42", s, r=24)
    # 72 degrees temp readout
    d.text("72°", W * 0.062, H * 0.475, 15 * s, WHITE, align="left")
    d.text("SEC TEMP", W * 0.062, H * 0.505, 6.5 * s, _f(HOLO, 0.7), align="left")
    d.text("D2", W * 0.062, H * 0.55, 8 * s, _f(HOLO, 0.7), align="left")
    d.text("57°", W * 0.11, H * 0.55, 8 * s, _f(HOLO, 0.7), align="left")
    # VIEW MODES stacked list
    vx, vy = W * 0.205, H * 0.075
    d.text("VIEW MODES", vx, vy, 9 * s, WHITE, align="left")
    modes = ["DISTRIBUTED APERTURE", "IR-CAM (YELLOW)", "MID-EYE X",
             "ATTUNE THERMAL", "SYNTHETIC APERTURE", "", "ELECTRO OPTICAL",
             "AUGMENTED OVERLAY"]
    for i, m in enumerate(modes):
        if not m:
            continue
        yy = vy + 16 * s + i * 12 * s
        # bullet
        d.disc(vx - 5 * s, yy + 4 * s, 1.6 * s, _f(HOLO, 0.8))
        d.text(m, vx + 3 * s, yy, 7 * s, _f(HOLO, 0.9), align="left")
    # faint reticle bracket on the left (over a person)
    corner_reticle(d, W * 0.205, H * 0.4, 40 * s, s, c=_f(HOLO, 0.8))
    d.text("WEAPONS SCAN", W * 0.078, H * 0.68, 6.5 * s, _f(HOLO, 0.6), align="left")
    d.text("SHIP STRENGTH", W * 0.03, H * 0.78, 6.5 * s, _f(HOLO, 0.55), align="left")
    # red accent arcs at the far-left corner (top and bottom)
    d.ring(W * -0.02, H * 0.13, H * 0.16, RED_B, 3.0 * s, a0=math.radians(-40), a1=math.radians(60))
    d.ring(W * -0.02, H * 0.13, H * 0.19, _f(RED_B, 0.6), 2.0 * s, a0=math.radians(-40), a1=math.radians(60))
    d.ring(W * 0.0, H * 0.86, H * 0.16, RED_B, 3.0 * s, a0=math.radians(-70), a1=math.radians(40))
    # small crosshairs scattered
    crosshair(d, W * 0.075, H * 0.83, 10 * s, s, c=_f(RED_B, 0.7))

    # =============================== RIGHT SIDE =========================
    # NATIONAL NAME CHECK PROGRAM db panel
    names = ["DANIEL DAVID", "DAVID, AARON X", "DAVID, ZADRA",
             "DAVID, AARON A", "DAVID, ALEXA", "FUMARIO, DAN",
             "DAVID, ALEXA", "DAVID, ACKER A", "DAVID, ALEXA",
             "DAVID, BENJAM", "DAVID, ALEXA", "DAVID, DANIEL"]
    db_panel(d, W * 0.685, H * 0.255, W * 0.795, H * 0.595,
             "NATIONAL NAME CHECK PROGRAM", names, s, highlights=(3, 8))
    # M. GARGAN caption at bottom of that panel
    d.text("M. GARGAN", W * 0.685, H * 0.60, 8 * s, WHITE, align="left")

    # NSA / CIA / FBI agency labels with RED highlight bars (to the right of
    # the name panel, sitting over the scene)
    # red highlight bar high up (near top of panel)
    d.line(W * 0.795, H * 0.355, W * 0.90, H * 0.355, RED, 6 * s)
    # NSA
    d.text("NSA", W * 0.73, H * 0.44, 17 * s, WHITE, align="left")
    # CIA with a long red bar to the right edge
    d.line(W * 0.795, H * 0.525, W * 0.985, H * 0.525, RED, 9 * s)
    d.text("CIA", W * 0.76, H * 0.505, 17 * s, WHITE, align="left")
    # FEDERAL BUREAU OF INVESTIGATION with a red bar
    d.line(W * 0.775, H * 0.585, W * 0.99, H * 0.585, RED, 8 * s)
    d.text("FEDERAL BUREAU OF INVESTIGATION", W * 0.775, H * 0.575, 10 * s,
           WHITE, align="left")

    # a second right-side name column (faint), under FBI
    rnames = ["ADAM", "GURU", "GILE", "BIOL", "TEDAC", "LEEP", "70.226.28.189"]
    for i, nm in enumerate(rnames):
        d.text(nm, W * 0.775, H * 0.63 + i * 15 * s, 7 * s, _f(HOLO, 0.85), align="left")
    # small red bar over the second column
    d.line(W * 0.775, H * 0.63, W * 0.86, H * 0.63, RED, 5 * s)

    # hex badge "84" (far right, mid)
    hex_badge(d, W * 0.885, H * 0.505, "84", s, r=24)

    # mirrored spectrum bar on the far right
    spectrum_bar(d, W * 0.978, H * 0.335, H * 0.10, s, num="82", side="right")
    # right red accent arcs at the corners
    d.ring(W * 1.02, H * 0.13, H * 0.16, RED_B, 3.0 * s, a0=math.radians(120), a1=math.radians(220))
    d.ring(W * 1.02, H * 0.86, H * 0.18, RED_B, 3.0 * s, a0=math.radians(140), a1=math.radians(240))
    corner_reticle(d, W * 0.945, H * 0.44, 34 * s, s, c=_f(HOLO, 0.7))

    # =============================== BOTTOM-CENTER ID CARD ==============
    id_card(d, W * 0.345, H * 0.675, W * 0.565, H * 0.83, s)

    # =============================== SCATTERED RETICLES ================
    # X target reticle top-left over a person
    crosshair(d, W * 0.115, H * 0.05, 16 * s, s, c=HOLO)
    d.text("TARGET 01", W * 0.115, H * 0.09, 6.5 * s, _f(HOLO, 0.7), align="center")
    # small crosshair mid-scene
    crosshair(d, W * 0.42, H * 0.42, 9 * s, s, c=_f(HOLO, 0.7))
    # tiny data labels scattered
    d.text("IP 74 / 189 / 21", W * 0.47, H * 0.55, 6.5 * s, _f(HOLO, 0.6), align="left")
    d.text("744-NRC-445", W * 0.30, H * 0.62, 6.0 * s, _f(HOLO, 0.5), align="left")


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _ref_render import render_png, save_compare
    from arcv.theme import make_theme

    REF = "C:/Users/antho/Downloads/arcv/examples/refs/gallery/ref5_reference.webp"
    theme = make_theme("ice", bloom_intensity=1.0, bloom_threshold=0.45,
                       exposure=1.5, scanline_strength=0.05, sweep_strength=0.0)
    render_png(build, "gallery/ref5.png", size=(1691, 837), mode="glow",
               theme=theme, base_color=(0.02, 0.03, 0.05, 1.0))
    save_compare(REF, "gallery/ref5.png", "gallery/ref5_compare.png", "REF5")
    print("done")
