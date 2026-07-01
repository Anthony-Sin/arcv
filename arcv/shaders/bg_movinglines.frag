#version 330

// Vertical "data rain" streaks scrolling down; speed scales with optical-flow
// magnitude when supplied.
in vec2 v_uv;
out vec4 fragColor;

uniform vec2 u_resolution;
uniform float u_progress;
uniform float u_time;
uniform vec3 u_color;
uniform float u_distance;   // column spacing in px
uniform float u_speed;
uniform float u_flow;       // 0..1 optical-flow magnitude

float hash(float x) { return fract(sin(x * 12.9898) * 43758.5453); }

void main() {
    vec2 px = v_uv * u_resolution;
    float col = floor(px.x / u_distance);
    float seed = hash(col);
    float speed = u_speed * (0.5 + seed) * (1.0 + u_flow * 4.0);
    float len = mix(0.12, 0.5, hash(col * 7.0));

    float inCol = 1.0 - smoothstep(u_distance * 0.12, u_distance * 0.12 + 1.5,
                                   abs(mod(px.x, u_distance) - u_distance * 0.5));
    float yv = fract(v_uv.y + u_time * speed + seed);
    float streak = yv < len ? (1.0 - yv / len) : 0.0;
    float a = inCol * streak * u_progress * 0.35;
    if (a <= 0.003) discard;
    fragColor = vec4(u_color * a, a);
}
