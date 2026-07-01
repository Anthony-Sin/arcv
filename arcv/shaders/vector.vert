#version 330

// Batched HUD vector geometry (lines expanded to quads + filled triangles).
// Positions arrive in pixels with a top-left origin.

in vec2 in_pos;
in float in_edge;   // -1..1 across a stroke (0 for fills)
in vec4 in_color;
in float in_hw;     // stroke half-width in px (large for fills)

uniform vec2 u_resolution;

out vec4 v_color;
out float v_edge;
out float v_hw;

void main() {
    v_color = in_color;
    v_edge = in_edge;
    v_hw = in_hw;
    vec2 ndc = vec2(in_pos.x / u_resolution.x * 2.0 - 1.0,
                    1.0 - in_pos.y / u_resolution.y * 2.0);
    gl_Position = vec4(ndc, 0.0, 1.0);
}
