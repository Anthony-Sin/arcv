#version 330

in vec2 v_auv;
in vec4 v_color;
out vec4 fragColor;

uniform sampler2D u_atlas;

void main() {
    float a = texture(u_atlas, v_auv).r * v_color.a;
    if (a <= 0.003) discard;
    fragColor = vec4(v_color.rgb * a, a);  // premultiplied for additive
}
