#version 330

// Grid of horizontal (dashed) + vertical (solid) lines.
in vec2 v_uv;
out vec4 fragColor;

uniform vec2 u_resolution;
uniform float u_progress;
uniform vec3 u_color;
uniform float u_distance;    // spacing in px
uniform float u_lineWidth;   // px

void main() {
    vec2 px = v_uv * u_resolution;
    vec2 g = mod(px, u_distance);
    float vx = 1.0 - smoothstep(u_lineWidth, u_lineWidth + 1.0, min(g.x, u_distance - g.x));
    float hy = 1.0 - smoothstep(u_lineWidth, u_lineWidth + 1.0, min(g.y, u_distance - g.y));
    float dash = step(0.5, fract(px.x / (u_distance * 0.25)));  // dashed horizontals
    hy *= dash;
    float a = max(vx, hy) * u_progress * 0.35;
    if (a <= 0.003) discard;
    fragColor = vec4(u_color * a, a);
}
