#version 330

// EdgeTrace: draw the OpenCV Canny edge mask as glowing cyan contours, aligned
// to the (v-flipped) camera feed. The "scanning the world" layer.

in vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_edge;   // single-channel mask, top-left origin
uniform vec3 u_color;
uniform float u_intensity;
uniform float u_progress;

void main() {
    vec2 uv = vec2(v_uv.x, 1.0 - v_uv.y);
    float e = texture(u_edge, uv).r;
    float a = e * u_intensity * u_progress;
    if (a <= 0.003) discard;
    fragColor = vec4(u_color * a, a);
}
