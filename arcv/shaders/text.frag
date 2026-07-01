#version 330

// Text fragment: atlas alpha -> cyan glyph. Decipher/scramble is resolved on
// the CPU (which glyph cell each character points at), so this stays trivial.

in vec2 v_auv;
out vec4 fragColor;

uniform sampler2D u_atlas;   // single-channel coverage
uniform vec3 u_color;
uniform float u_alpha;

void main() {
    float a = texture(u_atlas, v_auv).r * u_alpha;
    if (a <= 0.003) discard;
    fragColor = vec4(u_color * a, a);
}
