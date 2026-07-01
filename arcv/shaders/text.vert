#version 330

// Text glyph quads. Positions arrive in screen-space UV [0,1] (y-up); atlas
// coordinates index the monospace glyph atlas.

in vec2 in_pos;
in vec2 in_auv;
out vec2 v_auv;

void main() {
    v_auv = in_auv;
    gl_Position = vec4(in_pos * 2.0 - 1.0, 0.0, 1.0);
}
