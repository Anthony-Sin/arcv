#version 330

// Tracker dots at ORB keypoints.
in vec2 v_uv;
out vec4 fragColor;

uniform vec2 u_resolution;
uniform vec2 u_points[64];   // UV, y-up
uniform int u_pcount;
uniform vec3 u_color;
uniform float u_progress;

void main() {
    vec2 px = v_uv * u_resolution;
    float a = 0.0;
    for (int i = 0; i < 64; i++) {
        if (i >= u_pcount) break;
        float d = length(px - u_points[i] * u_resolution);
        a = max(a, 1.0 - smoothstep(1.8, 3.4, d));
    }
    a *= u_progress * 0.85;
    if (a <= 0.003) discard;
    fragColor = vec4(u_color * a, a);
}
