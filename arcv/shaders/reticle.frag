#version 330

// Targeting reticle locked to the primary detection: an expanding ring, a
// gapped crosshair, and four rotating ticks. Reveal scales with progress.

in vec2 v_uv;
out vec4 fragColor;

uniform vec2 u_resolution;
uniform vec2 u_center;   // UV, y-up
uniform vec2 u_half;     // UV half-size of the primary box
uniform float u_progress;
uniform float u_time;
uniform vec3 u_color;

float ringMask(vec2 p, vec2 c, float r, float w) {
    return 1.0 - smoothstep(w, w + 1.5, abs(length(p - c) - r));
}

float segMask(vec2 p, vec2 a, vec2 b, float w) {
    vec2 pa = p - a, ba = b - a;
    float h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-6), 0.0, 1.0);
    return 1.0 - smoothstep(w, w + 1.5, length(pa - ba * h));
}

void main() {
    if (u_progress <= 0.001) discard;

    vec2 px = v_uv * u_resolution;
    vec2 c = u_center * u_resolution;
    float r = max(min(u_half.x * u_resolution.x, u_half.y * u_resolution.y) * 0.55, 18.0);
    float w = 1.4;
    float a = 0.0;

    a = max(a, ringMask(px, c, r * u_progress, w) * 0.9);

    float gap = r * 0.45;
    float arm = r * 1.4 * u_progress;
    a = max(a, segMask(px, c + vec2(gap, 0.0), c + vec2(arm, 0.0), w));
    a = max(a, segMask(px, c - vec2(gap, 0.0), c - vec2(arm, 0.0), w));
    a = max(a, segMask(px, c + vec2(0.0, gap), c + vec2(0.0, arm), w));
    a = max(a, segMask(px, c - vec2(0.0, gap), c - vec2(0.0, arm), w));

    float ang = u_time * 1.2;
    for (int k = 0; k < 4; k++) {
        float th = ang + float(k) * 1.5707963;
        vec2 dir = vec2(cos(th), sin(th));
        a = max(a, segMask(px, c + dir * (r * 1.05), c + dir * (r * 1.28), w) * u_progress);
    }

    if (a <= 0.001) discard;
    fragColor = vec4(u_color * a, a);
}
