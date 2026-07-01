#version 330

// Text glyph quads with per-vertex color. Positions in pixels, top-left origin.

in vec2 in_pos;
in vec2 in_auv;
in vec4 in_color;

uniform vec2 u_resolution;

out vec2 v_auv;
out vec4 v_color;

void main() {
    v_auv = in_auv;
    v_color = in_color;
    vec2 ndc = vec2(in_pos.x / u_resolution.x * 2.0 - 1.0,
                    1.0 - in_pos.y / u_resolution.y * 2.0);
    gl_Position = vec4(ndc, 0.0, 1.0);
}
