#version 330
#include "frame_lib.glsl"

// Rectangle with 45-degree chamfered corners, drawn as one closed outline.
float frameShape(vec2 px, vec2 c, vec2 hs, float prog) {
    float L = c.x - hs.x, R = c.x + hs.x, T = c.y + hs.y, B = c.y - hs.y;
    float ss = clamp(min(hs.x, hs.y) * 0.4, 8.0, 28.0);
    float hw = 1.5;
    vec2 pts[10];
    pts[0] = vec2(L + ss, T);
    pts[1] = vec2(R - ss, T);
    pts[2] = vec2(R, T - ss);
    pts[3] = vec2(R, B + ss);
    pts[4] = vec2(R - ss, B);
    pts[5] = vec2(L + ss, B);
    pts[6] = vec2(L, B + ss);
    pts[7] = vec2(L, T - ss);
    pts[8] = vec2(L + ss, T);
    return strokeReveal(px, pts, 9, prog, hw);
}

#include "frame_main.glsl"
