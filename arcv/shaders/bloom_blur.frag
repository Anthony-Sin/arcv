#version 330

// Separable Gaussian blur. Run alternately horizontal/vertical (ping-pong)
// to build a wide, soft glow.

in vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_src;
uniform vec2 u_dir;   // texel step along one axis: (1/w, 0) or (0, 1/h)

void main() {
    float w[5] = float[](0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);
    vec3 result = texture(u_src, v_uv).rgb * w[0];
    for (int i = 1; i < 5; i++) {
        result += texture(u_src, v_uv + u_dir * float(i)).rgb * w[i];
        result += texture(u_src, v_uv - u_dir * float(i)).rgb * w[i];
    }
    fragColor = vec4(result, 1.0);
}
