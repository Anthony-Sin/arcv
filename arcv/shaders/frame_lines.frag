#version 330
#include "frame_lib.glsl"

// Top + bottom rules that draw from the center outward, plus small inner ticks.
float frameShape(vec2 px, vec2 c, vec2 hs, float prog) {
    float L = c.x - hs.x, R = c.x + hs.x, T = c.y + hs.y, B = c.y - hs.y;
    float cx = c.x;
    float tick = clamp(min(hs.x, hs.y) * 0.4, 8.0, 24.0);
    float hw = 1.5;
    vec2 pts[10];
    float a = 0.0;

    pts[0] = vec2(cx, T); pts[1] = vec2(L, T); a = max(a, strokeReveal(px, pts, 2, prog, hw));
    pts[0] = vec2(cx, T); pts[1] = vec2(R, T); a = max(a, strokeReveal(px, pts, 2, prog, hw));
    pts[0] = vec2(cx, B); pts[1] = vec2(L, B); a = max(a, strokeReveal(px, pts, 2, prog, hw));
    pts[0] = vec2(cx, B); pts[1] = vec2(R, B); a = max(a, strokeReveal(px, pts, 2, prog, hw));

    // inner ticks dropping from the top line near each end
    pts[0] = vec2(L + tick, T - 3.0); pts[1] = vec2(L + tick, T - 3.0 - tick);
    a = max(a, strokeReveal(px, pts, 2, prog, hw));
    pts[0] = vec2(R - tick, T - 3.0); pts[1] = vec2(R - tick, T - 3.0 - tick);
    a = max(a, strokeReveal(px, pts, 2, prog, hw));
    return a;
}

#include "frame_main.glsl"
