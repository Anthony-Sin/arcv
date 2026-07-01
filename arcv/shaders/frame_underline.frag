#version 330
#include "frame_lib.glsl"

// Bottom underline that kinks up at the bottom-right corner, plus a short
// top-left accent.
float frameShape(vec2 px, vec2 c, vec2 hs, float prog) {
    float L = c.x - hs.x, R = c.x + hs.x, T = c.y + hs.y, B = c.y - hs.y;
    float ss = clamp(min(hs.x, hs.y) * 0.4, 8.0, 28.0);
    float hw = 1.6;
    vec2 pts[10];

    pts[0] = vec2(L, B); pts[1] = vec2(R - ss, B); pts[2] = vec2(R, B + ss);
    float a = strokeReveal(px, pts, 3, prog, hw);

    pts[0] = vec2(L, T); pts[1] = vec2(L, T - ss);
    a = max(a, strokeReveal(px, pts, 2, prog, hw));
    pts[0] = vec2(L, T); pts[1] = vec2(L + ss, T);
    a = max(a, strokeReveal(px, pts, 2, prog, hw));
    return a;
}

#include "frame_main.glsl"
