#version 330

// Illuminator: a soft radial glow that follows the cursor (Arwes Illuminator).
// radial-gradient(color 0%, transparent ~70%).

in vec2 v_uv;
out vec4 fragColor;

uniform vec2 u_mouse;     // UV, y-up
uniform vec3 u_color;
uniform float u_radius;   // UV radius
uniform float u_strength;

void main() {
    float d = distance(v_uv, u_mouse);
    float a = smoothstep(u_radius, 0.0, d) * u_strength;
    if (a <= 0.002) discard;
    fragColor = vec4(u_color * a, a);
}
