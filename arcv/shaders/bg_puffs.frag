#version 330

// Rising, expanding radial-gradient puffs (procedural particles).
in vec2 v_uv;
out vec4 fragColor;

uniform vec2 u_resolution;
uniform float u_progress;
uniform float u_time;
uniform vec3 u_color;

float hash(float x) { return fract(sin(x * 12.9898) * 43758.5453); }

void main() {
    float a = 0.0;
    for (int i = 0; i < 24; i++) {
        float fi = float(i);
        float x = hash(fi * 1.7);
        float speed = 0.04 + 0.06 * hash(fi * 3.1);
        float life = fract(u_time * speed + hash(fi * 5.3));
        vec2 pos = vec2(x, life);                 // rises bottom -> top
        float rad = mix(0.02, 0.13, life);
        float puff = smoothstep(rad, 0.0, distance(v_uv, pos));
        a += puff * sin(life * 3.14159);          // fade in then out
    }
    a *= u_progress * 0.22;
    if (a <= 0.003) discard;
    fragColor = vec4(u_color * a, a);
}
