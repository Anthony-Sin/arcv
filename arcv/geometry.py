"""Shared GPU geometry helpers."""

from __future__ import annotations

import numpy as np

# A single oversized triangle that covers the whole screen (no VBO seam, one
# fewer vertex than a quad). v_uv is derived in the vertex shader.
_FULLSCREEN_TRI = np.array([-1.0, -1.0, 3.0, -1.0, -1.0, 3.0], dtype="f4")


def fullscreen_buffer(ctx):
    return ctx.buffer(_FULLSCREEN_TRI.tobytes())


def fullscreen_vao(ctx, program, vbo):
    return ctx.vertex_array(program, [(vbo, "2f", "in_pos")])
