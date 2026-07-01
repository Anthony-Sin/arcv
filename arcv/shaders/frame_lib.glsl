// Shared frame library: uniforms + SDF helpers. Included after the #version
// line by every frame shader. Each frame shader defines
//   float frameShape(vec2 px, vec2 c, vec2 hs, float prog)
// and then includes frame_main.glsl.

in vec2 v_uv;
out vec4 fragColor;

uniform vec2 u_resolution;
uniform vec4 u_boxes[16];   // (cx, cy, hw, hh) in UV, y-up
uniform vec4 u_meta[16];    // (progress, score, kind_flag, primary_flag)
uniform int u_count;
uniform vec3 u_color;

float _seg(vec2 p, vec2 a, vec2 b, out float h) {
    vec2 pa = p - a, ba = b - a;
    h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-6), 0.0, 1.0);
    return length(pa - ba * h);
}

// Reveal a polyline of `n` points up to `reveal` fraction of its arc length.
float strokeReveal(vec2 p, vec2 pts[10], int n, float reveal, float halfw) {
    float total = 0.0;
    for (int i = 0; i < 9; i++) { if (i >= n - 1) break; total += length(pts[i + 1] - pts[i]); }
    total = max(total, 1e-6);
    float showLen = reveal * total;
    float d = 1e9, acc = 0.0;
    for (int i = 0; i < 9; i++) {
        if (i >= n - 1) break;
        float L = length(pts[i + 1] - pts[i]);
        float h;
        float dd = _seg(p, pts[i], pts[i + 1], h);
        if (acc + h * L <= showLen) d = min(d, dd);
        acc += L;
    }
    return 1.0 - smoothstep(halfw, halfw + 1.5, d);
}
