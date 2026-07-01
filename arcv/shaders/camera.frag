#version 330

// Camera base pass: sample the live feed and color-grade it toward the dark
// teal Arwes look so the HUD pops on top.

in vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_cam;   // swizzle='BGR' makes .rgb read correct RGB
uniform vec3 u_base;       // dark scene base (#111)
uniform float u_grade;     // 0 = raw feed, 1 = fully graded

void main() {
    vec2 uv = vec2(v_uv.x, 1.0 - v_uv.y);  // flip: GL origin is bottom-left
    vec3 c = texture(u_cam, uv).rgb;

    float luma = dot(c, vec3(0.2126, 0.7152, 0.0722));
    vec3 desat = mix(c, vec3(luma), 0.35);
    vec3 tint = vec3(0.62, 1.04, 1.12);          // push toward cyan
    vec3 graded = desat * tint;
    graded = mix(u_base, graded, smoothstep(0.0, 0.28, luma) * 0.82 + 0.18);
    graded *= 0.82;                               // darken so HUD stands out

    fragColor = vec4(mix(c, graded, u_grade), 1.0);
}
