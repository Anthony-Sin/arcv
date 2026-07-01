#version 330
#include "frame_lib.glsl"

// Four L-shaped corner brackets.
float frameShape(vec2 px, vec2 c, vec2 hs, float prog) {
    float L = c.x - hs.x, R = c.x + hs.x, T = c.y + hs.y, B = c.y - hs.y;
    float arm = clamp(min(hs.x, hs.y) * 0.5, 8.0, 40.0);
    float hw = 1.5;
    vec2 pts[10];
    float a = 0.0;

    pts[0] = vec2(L, T - arm); pts[1] = vec2(L, T); pts[2] = vec2(L + arm, T);
    a = max(a, strokeReveal(px, pts, 3, prog, hw));
    pts[0] = vec2(R, T - arm); pts[1] = vec2(R, T); pts[2] = vec2(R - arm, T);
    a = max(a, strokeReveal(px, pts, 3, prog, hw));
    pts[0] = vec2(L, B + arm); pts[1] = vec2(L, B); pts[2] = vec2(L + arm, B);
    a = max(a, strokeReveal(px, pts, 3, prog, hw));
    pts[0] = vec2(R, B + arm); pts[1] = vec2(R, B); pts[2] = vec2(R - arm, B);
    a = max(a, strokeReveal(px, pts, 3, prog, hw));
    return a;
}

#include "frame_main.glsl"
