#version 330
#include "frame_lib.glsl"

// Asymmetric top-left / bottom-right tactical brackets with a diagonal notch.
float frameShape(vec2 px, vec2 c, vec2 hs, float prog) {
    float L = c.x - hs.x, R = c.x + hs.x, T = c.y + hs.y, B = c.y - hs.y;
    float arm = clamp(min(hs.x, hs.y) * 0.7, 10.0, 80.0);
    float s = clamp(arm * 0.35, 6.0, 24.0);
    float hw = 1.6;
    vec2 pts[10];

    pts[0] = vec2(L, T - arm); pts[1] = vec2(L, T - s);
    pts[2] = vec2(L + s, T);   pts[3] = vec2(L + arm, T);
    float a = strokeReveal(px, pts, 4, prog, hw);

    pts[0] = vec2(R, B + arm); pts[1] = vec2(R, B + s);
    pts[2] = vec2(R - s, B);   pts[3] = vec2(R - arm, B);
    return max(a, strokeReveal(px, pts, 4, prog, hw));
}

#include "frame_main.glsl"
