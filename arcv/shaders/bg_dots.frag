#version 330

// Dot grid that assembles from the center outward.
in vec2 v_uv;
out vec4 fragColor;

uniform vec2 u_resolution;
uniform float u_progress;
uniform vec3 u_color;
uniform float u_distance;   // spacing in px
uniform float u_size;       // dot radius in px

void main() {
    vec2 px = v_uv * u_resolution;
    vec2 cell = mod(px, u_distance) - u_distance * 0.5;
    float dot = 1.0 - smoothstep(u_size, u_size + 1.2, length(cell));
    float distC = length(v_uv - 0.5) / 0.7071;
    float reveal = clamp(u_progress * 1.6 - distC, 0.0, 1.0);
    float a = dot * reveal * 0.45;
    if (a <= 0.003) discard;
    fragColor = vec4(u_color * a, a);
}
