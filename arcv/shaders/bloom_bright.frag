#version 330

// Bloom bright-pass: keep only HUD pixels brighter than the threshold; these
// are the glow source fed into the separable blur.

in vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_src;
uniform float u_threshold;

void main() {
    vec3 c = texture(u_src, v_uv).rgb;
    float luma = dot(c, vec3(0.2126, 0.7152, 0.0722));
    fragColor = vec4(luma > u_threshold ? c : vec3(0.0), 1.0);
}
