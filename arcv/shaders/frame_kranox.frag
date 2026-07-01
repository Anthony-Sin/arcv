#version 330
#include "frame_lib.glsl"

// Ornate tech-panel brackets with a double-step notch and a deco accent line.
float frameShape(vec2 px, vec2 c, vec2 hs, float prog) {
    float L = c.x - hs.x, R = c.x + hs.x, T = c.y + hs.y, B = c.y - hs.y;
    float ss = clamp(min(hs.x, hs.y) * 0.32, 8.0, 26.0);
    float arm = clamp(min(hs.x, hs.y) * 0.8, 16.0, 90.0);
    float hw = 1.5;
    vec2 pts[10];

    // top-left layered bracket
    pts[0] = vec2(L, T - arm);
    pts[1] = vec2(L, T - ss * 2.0);
    pts[2] = vec2(L + ss, T - ss);
    pts[3] = vec2(L + ss, T);
    pts[4] = vec2(L + arm, T);
    float a = strokeReveal(px, pts, 5, prog, hw);

    // bottom-right mirror
    pts[0] = vec2(R, B + arm);
    pts[1] = vec2(R, B + ss * 2.0);
    pts[2] = vec2(R - ss, B + ss);
    pts[3] = vec2(R - ss, B);
    pts[4] = vec2(R - arm, B);
    a = max(a, strokeReveal(px, pts, 5, prog, hw));

    // deco accents
    pts[0] = vec2(L + ss * 1.8, T - ss * 1.8); pts[1] = vec2(L + ss * 1.8 + ss, T - ss * 1.8);
    a = max(a, strokeReveal(px, pts, 2, prog, hw));
    pts[0] = vec2(R - ss * 1.8, B + ss * 1.8); pts[1] = vec2(R - ss * 1.8 - ss, B + ss * 1.8);
    a = max(a, strokeReveal(px, pts, 2, prog, hw));
    return a;
}

#include "frame_main.glsl"
