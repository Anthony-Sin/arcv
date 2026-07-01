#version 330

// Faint background grid drawn behind the HUD (into the scene, not bloomed).

in vec2 v_uv;
out vec4 fragColor;

uniform vec2 u_resolution;
uniform vec3 u_color;
uniform float u_cell;    // grid spacing in px
uniform float u_alpha;

void main() {
    vec2 px = v_uv * u_resolution;
    vec2 g = mod(px, u_cell);
    float lw = 1.0;
    float lx = 1.0 - smoothstep(lw, lw + 1.0, min(g.x, u_cell - g.x));
    float ly = 1.0 - smoothstep(lw, lw + 1.0, min(g.y, u_cell - g.y));
    float a = max(lx, ly) * u_alpha;
    // brighter dots at intersections
    a = max(a, lx * ly * u_alpha * 2.0);
    if (a <= 0.002) discard;
    fragColor = vec4(u_color * a, a);
}
